"""Inspect a closed private opening package; launch only with explicit --run."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import types

PACKAGE_ID = 'first-boot-private-review-0172-v31'
PROFILES = ('draft31', 'previous20')
RUNTIME_FILES = frozenset('runtime/' + p for p in (
    'bin/aibs_assetc.exe', 'bin/aibs_capabilities.json', 'bin/aibs_content_host.exe',
    'bin/aibs_creator_host.exe', 'bin/aibs_creator_viewport.exe', 'bin/aibs_motherboard.exe',
    'bin/aibs_player.exe', 'bin/aibs_warm_opening_project.exe',
    'bin/shaders/character.ps.cso', 'bin/shaders/character.vs.cso',
    'bin/shaders/motherboard.ps.cso', 'bin/shaders/motherboard.vs.cso',
    'bin/shaders/shadow.vs.cso', 'bin/shaders/textured.ps.cso', 'bin/shaders/textured.vs.cso',
    'share/AIBS/licenses/Jolt-LICENSE.txt', 'share/AIBS/licenses/SQLite-NOTICE.txt',
    'share/licenses/AIBS/cgltf/LICENSE.txt'))
HELPERS = {'review.py', 'review_driver.py', 'opening_assets.py', 'README.txt',
           'Play_Current_Draft.cmd', 'Play_Previous_Preview.cmd', 'Check_Package.cmd'}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def plain(path, root=None):
    path = Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError('Package paths must not redirect')
    path = path.resolve(strict=True)
    if root is not None and not path.is_relative_to(root):
        raise ValueError('Package member escaped its root')
    return path

def read_json(path, limit=1024 * 1024):
    if not path.is_file() or not 1 <= path.stat().st_size <= limit:
        raise ValueError('Missing or oversized package metadata')
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('Duplicate package metadata key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite package metadata')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=invalid)

def load_module(path, prefix):
    name = prefix + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module

def inspect_package(root, profile='draft31'):
    if profile not in PROFILES:
        raise ValueError('Unknown draft choice')
    root = plain(root)
    metadata = read_json(plain(root / 'package.json', root))
    if (set(metadata) != {'schema_version', 'package_id', 'sdk_version', 'profiles', 'files'}
            or type(metadata['schema_version']) is not int or metadata['schema_version'] != 1
            or metadata['package_id'] != PACKAGE_ID or metadata['sdk_version'] != '0.17.2'
            or type(metadata['profiles']) is not dict or set(metadata['profiles']) != set(PROFILES)
            or type(metadata['files']) is not dict or not 1 <= len(metadata['files']) <= 128):
        raise ValueError('Unexpected private package identity')
    names = set(metadata['files'])
    if not RUNTIME_FILES | HELPERS <= names or {n for n in names if n.startswith('runtime/')} != RUNTIME_FILES:
        raise ValueError('Incomplete or unexpected runtime/helper inventory')
    total = 0
    for name, identity in metadata['files'].items():
        relative = Path(name)
        if not name or '\\' in name or relative.is_absolute() or relative.drive or '..' in relative.parts:
            raise ValueError('Invalid package-relative member')
        if (type(identity) is not dict or set(identity) != {'bytes', 'sha256'}
                or type(identity['bytes']) is not int or not 1 <= identity['bytes'] <= 64 * 1024**2
                or type(identity['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', identity['sha256'])):
            raise ValueError('Invalid package member identity')
        path = plain(root / relative, root)
        if not path.is_file() or path.stat().st_size != identity['bytes'] or digest(path) != identity['sha256']:
            raise ValueError('Package content changed: ' + name)
        total += identity['bytes']
    if total > 512 * 1024**2:
        raise ValueError('Private review package exceeds its bounded size')
    capabilities = read_json(root / 'runtime/bin/aibs_capabilities.json')
    if capabilities.get('sdk_version') != '0.17.2':
        raise ValueError('Runtime SDK metadata differs')
    assets_module = load_module(root / 'opening_assets.py', '_aibs_private_assets_')
    inventories = {}
    expected = set(RUNTIME_FILES) | HELPERS
    for name in PROFILES:
        row = metadata['profiles'][name]
        if (type(row) is not dict or set(row) != {'directory', 'manifest_sha256', 'asset_id'}
                or row['directory'] != 'profiles/' + name):
            raise ValueError('Invalid model profile location')
        assets = assets_module.read_opening_assets(root / row['directory'], verify_pack_contents=True)
        if assets.manifest_sha256 != row['manifest_sha256']:
            raise ValueError('Profile manifest changed')
        adam = next(role for role in assets.roles if role.role == 'adam')
        if adam.asset_id != row['asset_id']:
            raise ValueError('Profile model binding differs')
        prefix = row['directory'] + '/'
        expected.add(prefix + 'opening-assets.json')
        for role in assets.roles:
            expected.update(prefix + p.relative_to(assets.root).as_posix() for p in role.directory.iterdir())
        inventories[name] = assets
    if names != expected:
        raise ValueError('Private package has undeclared or omitted dependencies')
    return root / 'runtime/bin/aibs_motherboard.exe', root / 'runtime/bin/aibs_warm_opening_project.exe', inventories[profile]

def main(argv=None, *, package_root=None):
    if sys.version_info < (3, 12):
        raise RuntimeError('This review launcher needs Python 3.12 or newer')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=PROFILES, default='draft31')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    root = plain(package_root or Path(__file__).parent)
    player, _, assets = inspect_package(root, args.model)
    if not args.run:
        print(json.dumps({'status': 'ready_not_run', 'package_id': PACKAGE_ID, 'sdk': '0.17.2',
                          'model': args.model, 'player': str(player), 'window_started': False,
                          'asset_manifest_sha256': assets.manifest_sha256, 'installed_release_changed': False,
                          'likeness_approved': False, 'human_pacing_accepted': False}))
        return 0
    driver = load_module(root / 'review_driver.py', '_aibs_private_review_driver_')
    driver.resources = lambda: inspect_package(root, args.model)
    driver.SESSIONS = root / 'sessions' / args.model
    driver.ATTEMPTS = root / 'launches' / args.model
    driver.SDK_VERSION = '0.17.2'
    driver.STUDIO_VERSION = 'Private opening review - ' + args.model
    return driver.main(['--run'])

if __name__ == '__main__':
    raise SystemExit(main())
