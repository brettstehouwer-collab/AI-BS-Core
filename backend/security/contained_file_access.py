"""Bounded uploads and media paths confined to explicit application stores.

No application constructors, credentials, providers, or storage initialization
run on import. Caller admission must happen before these filesystem operations.
"""
import os
from contextlib import contextmanager, ExitStack
import mimetypes
from pathlib import Path
import secrets
import unicodedata

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MEDIA_SUFFIXES = frozenset({'.mp4', '.mov', '.webm', '.mkv', '.avi', '.mp3', '.wav',
    '.flac', '.ogg', '.m4a', '.aac', '.png', '.jpg', '.jpeg', '.webp', '.gif',
    '.avif', '.bmp', '.tif', '.tiff'})
_DEVICES = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
            *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def validate_upload_filename(filename):
    if (not isinstance(filename, str) or not filename or len(filename) > 180
            or filename[-1] in ' .'
            or any(c in '<>:"/\\|?*' or unicodedata.category(c).startswith('C') for c in filename)
            or filename in {'.', '..'}
            or unicodedata.normalize('NFKC', filename.split('.')[0]).rstrip(' .').upper() in _DEVICES):
        raise HTTPException(400, 'A plain, valid upload filename is required.')
    return filename


def _reject_links(path):
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise HTTPException(403, 'Linked storage paths are not permitted.')


def _windows_io():
    if os.name != 'nt':
        raise HTTPException(503, 'A verified filesystem handle adapter is required on this platform.')
    import msvcrt
    import ntsecuritycon
    import win32con
    import win32file
    return msvcrt, ntsecuritycon, win32con, win32file


def _normal_handle_path(value):
    if value.startswith('\\\\?\\'):
        value = value[4:]
    return os.path.normcase(os.path.normpath(value))


@contextmanager
def _pinned_directory(root, *, create=False):
    """Hold every directory without delete sharing; reject reparse handles."""
    _, security, con, native = _windows_io()
    root = Path(root).absolute()
    handles = []
    try:
        for part in [*reversed(root.parents), root]:
            if not part.exists() and create:
                part.mkdir()
            _reject_links(part)
            try:
                handle = native.CreateFile(str(part), security.FILE_READ_ATTRIBUTES,
                    con.FILE_SHARE_READ | con.FILE_SHARE_WRITE, None, con.OPEN_EXISTING,
                    con.FILE_FLAG_BACKUP_SEMANTICS | 0x00200000, None)  # FILE_FLAG_OPEN_REPARSE_POINT
            except OSError:
                raise HTTPException(409, 'Storage is unavailable or is being changed.') from None
            handles.append(handle)
            attributes = native.GetFileInformationByHandle(handle)[0]
            final = native.GetFinalPathNameByHandle(handle, 0)
            if attributes & 0x400 or not attributes & 0x10 or _normal_handle_path(final) != _normal_handle_path(str(part)):
                raise HTTPException(403, 'Storage identity is not a managed directory.')
        yield root
    finally:
        for handle in reversed(handles):
            handle.Close()


def _file_from_handle(handle, mode):
    msvcrt, _, _, _ = _windows_io()
    flags = (os.O_RDWR if '+' in mode else os.O_RDONLY) | os.O_BINARY
    descriptor = msvcrt.open_osfhandle(handle.Detach(), flags)
    try:
        return os.fdopen(descriptor, mode)
    except BaseException:
        os.close(descriptor)
        raise


async def write_bounded_upload(upload, root, filename, *, max_bytes=MAX_UPLOAD_BYTES):
    """Write once, bounded in chunks. Never replace an existing destination."""
    filename = validate_upload_filename(filename)
    root = Path(root).absolute()
    _reject_links(root)
    _, _, con, native = _windows_io()
    with _pinned_directory(root, create=True):
        destination = root / filename
        if destination.exists() or destination.is_symlink():
            raise HTTPException(409, 'A file with that name already exists.')
        temporary = root / ('.upload-' + secrets.token_hex(16) + '.tmp')
        handle = native.CreateFile(str(temporary), con.GENERIC_READ | con.GENERIC_WRITE,
            con.FILE_SHARE_READ, None, con.CREATE_NEW, 0x100 | 0x00200000, None)
        try:
            with _file_from_handle(handle, 'w+b') as output:
                size = 0
                while block := await upload.read(1024 * 1024):
                    size += len(block)
                    if size > max_bytes:
                        raise HTTPException(413, 'Upload exceeds the permitted size.')
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
                _reject_links(root)
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    raise HTTPException(409, 'A file with that name already exists.') from None
            return destination, size
        finally:
            if int(handle):
                handle.Close()
            temporary.unlink(missing_ok=True)


def resolve_media_path(value, roots):
    """Allow existing regular media only, under an explicitly supplied store."""
    if not isinstance(value, str) or not value or len(value) > 4096 or '\x00' in value:
        raise HTTPException(400, 'A valid media path is required.')
    if value.startswith(('\\\\', '//')):
        raise HTTPException(403, 'Network media paths are not permitted.')
    path = Path(value)
    if not path.is_absolute() or any(part == '..' for part in path.parts):
        raise HTTPException(403, 'Media must be in a managed application store.')
    if any(':' in part for part in path.parts[1:]):
        raise HTTPException(403, 'Alternate media streams are not permitted.')
    _reject_links(path)
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError, OSError):
        raise HTTPException(404, 'Media file is unavailable.') from None
    allowed = False
    for root in roots:
        root = Path(root).absolute()
        _reject_links(root)
        if resolved.is_relative_to(root.resolve(strict=False)):
            allowed = True
            break
    if not allowed:
        raise HTTPException(403, 'Media must be in a managed application store.')
    if resolved.suffix.lower() not in MEDIA_SUFFIXES or not resolved.is_file():
        raise HTTPException(415, 'This file is not supported streamable media.')
    return resolved


@contextmanager
def open_verified_media(value, roots):
    """Check the final opened identity and read that same immutable handle."""
    checked = resolve_media_path(value, roots)
    _, _, con, native = _windows_io()
    with _pinned_directory(checked.parent):
        _reject_links(checked)
        try:
            handle = native.CreateFile(str(checked), con.GENERIC_READ, con.FILE_SHARE_READ,
                                       None, con.OPEN_EXISTING, 0x00200000, None)
        except OSError:
            raise HTTPException(409, 'Media is unavailable or is being changed.') from None
        try:
            attributes = native.GetFileInformationByHandle(handle)[0]
            final = Path(_normal_handle_path(native.GetFinalPathNameByHandle(handle, 0)))
            allowed = any(final.is_relative_to(Path(root).absolute()) for root in roots)
            if attributes & (0x400 | 0x10) or not allowed or final.suffix.lower() not in MEDIA_SUFFIXES:
                raise HTTPException(403, 'The opened file is not managed media.')
            with _file_from_handle(handle, 'rb') as source:
                yield final, source
        finally:
            if int(handle):
                handle.Close()


class _PinnedMediaResponse(StreamingResponse):
    def __init__(self, *args, release, **kwargs):
        super().__init__(*args, **kwargs)
        self._release = release

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release()


def stream_media_response(value, roots, request: Request, *, media_type=None, filename=None):
    stack = ExitStack()
    try:
        path, source = stack.enter_context(open_verified_media(value, roots))
        size = os.fstat(source.fileno()).st_size
        start, end, status = 0, size - 1, 200
        supplied_range = request.headers.get('range', '')
        if supplied_range:
            try:
                unit, value_range = supplied_range.split('=', 1)
                first, last = value_range.split('-', 1)
                if unit != 'bytes' or ',' in value_range or not size:
                    raise ValueError
                if not first:
                    suffix = int(last)
                    if suffix <= 0:
                        raise ValueError
                    start = max(0, size - suffix)
                else:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                if start < 0 or start > end or start >= size:
                    raise ValueError
                status = 206
            except ValueError:
                raise HTTPException(416, 'Requested media range is unavailable.',
                                    headers={'Content-Range': f'bytes */{size}'}) from None
        length = max(0, end - start + 1)
        headers = {'Accept-Ranges': 'bytes', 'Content-Length': str(length), 'X-Content-Type-Options': 'nosniff'}
        if status == 206:
            headers['Content-Range'] = f'bytes {start}-{end}/{size}'
        if filename:
            from urllib.parse import quote
            headers['Content-Disposition'] = "inline; filename*=UTF-8''" + quote(filename, safe='')
        def chunks():
            source.seek(start)
            remaining = length
            while remaining:
                block = source.read(min(64 * 1024, remaining))
                if not block:
                    break
                remaining -= len(block)
                yield block
        return _PinnedMediaResponse(chunks(), status_code=status, headers=headers,
            media_type=media_type or mimetypes.guess_type(str(path))[0] or 'application/octet-stream', release=stack.close)
    except BaseException:
        stack.close()
        raise
