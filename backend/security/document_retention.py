"""Intake sources and prior versions are immutable through document/Drive mutation APIs."""
import os
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException


def _relative_parts(path: Path, drive_root: Path):
    try:
        return path.absolute().relative_to(drive_root.absolute()).parts
    except ValueError:
        return () if path.absolute() == drive_root.absolute() else None


def _protected_parts(parts):
    return (parts is not None and len(parts) >= 4
            and tuple(p.casefold() for p in parts[:2]) == ('documents', 'drive_intake')
            and parts[3].casefold() in {'originals', 'previous_versions'})


def _retained_ancestor(parts):
    if parts is None:
        return False
    folded = tuple(p.casefold() for p in parts)
    return (not folded or folded == ('documents',) or folded == ('documents', 'drive_intake')
            or len(folded) == 3 and folded[:2] == ('documents', 'drive_intake'))


def document_retention_metadata(path: Path, drive_root: Path) -> dict:
    lexical = _relative_parts(path, drive_root)
    resolved = _relative_parts(path.resolve(), drive_root.resolve())
    protected = _protected_parts(lexical) or _protected_parts(resolved)
    binary = path.suffix.casefold() in {'.pdf', '.doc', '.docx', '.odt'}
    reason = 'Originals and previous versions are preserved. Create a working copy to edit.' if protected else None
    return {'read_only': bool(protected), 'retention_reason': reason, 'binary': binary,
            'editable': not protected and not binary}


def assert_document_write_allowed(path: Path, drive_root: Path, *, encompassing: bool = False):
    """Check lexical and resolved paths and reject mutable reparse-point aliases."""
    path, drive_root = Path(path).absolute(), Path(drive_root).absolute()
    lexical = _relative_parts(path, drive_root)
    resolved = _relative_parts(path.resolve(), drive_root.resolve())
    if (_protected_parts(lexical) or _protected_parts(resolved)
            or encompassing and (_retained_ancestor(lexical) or _retained_ancestor(resolved))):
        raise HTTPException(status_code=403, detail='Retention policy: Originals and Previous_Versions cannot be changed, moved, renamed, or overwritten. Create a unique Working_Copies document instead.')
    # Mutations do not follow links, even if the alias currently points somewhere writable.
    # Read/preview access keeps its existing safe-path behavior.
    cursor = path
    while True:
        if cursor.is_symlink() or getattr(cursor, 'is_junction', lambda: False)():
            raise HTTPException(status_code=403, detail='Retention policy: writes through symbolic links or junctions are not allowed.')
        if cursor == drive_root or cursor.parent == cursor:
            break
        cursor = cursor.parent


def editable_copy_path(source: Path, drive_root: Path, suffix: str, label: str = 'working') -> Path:
    """Choose a fresh working-copy name, keeping intake batch/family/Drive-ID grouping."""
    source, drive_root = Path(source), Path(drive_root)
    parts = _relative_parts(source, drive_root)
    if not _protected_parts(parts):
        parts = _relative_parts(source.resolve(), drive_root.resolve())
    if _protected_parts(parts):
        parent = drive_root.joinpath(*parts[:3], 'Working_Copies', *parts[4:-1])
    else:
        parent = source.parent
    output = parent / f'{source.stem}-{label}-{uuid4().hex}{suffix}'
    assert_document_write_allowed(output, drive_root)
    return output


def safe_drive_leaf(value: str) -> str:
    value = (value or '').strip()
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}
    if (not value or value in {'.', '..'} or value.endswith(('.', ' '))
            or any(ch in value for ch in '<>:"/\\|?*') or any(ord(ch) < 32 for ch in value)
            or value.split('.')[0].upper() in reserved):
        raise HTTPException(status_code=400, detail='Invalid file or folder name.')
    return value
