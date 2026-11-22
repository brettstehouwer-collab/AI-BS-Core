"""Validate generated media references and keep delivery on the protected API."""
from pathlib import Path, PureWindowsPath
import re
import stat
from urllib.parse import parse_qs, urlencode, urlsplit

MEDIA_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.mp4', '.webm', '.mov', '.mkv', '.wav', '.mp3', '.ogg', '.flac', '.m4a', '.glb', '.gltf', '.obj', '.stl', '.ply'}


def _parts(filename, subfolder):
    if not isinstance(filename, str) or not filename or len(filename) > 255:
        raise ValueError('Invalid media filename')
    if any(c in filename for c in '/\\:') or any(ord(c) < 32 for c in filename):
        raise ValueError('Invalid media filename')
    if Path(filename).suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError('Unsupported media format')
    if not isinstance(subfolder, str) or len(subfolder) > 1000 or ':' in subfolder or any(ord(c) < 32 for c in subfolder):
        raise ValueError('Invalid media folder')
    folder = PureWindowsPath(subfolder)
    if folder.is_absolute() or folder.drive or folder.root or '..' in folder.parts:
        raise ValueError('Invalid media folder')
    return filename, '/'.join(folder.parts)


def media_output_path(root, filename, subfolder=''):
    filename, folder = _parts(filename, subfolder)
    root = Path(root).absolute()
    path = root / folder / filename
    if root.resolve() != root or not path.resolve().is_relative_to(root):
        raise ValueError('Media path leaves its store')
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if current.is_symlink() or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
                raise ValueError('Redirected media path')
    return path


def format_media_result(result, prompt='Generated media'):
    """Only confirmed successes with valid output references can create cards."""
    if isinstance(result, dict) and result.get('status') in {'queued', 'pending', 'running'}:
        return 'Media generation is still processing. No completed file is available yet. Check this job before submitting another request.'
    if not isinstance(result, dict) or result.get('status') != 'success':
        return 'Media generation did not complete. No new media is available. Check the media service and job status before trying again.'
    try:
        reference = result.get('image_url')
        query = {}
        if reference:
            if not isinstance(reference, str):
                raise ValueError('Invalid media reference')
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or parsed.path != '/api/comfy/media':
                raise ValueError('Invalid media reference')
            query = parse_qs(parsed.query)
        filename = result.get('filename') or query.get('filename', [''])[0]
        folder = result.get('subfolder', query.get('subfolder', [''])[0])
        filename, folder = _parts(filename, folder)
        url = '/api/comfy/media?' + urlencode({'filename': filename, 'subfolder': folder, 'type': 'output'})
    except (ValueError, TypeError, IndexError):
        return 'Media generation returned no valid output file. No preview or download is available.'
    alt = re.sub(r'[\r\n\[\]"\'`<>]+', ' ', str(prompt)).strip()[:70] or 'Generated media'
    extension = Path(filename).suffix.lower()
    preview = f'![{alt}]({url})\n\n' if extension not in {'.glb', '.gltf', '.obj', '.stl', '.ply'} else ''
    return f'**Generated media:**\n\n{preview}[Download / open media]({url})'
