"""Repeatable, source-only backend inventory. No application imports or live checks.

Import/mount resolution lists candidates: conditions, rebinding, startup failures,
dispatch order, middleware and handler behavior still require separate review.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path

from workspace.reviews.security_route_inventory import inspect_source

EXCLUDED = {'tests', '__pycache__', '.venv', 'venv', 'node_modules', 'dist',
            'build', 'backups', '.git', 'site-packages'}
MAX_FILES = 5000


def _module_file(root, parts):
    if parts and parts[0] == 'backend':
        parts = parts[1:]
    candidate = root.joinpath('backend', *parts)
    for path in (candidate.with_suffix('.py'), candidate / '__init__.py'):
        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to((root / 'backend').resolve()):
            return path.relative_to(root).as_posix()
    return None


def _imports(tree, relative, root):
    """Map aliases to possible local modules without importing any of them."""
    aliases = defaultdict(set)
    package = list(Path(relative).parts[1:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module.split('.') if node.module else []
            if node.level:
                base = package[:len(package) - node.level + 1] + base
            for alias in node.names:
                if alias.name == '*':
                    continue
                local = alias.asname or alias.name
                for parts in (base + alias.name.split('.'), base):
                    file = _module_file(root, parts)
                    if file:
                        aliases[local].add(file)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                file = _module_file(root, alias.name.split('.'))
                if file:
                    aliases[alias.asname or alias.name.split('.')[0]].add(file)
    return aliases


def collect_backend(root):
    root = Path(root).absolute()
    backend = root / 'backend'
    if not backend.is_dir() or backend.is_symlink() or getattr(backend, 'is_junction', lambda: False)():
        raise ValueError('A non-redirected backend directory is required')
    paths = []
    for directory, folders, filenames in os.walk(backend, followlinks=False):
        folders[:] = sorted(name for name in folders if name not in EXCLUDED
                            and not (Path(directory) / name).is_symlink()
                            and not getattr(Path(directory) / name, 'is_junction', lambda: False)())
        paths.extend(Path(directory) / name for name in sorted(filenames)
                     if name.endswith('.py') and not name.startswith('test_')
                     and not name.endswith('_test.py') and not (Path(directory) / name).is_symlink())
        if len(paths) > MAX_FILES:
            raise ValueError('Source inventory file bound exceeded')
    pins, routes, mounts, errors = [], [], [], []
    for path in sorted(paths):
        report = inspect_source(path, root)
        relative = report['file']
        pins.append({key: report[key] for key in ('file', 'bytes', 'sha256', 'parse_status')})
        if report['parse_status'] != 'ok':
            errors.append({'file': relative, 'error_type': report['error_type']})
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != report['sha256']:
            raise ValueError('Source changed during inventory: ' + relative)
        aliases = _imports(ast.parse(raw.decode('utf-8-sig')), relative, root)
        for route in report['routes']:
            routes.append({'file': relative, **route})
        for mount in sorted(report['mounts'], key=lambda item: item['line']):
            symbol = mount['router_symbol']
            candidates = sorted(aliases.get(symbol.split('.')[0], set())) if symbol else []
            if symbol and symbol.split('.')[0] in {r['owner_symbol'] for r in report['routes']}:
                candidates = sorted(set(candidates + [relative]))
            mounts.append({'file': relative, **mount, 'candidate_router_files': candidates,
                           'resolution': 'candidate' if candidates else 'unresolved',
                           'runtime_registration_verified': False})
    groups = defaultdict(list)
    for mount in mounts:
        if mount['router_symbol'] is not None:
            groups[(mount['file'], mount['target_symbol'], mount['router_symbol'], mount['prefix'])].append(mount['line'])
    repeated = [{'file': key[0], 'target_symbol': key[1], 'router_symbol': key[2],
                 'prefix': key[3], 'lines': lines, 'dispatch_collision_verified': False}
                for key, lines in sorted(groups.items(), key=lambda pair: str(pair[0])) if len(lines) > 1]
    return {'schema_version': 1, 'evidence': 'source_declared',
            'runtime_registration_verified': False, 'authorization_verified': False,
            'complete_source_parse': not errors, 'source_file_count': len(pins),
            'declared_route_count': len(routes), 'mount_count': len(mounts),
            'parse_errors': errors, 'source_pins': pins, 'routes': routes,
            'mounts': mounts, 'repeated_mount_candidates': repeated,
            'limits': ['Static declarations do not prove live registration, authorization or functionality.',
                       'Conditional imports and aliases may be rebound; candidates require review.',
                       'Tests, dependencies, builds, private data and non-Python gateways are excluded.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = collect_backend(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('source_file_count', 'declared_route_count', 'mount_count', 'complete_source_parse')}))


if __name__ == '__main__':
    main()
