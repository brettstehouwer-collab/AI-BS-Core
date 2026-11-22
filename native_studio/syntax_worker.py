"""Bounded compile-only scratchpad worker; never imports or executes input."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sys

STORE = Path('C:/AI-BS/saved_data/native_syntax_checks')
MAX_BYTES = 1024 * 1024


def inspect_snapshot(path, expected, *, store=STORE):
    path, store = Path(path), Path(store)
    if (not path.is_absolute() or path.name != 'source.txt'
            or path.parent.parent != store or not re.fullmatch(r'[a-f0-9]{32}', path.parent.name)
            or not re.fullmatch(r'[a-f0-9]{64}', expected)):
        raise ValueError('Invalid syntax snapshot')
    for item in (path, *path.parents):
        info = item.lstat()
        if item.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Redirected snapshot')
    if path.resolve() != path:
        raise ValueError('Noncanonical snapshot')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if info.st_nlink != 1 or info.st_size > MAX_BYTES:
            raise ValueError('Snapshot bound exceeded')
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Snapshot identity mismatch')
    text = raw.decode('utf-8')
    result = {'schema': 1, 'sha256': expected, 'bytes': len(raw), 'executed': False}
    try:
        compile(text, '<scratchpad>', 'exec')
        result['status'] = 'valid'
    except (SyntaxError, ValueError, RecursionError) as error:
        result.update(status='invalid', error=type(error).__name__)
        if isinstance(error, SyntaxError):
            result.update(line=error.lineno, column=error.offset)
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3 or argv[0] != '--scratchpad-syntax-worker':
        return 2
    try:
        result = inspect_snapshot(argv[1], argv[2])
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({'schema': 1, 'status': 'unavailable', 'executed': False}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
