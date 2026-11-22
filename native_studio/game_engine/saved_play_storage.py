"""Bounded project-owned immutable publications and persistent player slots.

Native typed asset staging precedes publication. This module never opens SQLite,
decodes game content, migrates a save, or deletes a retained publication/slot.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import stat
import uuid

CONTENT_LIMIT = 1024 * 1024
CLOSURE_LIMIT = 128 * 1024 * 1024
RECORD_LIMIT = 256 * 1024
SLOT_LIMIT = 32 * 1024
MAX_DEPENDENCIES = 32  # Complete export v2's existing native/wire limit.
MAX_FILE = 48 * 1024 * 1024 + 65536
SAVED_PLAY_CAPABILITY = 'chapter-saved-play-v1'
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z')
_REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('Duplicate saved-play record key')
        value[key] = item
    return value


def _constant(value):
    raise ValueError('Nonfinite saved-play record')


def _json(raw, limit=RECORD_LIMIT):
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError('Saved-play record byte limit')
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_pairs,
                      parse_constant=_constant)


def _encoded(value, limit=RECORD_LIMIT):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > limit:
        raise ValueError('Saved-play record byte limit')
    return raw


def _uuid(value):
    if type(value) is not str or not _UUID.fullmatch(value):
        raise ValueError('Saved play requires canonical version4 UUIDs')
    return value


def _digest(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        raise ValueError('Invalid saved-play digest')
    return value


def _text(value):
    if (type(value) is not str or not value or '\0' in value or
            len(value.encode('utf-8', 'strict')) > 4096):
        raise ValueError('Invalid saved-play identity text')
    return value


def _io_path(path, *, recursive=False):
    """Use extended Windows spelling for I/O, keeping public identities lexical.

    This is not a resolver or an admission check. Callers still validate every
    logical ancestor and pin directory handles before reading or mutating it.
    """
    p = Path(path)
    if os.name != 'nt':
        return p
    value = os.path.abspath(p)
    if value.startswith('\\\\?\\'):
        return Path(value)
    # Preserve ordinary spelling where Windows APIs already support it. The
    # directory creation boundary is lower than MAX_PATH's file boundary.
    if not recursive and len(value) < 248:
        return p
    if value.startswith('\\\\'):
        return Path('\\\\?\\UNC\\' + value[2:])
    return Path('\\\\?\\' + value)


def checked_path(path, *, directory=None, missing=False):
    """Inspect every lexical ancestor before resolving or using an owned path."""
    p = Path(path)
    if '..' in p.parts:
        raise ValueError('Saved-play paths cannot traverse ancestors')
    p = Path(os.path.abspath(p))
    for member in (*reversed(p.parents), p):
        try:
            info = _io_path(member).lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise ValueError('Saved-play path does not exist: ' + str(member)) from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & _REPARSE:
            raise ValueError('Saved-play paths cannot use links or junctions')
        if member != p and not stat.S_ISDIR(info.st_mode):
            raise ValueError('Saved-play ancestor is not a directory')
    if _io_path(p).exists() and directory is not None and _io_path(p).is_dir() != directory:
        raise ValueError('Unexpected saved-play path type')
    return p


def _windows_handle(path, *, directory, read=False):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE];close.restype = wintypes.BOOL
    info = kernel.GetFileInformationByHandleEx
    info.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    info.restype = wintypes.BOOL
    class AttributeTag(ctypes.Structure):
        _fields_ = [('attributes', wintypes.DWORD), ('tag', wintypes.DWORD)]
    # OPEN_REPARSE_POINT inspects the terminal entry itself. Omitting
    # SHARE_DELETE pins directory names; a read also denies concurrent writes.
    flags = 0x00200000 | (0x02000000 if directory else 0x08000000)
    handle = create(str(_io_path(path)), 0x80000000 if read else 0, 1 if read else 3,
                    None, 3, flags, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        tag = AttributeTag()
        if not info(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
            raise ctypes.WinError(ctypes.get_last_error())
        if bool(tag.attributes & 0x10) != directory or tag.attributes & _REPARSE:
            raise ValueError('Saved-play handle resolves to a link or unexpected file type')
    except Exception:
        close(handle);raise
    return handle, close


@contextmanager
def _pinned_directory(path):
    p = checked_path(path, directory=True)
    handles = []
    try:
        if os.name == 'nt':
            # Open from root downward. Once a parent is pinned, the next
            # component cannot be redirected by renaming that parent.
            for member in (*reversed(p.parents), p):
                handles.append(_windows_handle(member, directory=True))
        yield p
    finally:
        for handle, close in reversed(handles):close(handle)


@contextmanager
def _reader(path):
    p = checked_path(path, directory=False)
    with _pinned_directory(p.parent):
        if os.name == 'nt':
            import msvcrt
            handle, close = _windows_handle(p, directory=False, read=True)
            try:
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except Exception:
                close(handle);raise
            with os.fdopen(fd, 'rb') as stream:yield stream
        else:
            with _io_path(p).open('rb') as stream:yield stream


def _new_directory(path):
    p = checked_path(path, directory=True, missing=True)
    with _pinned_directory(p.parent):_io_path(p).mkdir()
    return checked_path(p, directory=True)


def _rename_new_directory(source, destination):
    checked_path(source, directory=True)
    checked_path(destination, directory=True, missing=True)
    with _pinned_directory(source.parent), _pinned_directory(destination.parent):
        os.rename(_io_path(source), _io_path(destination))


def _mkdir(path):
    p = checked_path(path, directory=True, missing=True)
    with _pinned_directory(p.parent):
        try:
            _io_path(p).mkdir()
        except FileExistsError:
            pass
    return checked_path(p, directory=True)


def _read(path, limit):
    p = checked_path(path, directory=False)
    size = _io_path(p).stat().st_size
    if not 0 < size <= limit:
        raise ValueError('Saved-play file byte limit')
    with _reader(p) as stream:
        if os.fstat(stream.fileno()).st_size != size:
            raise ValueError('Saved-play file changed before reading')
        raw = stream.read(limit + 1)
    if len(raw) != size:
        raise ValueError('Saved-play file changed while reading')
    checked_path(p, directory=False)
    return raw


def _write_new(path, raw):
    p = checked_path(path, directory=False, missing=True)
    with _pinned_directory(p.parent):
        with _io_path(p).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    checked_path(p, directory=False)


def snapshot_identity(snapshot):
    """Validate owned metadata, not native AIBD/geometry semantics."""
    if (type(snapshot.payload) is not bytes or not 1 <= len(snapshot.payload) <= CONTENT_LIMIT
            or hashlib.sha256(snapshot.payload).hexdigest() != _digest(snapshot.fingerprint)):
        raise ValueError('Saved chapter snapshot hash or byte limit mismatch')
    if type(snapshot.export_version) is not int or snapshot.export_version != 2:
        raise ValueError('Saved play requires complete native dependency export v2')
    if snapshot.asset_profile not in ('legacy_v1', 'warm-beginning'):
        raise ValueError('Unknown saved chapter asset profile')
    if type(snapshot.content_revision) is not int or not 0 <= snapshot.content_revision < 2**64:
        raise ValueError('Invalid saved content revision')
    if (type(snapshot.asset_refs) is not tuple or type(snapshot.dependency_kinds) is not tuple
            or len(snapshot.asset_refs) != len(snapshot.dependency_kinds)
            or len(snapshot.asset_refs) > MAX_DEPENDENCIES):
        raise ValueError('Invalid complete saved chapter dependency closure')
    dependencies = []
    previous = ''
    for ref, kind in zip(snapshot.asset_refs, snapshot.dependency_kinds):
        if type(kind) is not int or kind not in (0, 1, 2):
            raise ValueError('Invalid saved chapter dependency kind')
        row = {'asset_id': _uuid(ref.asset_id), 'asset_sha256': _digest(ref.asset_sha256),
               'pack_sha256': _digest(ref.pack_sha256), 'kind': kind}
        if row['pack_sha256'] <= previous:
            raise ValueError('Duplicate or unordered saved chapter dependency')
        previous = row['pack_sha256']
        dependencies.append(row)
    return {'project_id': _text(snapshot.scope.project), 'branch_id': _text(snapshot.scope.branch),
            'world_id': _uuid(snapshot.scope.world_id), 'definition_id': _uuid(snapshot.definition_id),
            'content_revision': snapshot.content_revision,
            'content_fingerprint': snapshot.fingerprint, 'asset_profile': snapshot.asset_profile,
            'dependencies': dependencies}


def require_saved_player(executable, snapshot):
    """Capability admission occurs before publication or a retained save is touched."""
    identity = snapshot_identity(snapshot)
    exe = checked_path(executable, directory=False)
    value = _json(_read(exe.with_name('aibs_capabilities.json'), 16 * 1024), 16 * 1024)
    if (type(value) is not dict or type(value.get('schema_version')) is not int
            or value['schema_version'] != 1 or value.get('target') != 'windows-x64'
            or type(value.get('sdk_version')) is not str or len(value['sdk_version']) > 32
            or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value['sdk_version'])):
        raise ValueError('Malformed saved-play native capability declaration')
    features = value.get('features')
    if (type(features) is not dict or any(type(k) is not str or not k or len(k) > 128
                                         or type(v) is not bool for k, v in features.items())):
        raise ValueError('Malformed saved-play native capability flags')
    required = {SAVED_PLAY_CAPABILITY, 'durable_world', 'first_boot_chapter', 'first_boot_content_play',
                'chapter_content_export_v2'}
    if identity['asset_profile'] == 'warm-beginning':
        required.update(('chapter_content_v3', 'chapter_asset_surfaces'))
    for row in identity['dependencies']:
        required.add({0: 'mesh_asset_v1', 1: 'character_asset_v2', 2: 'audio_asset_v2'}[row['kind']])
    for attr, feature in (('authored_inspections', 'chapter-authored-inspections-v1'),
                          ('initial_view_authored', 'chapter-initial-view-v1'),
                          ('opening_workshop_authored', 'chapter-workshop-commissioning-v1')):
        flag = getattr(snapshot, attr, False)
        if type(flag) is not bool:
            raise ValueError('Invalid saved chapter reader requirement')
        if flag:
            required.add(feature)
    if any(features.get(flag) is not True for flag in required):
        raise ValueError('Upgrade the native player before Play saved chapter; a required capability is unavailable')
    return exe


@dataclass(frozen=True)
class PublicationPreparation:
    project: Path
    root: Path
    staging: Path
    identity: dict


@dataclass(frozen=True)
class SavedPublication:
    project: Path
    content_directory: Path
    slot_directory: Path
    identity: dict
    timeline_id: str
    reused_publication: bool
    reused_slot: bool
    record_sha256: str

    @property
    def content_path(self):
        return self.content_directory / 'chapter.aibd'

    @property
    def asset_root(self):
        return self.content_directory / 'assets/packs'

    @property
    def database_path(self):
        return self.slot_directory / 'world.sqlite'


def prepare_publication(project_directory, snapshot):
    identity = snapshot_identity(snapshot)
    project = checked_path(project_directory, directory=True)
    root = _mkdir(project / '.aibs-runtime')
    for name in ('staging', 'content', 'saves'):
        _mkdir(root / name)
    stage = root / 'staging' / str(uuid.uuid4())
    _new_directory(stage)
    _write_new(stage / 'chapter.aibd', snapshot.payload)
    if identity['dependencies']:
        _mkdir(stage / 'assets')
    return PublicationPreparation(project, root, stage, identity)


def _entries(directory, maximum):
    values = []
    for entry in _io_path(directory).iterdir():
        if len(values) == maximum:
            raise ValueError('Saved publication directory member limit')
        # Extended spelling belongs only to the filesystem call, not records,
        # relative membership checks, native arguments or public return values.
        values.append(directory / entry.name)
    return values


def _pack_inventory(stage, identity):
    """Charge bounded encoded bytes; native stage-store owns typed/decoded admission."""
    dependencies = identity['dependencies']
    expected_paths = {'chapter.aibd'}
    expected_dirs = set()
    if dependencies:
        packs = checked_path(stage / 'assets/packs', directory=True)
        expected_dirs.update(('assets', 'assets/packs'))
        actual_packs = _entries(packs, MAX_DEPENDENCIES)
        if {p.name for p in actual_packs} != {r['pack_sha256'] for r in dependencies}:
            raise ValueError('Staged saved chapter dependency set changed')
        total = 0
        for row in dependencies:
            pack = checked_path(packs / row['pack_sha256'], directory=True)
            expected_dirs.add('assets/packs/' + row['pack_sha256'])
            entries = _entries(pack, 4)
            names = {p.name for p in entries}
            payloads = [p for p in entries if p.name not in ('catalog.aibcat', 'LICENSE.txt', 'provenance.json')]
            if len(entries) != 4 or not {'catalog.aibcat', 'LICENSE.txt', 'provenance.json'} <= names or len(payloads) != 1:
                raise ValueError('Staged saved chapter pack is not a complete four-file pack')
            payload = payloads[0]
            allowed = {0: ('.aibmesh', '.aibsurf'), 1: ('.aibchar',), 2: ('.aibaud',)}[row['kind']]
            # Native pack naming binds the payload digest, not the pack digest.
            if payload.stem != row['asset_sha256'] or payload.suffix not in allowed:
                raise ValueError('Staged saved chapter payload identity/type changed')
            for p in entries:
                checked_path(p, directory=False)
                size = _io_path(p).stat().st_size
                maximum = (48 if row['kind'] == 2 else 32) * 1024 * 1024 if p == payload else 1024 * 1024 if p.name == 'catalog.aibcat' else 65536
                if not 0 < size <= maximum or total + size > CLOSURE_LIMIT:
                    raise ValueError('Saved chapter dependency encoded byte limit')
                total += size
                expected_paths.add(p.relative_to(stage).as_posix())
    actual_paths, actual_dirs = set(), set()
    pending = [stage]
    while pending:
        directory = pending.pop()
        for path in _entries(directory, 1 + 4 * MAX_DEPENDENCIES):
            checked_path(path)
            relative = path.relative_to(stage).as_posix()
            if _io_path(path).is_dir():
                actual_dirs.add(relative)
                if relative not in expected_dirs:
                    raise ValueError('Unexpected saved publication directory')
                pending.append(path)
            else:
                actual_paths.add(relative)
            if len(actual_paths) > 1 + 4 * MAX_DEPENDENCIES or len(actual_dirs) > 2 + MAX_DEPENDENCIES:
                raise ValueError('Saved publication member limit')
    if actual_paths != expected_paths or actual_dirs != expected_dirs:
        raise ValueError('Saved publication membership differs from staged closure')
    files = []
    for relative in sorted(expected_paths):
        raw = _read(stage / relative, CONTENT_LIMIT if relative == 'chapter.aibd' else MAX_FILE)
        files.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    content = next(row for row in files if row['path'] == 'chapter.aibd')
    if content['sha256'] != identity['content_fingerprint']:
        raise ValueError('Staged saved chapter changed')
    indexed = {row['path']: row for row in files}
    for dependency in dependencies:
        prefix = 'assets/packs/' + dependency['pack_sha256'] + '/'
        members = {name[len(prefix):]: row for name, row in indexed.items() if name.startswith(prefix)}
        payload = next(name for name in members if name.startswith(dependency['asset_sha256'] + '.'))
        if members[payload]['sha256'] != dependency['asset_sha256']:
            raise ValueError('Native staged payload changed after validation')
        header = b'AIBCAT 1\n' if payload.endswith('.aibmesh') else ('AIBCAT 2\n' + {'.aibsurf': 'surface', '.aibchar': 'character', '.aibaud': 'audio'}[Path(payload).suffix] + ' ').encode('ascii')
        catalog = header + (dependency['asset_id'] + ' ' + dependency['asset_sha256'] + ' ' + payload + '\n').encode('ascii')
        if _read(stage / prefix / 'catalog.aibcat', 1024 * 1024) != catalog:
            raise ValueError('Native staged typed catalog changed after validation')
        manifest = 'AIBPACK 1\n' if payload.endswith('.aibmesh') else 'AIBPACK 2\n'
        manifest += ''.join(name + ' ' + str(members[name]['bytes']) + ' ' + members[name]['sha256'] + '\n' for name in sorted(members))
        if hashlib.sha256(manifest.encode('ascii')).hexdigest() != dependency['pack_sha256']:
            raise ValueError('Native staged pack changed after validation')
    return files


def _verify_existing(publication, record):
    value = _json(_read(publication / 'publication.json', RECORD_LIMIT))
    if _encoded(value) != _encoded(record) or type(value.get('version')) is not int:
        raise ValueError('Existing saved chapter publication is corrupt or has a conflicting identity')
    # Compare every current byte, including exact directory/file membership.
    expected_files = {row['path']: row for row in record['files']}
    expected_dirs = set()
    for name in expected_files:
        parent = PurePosixPath(name).parent
        while parent != PurePosixPath('.'):
            expected_dirs.add(parent.as_posix())
            parent = parent.parent
    actual_files, actual_dirs = set(), set()
    pending = [publication]
    while pending:
        directory = pending.pop()
        for p in _entries(directory, 2 + 4 * MAX_DEPENDENCIES):
            checked_path(p)
            relative = p.relative_to(publication).as_posix()
            if _io_path(p).is_dir():
                if relative not in expected_dirs:
                    raise ValueError('Unexpected existing saved publication directory')
                actual_dirs.add(relative);pending.append(p)
            else:
                if relative not in expected_files and relative != 'publication.json':
                    raise ValueError('Unexpected existing saved publication file')
                actual_files.add(relative)
    if actual_files != set(expected_files) | {'publication.json'} or actual_dirs != expected_dirs:
        raise ValueError('Existing saved publication is incomplete')
    for relative, row in expected_files.items():
        raw = _read(publication / relative, CONTENT_LIMIT if relative == 'chapter.aibd' else MAX_FILE)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Existing saved publication dependency changed')


def _slot(root, identity):
    destination = root / 'saves' / identity['content_fingerprint']
    expected = {'version': 1, 'identity': identity}
    if _io_path(destination).exists():
        checked_path(destination, directory=True)
        value = _json(_read(destination / 'slot.json', SLOT_LIMIT), SLOT_LIMIT)
        if (type(value) is not dict or set(value) != {'version', 'identity', 'timeline_id'}
                or type(value['version']) is not int or value['version'] != 1
                or _encoded(value['identity']) != _encoded(identity)):
            raise ValueError('Existing player slot has a conflicting or malformed binding')
        return destination, _uuid(value['timeline_id']), True
    checked_path(destination, directory=True, missing=True)
    temporary = root / 'staging' / str(uuid.uuid4())
    _new_directory(temporary)
    value = dict(expected, timeline_id=str(uuid.uuid4()))
    _write_new(temporary / 'slot.json', _encoded(value, SLOT_LIMIT))
    # On the supported Windows target rename never replaces an existing directory.
    try:
        _rename_new_directory(temporary, destination)
        return destination, value['timeline_id'], False
    except FileExistsError:
        discard_staging(PublicationPreparation(root.parent, root, temporary, identity))
        return _slot(root, identity)


def finish_publication(preparation, *, context_valid=None):
    """Call only after the native stager's matching success receipt and child exit."""
    p = preparation
    checked_path(p.project, directory=True);checked_path(p.root, directory=True)
    checked_path(p.staging, directory=True)
    if p.staging.parent != p.root / 'staging' or not _UUID.fullmatch(p.staging.name):
        raise ValueError('Invalid owned publication staging path')
    if context_valid is not None and not context_valid():
        raise ValueError('Saved chapter changed before publication')
    files = _pack_inventory(p.staging, p.identity)
    record = {'version': 1, 'identity': p.identity, 'files': files}
    encoded = _encoded(record)
    _write_new(p.staging / 'publication.json', encoded)
    if context_valid is not None and not context_valid():
        raise ValueError('Saved chapter changed before publication')
    destination = p.root / 'content' / p.identity['content_fingerprint']
    checked_path(destination, directory=True, missing=True)
    reused = False
    if _io_path(destination).exists():
        _verify_existing(destination, record)
        discard_staging(p);reused = True
    else:
        try:
            _rename_new_directory(p.staging, destination)
        except FileExistsError:
            _verify_existing(destination, record)
            discard_staging(p);reused = True
    if context_valid is not None and not context_valid():
        raise ValueError('Saved chapter changed before player slot creation')
    directory, timeline, reused_slot = _slot(p.root, p.identity)
    return SavedPublication(p.project, destination, directory, p.identity, timeline, reused, reused_slot,
                            hashlib.sha256(encoded).hexdigest())


def revalidate_publication(publication):
    p = publication
    checked_path(p.project, directory=True)
    root = checked_path(p.project / '.aibs-runtime', directory=True)
    fingerprint = _digest(p.identity['content_fingerprint'])
    if p.content_directory != root / 'content' / fingerprint or p.slot_directory != root / 'saves' / fingerprint:
        raise ValueError('Saved play publication ownership changed')
    checked_path(p.content_directory, directory=True)
    raw = _read(p.content_directory / 'publication.json', RECORD_LIMIT)
    if hashlib.sha256(raw).hexdigest() != p.record_sha256:
        raise ValueError('Saved publication manifest changed before launch')
    record = _json(raw)
    if (type(record) is not dict or set(record) != {'version', 'identity', 'files'}
            or type(record['version']) is not int or record['version'] != 1
            or _encoded(record['identity']) != _encoded(p.identity) or type(record['files']) is not list
            or not 1 <= len(record['files']) <= 1 + 4 * MAX_DEPENDENCIES):
        raise ValueError('Saved publication record changed')
    # Only already published bounded relative names and canonical hashes are used.
    for row in record['files']:
        if (type(row) is not dict or set(row) != {'path', 'bytes', 'sha256'}
                or type(row['path']) is not str or '\\' in row['path']
                or PurePosixPath(row['path']).is_absolute() or '..' in PurePosixPath(row['path']).parts
                or type(row['bytes']) is not int or not 0 < row['bytes'] <= MAX_FILE):
            raise ValueError('Malformed saved publication member record')
        _digest(row['sha256'])
    _verify_existing(p.content_directory, record)
    slot = _json(_read(p.slot_directory / 'slot.json', SLOT_LIMIT), SLOT_LIMIT)
    if _encoded(slot) != _encoded({'version': 1, 'identity': p.identity, 'timeline_id': p.timeline_id}) or type(slot['version']) is not int:
        raise ValueError('Player slot binding changed')
    # SQLite admission, immutable component binding and exclusive slot ownership
    # are performed by native code before a read/write database open.
    return p


def discard_staging(preparation):
    """Delete only this invocation's new staging tree after all children join."""
    root = checked_path(preparation.project / '.aibs-runtime', directory=True)
    target = Path(os.path.abspath(preparation.staging))
    staging_root = checked_path(root / 'staging', directory=True)
    if target.parent != staging_root or not _UUID.fullmatch(target.name):
        raise ValueError('Refusing cleanup outside the owned saved-play staging directory')
    if not _io_path(target).exists():
        return
    pending = [checked_path(target, directory=True)]
    inspected = 0
    while pending:
        for p in _entries(pending.pop(), 6 + 5 * MAX_DEPENDENCIES):
            inspected += 1
            if inspected > 6 + 5 * MAX_DEPENDENCIES:
                raise ValueError('Owned saved-play staging cleanup member limit')
            checked_path(p)
            if _io_path(p).is_dir():pending.append(p)
    with _pinned_directory(staging_root):
        # A short root can contain long hashed descendants. Recursive APIs
        # must keep extended spelling throughout their own child traversal.
        shutil.rmtree(_io_path(target, recursive=True))
