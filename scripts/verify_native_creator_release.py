"""Verify a frozen native creator release without importing or executing its app.

Run with the same Python minor version used by PyInstaller. The freeze plan and
its staged source are the reference; mutable workspace source is never read.
This verifies static packaging evidence, not runtime behavior, signing, or web parity.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import marshal
from pathlib import Path, PurePosixPath
import re
import struct
import types
import zipfile

GAME_MODULES = frozenset('native_studio.game_engine' + suffix for suffix in (
    '', '.project_model', '.creator_wire', '.creator_viewport', '.creator_view',
    '.creator_payload', '.creator_commands', '.creator_client', '.content_view',
    '.content_proposals', '.content_preview', '.content_play', '.content_jobs',
    '.content_commands', '.content_client', '.content_ai'))
REQUIRED_MODULES = GAME_MODULES | {
    'native_studio', 'native_studio.app', 'native_studio.game_build_view',
    'native_studio.game_build_monitor', 'native_studio.game_release_smoke'}
ALLOWED_ASSETS = frozenset({
    'version.txt', 'game_release.json', 'assets/psychedelic_theme.jpg', 'assets/favicon.ico',
    'game_assets/playground/index.html', 'game_assets/playground/vendor/three-r128.min.js',
    'game_assets/playground/vendor/THREE-LICENSE.txt',
    *('game_assets/player/' + name for name in (
        'aibs_player.exe', 'aibs_motherboard.exe', 'aibs_creator_host.exe',
        'aibs_content_host.exe', 'aibs_creator_viewport.exe', 'aibs_capabilities.json',
        'shaders/motherboard.vs.cso', 'shaders/motherboard.ps.cso',
        'Jolt-LICENSE.txt', 'SQLite-NOTICE.txt'))})
TERMINAL_HELPER_FILES = {
    'native_studio/ai_bs_ide_terminal.py': 'native_helpers/ai_bs_ide_terminal.py',
    'native_studio/owned_process.py': 'native_helpers/owned_process.py',
}
TERMINAL_HELPER_MODULES = frozenset({'native_studio.ai_bs_ide_terminal', 'native_studio.owned_process'})


def validate_terminal_helper_profile(plan, modules, metadata=None):
    """Require only the two reviewed DATA sources when terminal UI is included.

    Older held releases without the terminal module retain their original asset
    contract. Backend packages and arbitrary source DATA remain unadmitted.
    """
    included = 'native_studio.ai_bs_ide_terminal' in modules
    declared = plan.get('nativeTerminalHelpersIncluded', False)
    if type(declared) is not bool or declared != included:
        raise ValueError('Terminal helper inclusion must match the frozen native modules')
    if included and not TERMINAL_HELPER_MODULES.issubset(modules):
        raise ValueError('Terminal helper requires reviewed native owned-process mechanics')
    if metadata is not None and (included or 'native_terminal_helpers_included' in metadata):
        value = metadata.get('native_terminal_helpers_included')
        if type(value) is not bool or value != included:
            raise ValueError('Terminal helper metadata differs from the frozen inclusion profile')
    return included


WARM_PLAYER_FILES = ('shaders/textured.vs.cso','shaders/textured.ps.cso','shaders/shadow.vs.cso',
                     'shaders/character.vs.cso','shaders/character.ps.cso','aibs_assetc.exe','cgltf-LICENSE.txt')
PRIVATE_SUFFIXES = frozenset({
    '.db', '.sqlite', '.sqlite3', '.pfx', '.p12', '.key', '.iso', '.aibs',
    '.gguf', '.ggml', '.safetensors', '.ckpt', '.pth', '.pt', '.onnx', '.h5', '.hdf5',
    '.bin', '.model', '.tflite'})
PRIVATE_PARTS = frozenset({
    'backend', 'memoir', 'memoirs', 'credentials', '.ssh', '.aws', '.azure',
    'model_weights', 'ollama', 'agent_sync', 'contacts'})
SECRET_PATTERN = re.compile(
    rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|'
    rb'ghp_[A-Za-z0-9]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|'
    rb'AIzaSy[A-Za-z0-9_-]{25,}|Bearer\s+eyJ[A-Za-z0-9_-]+\.')
ASSET_VIEW_MODULE = 'native_studio.game_engine.asset_view'
PLACEMENT_MODULES = frozenset({'native_studio.game_engine.project_assets','native_studio.placement_release_smoke'})
REFERENCE_PREFIX = 'game_assets/reference_part/'
SAVED_PLAY_CAPABILITY = 'chapter-saved-play-v1'
SAVED_PLAY_MODULES = frozenset('native_studio.game_engine.' + name for name in
    ('saved_play', 'saved_play_storage', 'saved_chapter_export'))
SAVED_PLAY_FEATURES = frozenset((SAVED_PLAY_CAPABILITY, 'durable_world', 'first_boot_chapter',
    'first_boot_content_play', 'chapter_content_export_v2', 'chapter_content_v3',
    'chapter_asset_surfaces', 'mesh_asset_v1', 'character_asset_v2', 'audio_asset_v2',
    'chapter-memory-audio-v1', 'chapter-authored-inspections-v1', 'chapter-initial-view-v1',
    'chapter-workshop-commissioning-v1'))


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate reference provenance JSON key')
        result[key] = value
    return result


def read_native_capabilities(path: Path) -> dict:
    """Read a bounded SDK declaration without executing its binaries."""
    path=checked(path,path.parent)
    with path.open('rb') as stream:encoded=stream.read(16*1024+1)
    if len(encoded)>16*1024:raise ValueError('Native SDK capability declaration exceeds 16 KiB')
    data=json.loads(encoded.decode('utf-8-sig'),object_pairs_hook=_unique_pairs)
    if (type(data) is not dict or type(data.get('schema_version')) is not int or data['schema_version']!=1
            or type(data.get('features')) is not dict
            or any(type(key) is not str or not key or type(value) is not bool for key,value in data['features'].items())):
        raise ValueError('Invalid native SDK capability declaration')
    if data['features'].get('chapter_asset_placement_v1') is True:
        version=data.get('sdk_version')
        if type(version) is not str or not re.fullmatch(r'\d+\.\d+\.\d+',version) or tuple(map(int,version.split('.')))<(0,10,0):
            raise ValueError('Persistent placement capability requires SDK 0.10.0 or newer')
    return data


def placement_capable(capabilities: dict) -> bool:
    return capabilities.get('features',{}).get('chapter_asset_placement_v1') is True


def warm_asset_profile(capabilities: dict) -> bool:
    version=capabilities.get('sdk_version','')
    return type(version) is str and re.fullmatch(r'\d+\.\d+\.\d+',version) is not None and tuple(map(int,version.split('.')))>=(0,11,0)


def require_saved_play_capabilities(capabilities: dict) -> None:
    """Static complete016 profile only; no native runtime/inference claim."""
    version = capabilities.get('sdk_version')
    features = capabilities.get('features')
    if (type(capabilities.get('schema_version')) is not int or capabilities['schema_version'] != 1
            or capabilities.get('target') != 'windows-x64' or type(version) is not str
            or re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version) is None
            or tuple(map(int, version.split('.'))) < (0, 16, 0)
            or type(features) is not dict
            or any(type(key) is not str or not key or type(value) is not bool for key,value in features.items())
            or any(features.get(key) is not True for key in SAVED_PLAY_FEATURES)):
        raise ValueError('Saved chapter play requires the complete Windows SDK0.16 capability profile')


def saved_play_capable(capabilities: dict) -> bool:
    try:
        require_saved_play_capabilities(capabilities)
        return True
    except ValueError:
        return False


def validate_saved_play_profile(plan: dict, capabilities: dict, modules, metadata: dict | None = None) -> tuple[bool, bool]:
    """Bind frozen intent, actual runtime capability and all three client files.

    Historical profiles may omit the fields while the feature is unavailable.
    A complete016 release cannot hide it by omitting either explicit field.
    """
    fields = ('requireSavedPlay', 'savedChapterPlayIncluded')
    for key in fields:
        if key in plan and type(plan[key]) is not bool:
            raise ValueError('Saved chapter release flags must be typed booleans')
    required = plan.get(fields[0], False)
    included = plan.get(fields[1], False)
    player = plan.get('includePlayer') is True
    capable = player and saved_play_capable(capabilities)
    if required:
        if not player:
            raise ValueError('Required saved chapter play needs the complete native player')
        require_saved_play_capabilities(capabilities)
    if capable or included or required:
        if any(key not in plan for key in fields):
            raise ValueError('Saved chapter release requires explicit inclusion and requirement flags')
        if not SAVED_PLAY_MODULES.issubset(modules):
            raise ValueError('Missing required saved chapter client modules: ' + ', '.join(sorted(SAVED_PLAY_MODULES-set(modules))))
    if included is not capable:
        raise ValueError('Saved chapter inclusion differs from its actual complete SDK capability profile')
    if metadata is not None:
        names = ('require_saved_play', 'saved_chapter_play_included')
        explicit = any(key in plan for key in fields) or any(key in metadata for key in names) or capable
        if explicit and (any(key not in metadata or type(metadata[key]) is not bool for key in names)
                or (metadata[names[0]], metadata[names[1]]) != (required, included)):
            raise ValueError('Saved chapter release metadata flags differ from the frozen requirement/inclusion profile')
    return required, included


def validate_reference_pack(root: Path, expected: dict | None = None) -> dict:
    """Check the exact public sample/envelope; never execute the native decoder.

    Geometry validation and actual rendering require separate native runtime
    evidence. The cooked file's outer SHA, envelope checksum and public
    provenance binding are checked here before any package can be admitted.
    """
    root = Path(root).absolute()
    for part in (root, *root.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Redirected reference asset pack is not admitted')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Reference asset pack must be an existing directory')

    def bounded(name, maximum):
        path = checked(root / name, root)
        if not 0 < path.stat().st_size <= maximum:
            raise ValueError('Reference asset file exceeds its byte bound: ' + name)
        with path.open('rb') as stream:
            data = stream.read(maximum + 1)
        if not 0 < len(data) <= maximum:
            raise ValueError('Reference asset changed/exceeds its byte bound')
        return data

    catalog = bounded('catalog.aibcat', 1024 * 1024)
    record = re.fullmatch(rb'AIBCAT 1\n([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}) ([0-9a-f]{64}) ([0-9a-f]{64}\.aibmesh)\n', catalog)
    if record is None:
        raise ValueError('Reference catalog requires exactly one canonical UUID/digest record')
    identity, sha, filename = (value.decode('ascii') for value in record.groups())
    result = {'asset_id': identity, 'sha256': sha, 'file': filename}
    if filename != sha + '.aibmesh' or (expected is not None and result != expected):
        raise ValueError('Reference catalog digest/identity differs from its declared source plan')
    if {path.name for path in root.iterdir()} != {'catalog.aibcat', filename, 'LICENSE.txt', 'provenance.json'}:
        raise ValueError('Reference pack must contain exactly four declared public files')
    mesh = bounded(filename, 32 * 1024 * 1024)
    if hashlib.sha256(mesh).hexdigest() != sha:
        raise ValueError('Reference mesh digest differs from its catalog')
    if (len(mesh) < 48 or mesh[:8] != b'AIBMesh1' or
            struct.unpack('<II', mesh[8:16]) != (1, len(mesh) - 48) or
            mesh[16:48] != hashlib.sha256(mesh[48:]).digest()):
        raise ValueError('Reference mesh has an invalid versioned envelope/checksum')
    license_bytes = bounded('LICENSE.txt', 65536)
    if not license_bytes.decode('utf-8').strip() or b'\0' in license_bytes:
        raise ValueError('Reference license must be explicit bounded public text')
    provenance_bytes = bounded('provenance.json', 65536)
    if SECRET_PATTERN.search(license_bytes + provenance_bytes):
        raise ValueError('Private credentials are not reference asset data')
    info = json.loads(provenance_bytes.decode('utf-8'), object_pairs_hook=_unique_pairs)
    keys = {'schema_version', 'asset_id', 'name', 'source', 'materials', 'license',
            'license_review', 'importer', 'options', 'cooked'}
    if (type(info) is not dict or set(info) != keys or type(info['schema_version']) is not int
            or info['schema_version'] != 1 or info['asset_id'] != identity or
            type(info['name']) is not str or not 0 < len(info['name'].encode('utf-8')) <= 4096 or
            any(ord(c) < 32 or ord(c) == 127 for c in info['name']) or
            re.search(r'[A-Za-z]:[\\/]|\\\\', info['name'])):
        raise ValueError('Reference provenance contains unknown/private fields or invalid identity')
    for key, maximum in (('source', 32 * 1024 * 1024), ('materials', 65536), ('license', 65536)):
        value = info[key]
        if (type(value) is not dict or set(value) != {'sha256', 'bytes'} or
                type(value['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', value['sha256']) or
                type(value['bytes']) is not int or not 0 < value['bytes'] <= maximum):
            raise ValueError('Reference provenance must contain bounded hashes only; no private source paths')
    if (info['license'] != {'sha256': hashlib.sha256(license_bytes).hexdigest(), 'bytes': len(license_bytes)} or
            info['cooked'] != {'file': filename, 'sha256': sha, 'bytes': len(mesh)} or
            info['importer'] != {'name': 'aibs-obj', 'format_version': 1} or
            type(info['importer']['format_version']) is not int or
            info['license_review'] != 'Supplied declaration copied verbatim; ownership/permission not inferred' or
            info['options'] != {'units': 'meters', 'up_axis': '+Y', 'axis_conversion': 'none',
                'material_model': 'opaque-base-color-emission-v1',
                'external_material_libraries': 'ignored-explicit-material-table-only'}):
        raise ValueError('Reference provenance license/cooked/importer contract mismatch')
    return result


OPENING_PREFIX = 'game_assets/opening/'
OPENING_FACTORY = 'game_assets/player/aibs_warm_opening_project.exe'
OPENING_MODULES = frozenset({'native_studio.game_engine.opening_assets', 'native_studio.game_engine.opening_project'})
OPENING_ROLES = ('capacitor', 'adam', 'nook', 'fault', 'bypass', 'shelter')


def require_opening_capabilities(capabilities: dict) -> None:
    version = capabilities.get('sdk_version', '')
    required = ('chapter_content_v3', 'character_asset_v2', 'chapter-initial-view-v1',
                'chapter-workshop-commissioning-v1')
    if (type(version) is not str or re.fullmatch(r'\d+\.\d+\.\d+', version) is None
            or tuple(map(int, version.split('.'))) < (0, 15, 0)
            or any(capabilities.get('features', {}).get(key) is not True for key in required)):
        raise ValueError('Curated opening requires the complete SDK0.15 workshop capability set')


def require_opening_payload_capabilities(capabilities: dict, opening: dict) -> None:
    # Legacy declarations retain their exact shape and SDK0.15 baseline.
    if opening.get('character_payload_version',2)==3:
        version=capabilities.get('sdk_version','')
        if (type(version) is not str or re.fullmatch(r'\d+\.\d+\.\d+',version) is None
                or tuple(map(int,version.split('.')))<(0,17,0)):
            raise ValueError('Character surface payload3 requires SDK0.17.0 or newer')


def validate_opening_bundle(root: Path, expected: dict | None = None) -> dict:
    """Independently verify the curated envelope without importing client code.

    Native geometry/image/skin decoding and GPU residency remain separate runtime
    acceptance. This checks bounded bytes, typed envelopes, provenance and exact
    immutable pack identities before any staging write.
    """
    root = checked(Path(root).absolute(), Path(root).absolute(), file=False)
    encoded_total = 0
    def bounded(path, maximum):
        nonlocal encoded_total
        path = checked(path, root)
        size = path.stat().st_size
        if not 0 < size <= maximum or size > 128 * 1024 * 1024 - encoded_total:
            raise ValueError('Opening asset exceeds its explicit byte bound')
        with path.open('rb') as stream:
            raw = stream.read(maximum + 1)
        if len(raw) != size or not 0 < len(raw) <= maximum or len(raw) > 128 * 1024 * 1024 - encoded_total:
            raise ValueError('Opening asset changed or exceeds its bound')
        encoded_total += len(raw)
        return raw
    def json_value(raw):
        def reject(value):
            raise ValueError('Nonfinite opening JSON value: ' + value)
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_pairs, parse_constant=reject)
    manifest_bytes = bounded(root / 'opening-assets.json', 16 * 1024)
    manifest = json_value(manifest_bytes)
    if (type(manifest) is not dict or set(manifest) != {'version', 'roles'}
            or type(manifest['version']) is not int or manifest['version'] != 1
            or type(manifest['roles']) is not dict or set(manifest['roles']) != set(OPENING_ROLES)):
        raise ValueError('Opening manifest requires exactly six typed roles and version1')
    files = {'opening-assets.json': manifest_bytes}
    directories = set()
    kinds = {}
    character_payload_version=2
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    digest_pattern = r'[0-9a-f]{64}'
    for role in OPENING_ROLES:
        entry = manifest['roles'][role]
        if type(entry) is not dict or set(entry) != {'directory', 'asset_id', 'asset_sha256', 'pack_sha256'}:
            raise ValueError('Invalid opening role declaration: ' + role)
        directory = safe_relative(entry['directory'])
        if not directory.startswith('packs/') or len(directory) > 256 or len(directory.split('/')) > 5 or directory in directories or any(ord(c) < 32 for c in directory):
            raise ValueError('Opening role requires a unique project-owned pack directory')
        directories.add(directory)
        if (type(entry['asset_id']) is not str or re.fullmatch(uuid_pattern, entry['asset_id']) is None
                or any(type(entry[k]) is not str or re.fullmatch(digest_pattern, entry[k]) is None
                       for k in ('asset_sha256', 'pack_sha256'))):
            raise ValueError('Opening role requires canonical UUID and digests')
        pack = checked(root / directory, root, file=False)
        catalog = bounded(pack / 'catalog.aibcat', 1024 * 1024)
        options = [('mesh', b'AIBCAT 1\n', '.aibmesh', b'AIBMesh1', 1),
                   ('surface', b'AIBCAT 2\nsurface ', '.aibsurf', b'AIBSurf2', 2),
                   ('character', b'AIBCAT 2\ncharacter ', '.aibchar', b'AIBChar2', 2)]
        match = next((option for option in options if catalog.startswith(option[1])), None)
        if match is None or (role == 'adam') != (match[0] == 'character'):
            raise ValueError('Opening role/catalog type mismatch: ' + role)
        kind, header, suffix, magic, version = match
        allowed_versions=(2,3) if kind=='character' else (version,)
        filename = entry['asset_sha256'] + suffix
        canonical = header + (entry['asset_id'] + ' ' + entry['asset_sha256'] + ' ' + filename + '\n').encode('ascii')
        if catalog != canonical or {p.name for p in pack.iterdir()} != {'catalog.aibcat', filename, 'LICENSE.txt', 'provenance.json'}:
            raise ValueError('Opening pack must contain exactly its four canonical cooker files')
        payload = bounded(pack / filename, 32 * 1024 * 1024)
        if (hashlib.sha256(payload).hexdigest() != entry['asset_sha256'] or len(payload) < 48
                or payload[:8] != magic or struct.unpack_from('<I',payload,8)[0] not in allowed_versions
                or struct.unpack_from('<I',payload,12)[0] != len(payload)-48
                or payload[16:48] != hashlib.sha256(memoryview(payload)[48:]).digest()):
            raise ValueError('Opening cooked payload envelope/digest mismatch')
        license_bytes = bounded(pack / 'LICENSE.txt', 65536)
        provenance = bounded(pack / 'provenance.json', 65536)
        if not license_bytes.decode('utf-8').strip() or b'\0' in license_bytes or SECRET_PATTERN.search(license_bytes + provenance):
            raise ValueError('Opening pack requires explicit text license without credential material')
        info = json_value(provenance)
        if (type(info) is not dict or type(info.get('schema_version')) is not int
                or info['schema_version'] not in (1, 2) or info.get('asset_id') != entry['asset_id']
                or type(info.get('cooked')) is not dict
                or any(info['cooked'].get(k) != v for k, v in {'file': filename, 'sha256': entry['asset_sha256'], 'bytes': len(payload)}.items())
                or info.get('license') != {'sha256': hashlib.sha256(license_bytes).hexdigest(), 'bytes': len(license_bytes)}):
            raise ValueError('Opening provenance/cooked/license identity mismatch')
        raw_files = {'catalog.aibcat': catalog, filename: payload, 'LICENSE.txt': license_bytes, 'provenance.json': provenance}
        pack_bytes = sum(map(len, raw_files.values()))
        if pack_bytes > 33 * 1024 * 1024:
            raise ValueError('Opening pack exceeds33MiB complete-pack bound')
        pack_manifest = ('AIBPACK ' + ('1' if kind == 'mesh' else '2') + '\n')
        for name, raw in sorted(raw_files.items()):
            pack_manifest += name + ' ' + str(len(raw)) + ' ' + hashlib.sha256(raw).hexdigest() + '\n'
            files[directory + '/' + name] = raw
        if hashlib.sha256(pack_manifest.encode('utf-8')).hexdigest() != entry['pack_sha256']:
            raise ValueError('Opening immutable pack digest mismatch')
        kinds[role] = kind
        if kind=='character':character_payload_version=struct.unpack_from('<I',payload,8)[0]
    total = sum(map(len, files.values()))
    if total > 128 * 1024 * 1024:
        raise ValueError('Opening dependency envelope exceeds128MiB')
    observed = set()
    for index, path in enumerate(root.rglob('*')):
        if index > 512 or path.is_symlink() or path.is_junction():
            raise ValueError('Opening bundle contains redirected/excessive entries')
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            observed.add(relative)
        elif not path.is_dir() or not any(name.startswith(relative + '/') for name in files):
            raise ValueError('Opening bundle has an undeclared directory')
    if observed != set(files):
        raise ValueError('Opening bundle contains missing/undeclared files')
    result = {'version': 1, 'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
              'roles': manifest['roles'], 'kinds': kinds, 'total_bytes': total,
              'files': [{'relative': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                        for name, raw in sorted(files.items())],
              'native_decoded_validation_claimed': False}
    if character_payload_version==3:result['character_payload_version']=3
    if expected is not None and result != expected:
        raise ValueError('Opening bundle differs from its frozen source declaration')
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def safe_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value or
            value.startswith('/') or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Invalid relative path in freeze plan')
    return PurePosixPath(value).as_posix()


def checked(path: Path, boundary: Path, *, file: bool = True) -> Path:
    absolute = path.absolute()
    base = boundary.absolute()
    absolute.relative_to(base)
    current = absolute
    while True:
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError('Redirected package/staged path is not admitted')
        if current == base:
            break
        current = current.parent
    resolved = absolute.resolve(strict=True)
    resolved.relative_to(base.resolve(strict=True))
    if file and not resolved.is_file():
        raise ValueError('Regular package/staged file required')
    if not file and not resolved.is_dir():
        raise ValueError('Package/staged directory required')
    return resolved


UI_MODULES = frozenset({'ui_modernization', 'ui_modernization.components',
    'ui_modernization.components.native_badge', 'ui_modernization.generated',
    'ui_modernization.generated.native_palette', 'ui_modernization.generated.studio_overview'})
UI_NAMESPACE_MODULES = frozenset({'ui_modernization.generated'})


def module_relative(module: str) -> str | None:
    if (not isinstance(module, str) or not re.fullmatch(r'(?:native_studio|ui_modernization)(?:\.[A-Za-z_]\w*)*', module)
            or any(part.startswith(('test_', 'sign_', 'scratch_', 'build_')) for part in module.split('.'))):
        raise ValueError('Only declared native application modules are admitted')
    if module.startswith('ui_modernization') and module not in UI_MODULES:
        raise ValueError('Unreviewed UI modernization source module')
    if module in UI_NAMESPACE_MODULES:
        return None
    if module in ('native_studio', 'native_studio.game_engine', 'ui_modernization', 'ui_modernization.components'):
        return module.replace('.', '/') + '/__init__.py'
    return module.replace('.', '/') + '.py'


def verify_local_import_closure(source: Path, module_paths: dict[str, str], modules: set[str]) -> int:
    """Reject missing declared local dependencies using staged ASTs, without imports."""
    dependencies = set()
    def owned(name):
        return name.split('.')[0] in {'native_studio', 'ui_modernization'}
    def require_module(name):
        pieces = name.split('.')
        for end in range(1, len(pieces) + 1):
            dependency = '.'.join(pieces[:end])
            module_relative(dependency)
            if dependency not in modules:
                raise ValueError('Missing declared local import: ' + dependency)
            dependencies.add(dependency)
    for relative, module in module_paths.items():
        package = module if relative.endswith('/__init__.py') else module.rpartition('.')[0]
        for node in ast.walk(ast.parse((source / relative).read_text(encoding='utf-8-sig'), filename=relative)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if owned(alias.name):
                        require_module(alias.name)
            elif isinstance(node, ast.ImportFrom):
                target = node.module or ''
                if node.level:
                    parts = package.split('.')
                    if node.level > len(parts):
                        raise ValueError('Relative application import escaped its package')
                    target = '.'.join(parts[:len(parts) - node.level + 1] + ([target] if target else []))
                if target and owned(target):
                    require_module(target)
                    for alias in node.names:
                        child = target + '.' + alias.name
                        path = source / child.replace('.', '/')
                        if alias.name != '*' and (child in UI_MODULES or path.is_dir() or path.with_suffix('.py').is_file()):
                            require_module(child)
    return len(dependencies)


def private_reason(relative: str) -> str | None:
    path = PurePosixPath(relative)
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if (parts & PRIVATE_PARTS or name == '.env' or name.startswith('.env.') or
            name in {'agents.md', 'codex_handoff.md', 'ai_bs_master_architectural_ledger.md'}):
        return 'private source/input path'
    if path.suffix.lower() in PRIVATE_SUFFIXES:
        return 'private/archive/model artifact'
    return None


def read_pe_metadata(executable: Path) -> dict:
    """Read Windows PE resources using pefile; do not load the executable."""
    import pefile
    with pefile.PE(str(executable), fast_load=False) as pe:
        if not getattr(pe, 'VS_FIXEDFILEINFO', None):
            raise ValueError('Studio PE has no fixed Windows version resource')
        info = pe.VS_FIXEDFILEINFO[0]
        def components(ms, ls):
            return [ms >> 16, ms & 65535, ls >> 16, ls & 65535]
        strings = {}
        for group in getattr(pe, 'FileInfo', []):
            for entry in group:
                for table in getattr(entry, 'StringTable', []):
                    for key, value in table.entries.items():
                        key = key.decode('utf-8') if isinstance(key, bytes) else key
                        value = value.decode('utf-8') if isinstance(value, bytes) else value
                        if key in strings and strings[key] != value:
                            raise ValueError('Conflicting PE version string resources')
                        strings[key] = value
        return {'machine': pe.FILE_HEADER.Machine, 'subsystem': pe.OPTIONAL_HEADER.Subsystem,
                'file_version': components(info.FileVersionMS, info.FileVersionLS),
                'product_version': components(info.ProductVersionMS, info.ProductVersionLS),
                'strings': strings}


def read_frozen_archive(executable: Path, modules: list[str]) -> dict:
    """Unmarshal code for comparison only. No eval, exec, or application import."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    archive = CArchiveReader(str(executable))
    pyz_entries = [name for name, row in archive.toc.items() if row[-1] == 'z']
    if len(pyz_entries) != 1:
        raise ValueError('Exactly one embedded PYZ archive is required')
    entry = archive.toc[pyz_entries[0]]
    pyz = ZlibArchiveReader(str(executable), archive._start_offset + entry[0], check_pymagic=True)
    missing = set(modules) - set(pyz.toc)
    if missing:
        raise ValueError('Missing frozen modules: ' + ', '.join(sorted(missing)))
    if 'app' not in archive.toc or archive.toc['app'][-1] != 's':
        raise ValueError('Missing native app entry script')
    return {'names': set(pyz.toc), 'namespace_packages': {name for name in modules if pyz.toc[name][0] == 3}, 'code': {name: pyz.extract(name) for name in modules},
            'entry_code': marshal.loads(archive.extract('app'))}


def collection_paths(work: Path) -> tuple[set[str], str]:
    """Read PyInstaller's literal collection manifest to detect extra loose files."""
    path = checked(work / 'pyinstaller/AI_BS_GameRelease/COLLECT-00.toc', work)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Collection manifest exceeds static audit bound')
    content = ast.literal_eval(path.read_text(encoding='utf-8'))
    if not isinstance(content, tuple) or len(content) != 1 or not isinstance(content[0], list):
        raise ValueError('Unexpected PyInstaller collection manifest shape')
    paths = set()
    for row in content[0]:
        if not isinstance(row, tuple) or len(row) != 3 or row[2] not in {'EXECUTABLE', 'BINARY', 'EXTENSION', 'DATA'}:
            raise ValueError('Unexpected PyInstaller collection entry')
        relative = safe_relative(row[0].replace('\\', '/'))
        packaged = relative if row[2] == 'EXECUTABLE' else '_internal/' + relative
        if packaged in paths:
            raise ValueError('Duplicate package collection entry')
        paths.add(packaged)
    return paths, digest(path)


def code_fingerprint(code: types.CodeType) -> str:
    """Fingerprint all semantic/debug code fields except build-machine filenames."""
    def constant(value):
        if isinstance(value, types.CodeType):
            return ['code', structure(value)]
        if isinstance(value, tuple):
            return ['tuple', [constant(item) for item in value]]
        if isinstance(value, frozenset):
            items = [constant(item) for item in value]
            return ['frozenset', sorted(items, key=lambda item: json.dumps(item, sort_keys=True))]
        if isinstance(value, bytes):
            return ['bytes', value.hex()]
        if isinstance(value, float):
            return ['float', value.hex()]
        if isinstance(value, complex):
            return ['complex', value.real.hex(), value.imag.hex()]
        if value is Ellipsis:
            return ['ellipsis']
        return [type(value).__name__, value]
    def structure(value):
        if not isinstance(value, types.CodeType):
            raise ValueError('Frozen module did not contain a code object')
        fields = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals',
                  'co_stacksize', 'co_flags', 'co_code', 'co_names', 'co_varnames',
                  'co_freevars', 'co_cellvars', 'co_name', 'co_qualname', 'co_firstlineno',
                  'co_linetable', 'co_exceptiontable', 'co_consts')
        return {field: constant(getattr(value, field)) for field in fields}
    return hashlib.sha256(json.dumps(structure(code), sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def verify_generated_cache(path: Path, source: Path, rows: dict) -> dict:
    """Admit only a complete, current-interpreter cache of exact declared source."""
    relative = path.relative_to(source).as_posix()
    if path.suffix != '.pyc' or path.parent.name != '__pycache__':
        raise ValueError('Undeclared staged input is not a generated cache: ' + relative)
    cache = checked(path, source)
    try:
        original = Path(importlib.util.source_from_cache(str(cache)))
    except ValueError as error:
        raise ValueError('Invalid staged cache path: ' + relative) from error
    source_relative = original.relative_to(source).as_posix()
    if (source_relative not in rows or not source_relative.endswith('.py') or
            Path(importlib.util.cache_from_source(str(original), optimization='')) != cache):
        raise ValueError('Cache is not for declared source/current Python tag: ' + relative)
    original = checked(original, source)
    original_bytes = original.read_bytes()
    row = rows[source_relative]
    if len(original_bytes) != row['bytes'] or digest(original) != row['sha256']:
        raise ValueError('Staged source for generated cache changed: ' + relative)
    data = cache.read_bytes()
    if len(data) < 16 or data[:4] != importlib.util.MAGIC_NUMBER:
        raise ValueError('Staged cache Python magic/header mismatch: ' + relative)
    flags = struct.unpack('<I', data[4:8])[0]
    if flags not in (0, 1, 3):
        raise ValueError('Staged cache flags are invalid: ' + relative)
    if flags == 0:
        expected = struct.pack('<II', int(original.stat().st_mtime) & 0xFFFFFFFF,
                               len(original_bytes) & 0xFFFFFFFF)
        if data[8:16] != expected:
            raise ValueError('Staged cache timestamp/source length mismatch: ' + relative)
        invalidation = 'timestamp-and-source-length'
    else:
        if data[8:16] != importlib.util.source_hash(original_bytes):
            raise ValueError('Staged cache source hash mismatch: ' + relative)
        invalidation = 'checked-source-hash' if flags == 3 else 'unchecked-source-hash-verified-by-audit'
    payload = io.BytesIO(data[16:])
    try:
        cached_code = marshal.load(payload)
        expected_code = compile(original_bytes, source_relative, 'exec', dont_inherit=True, optimize=0)
        if (payload.tell() != len(data) - 16 or
                code_fingerprint(cached_code) != code_fingerprint(expected_code)):
            raise ValueError('Code/trailing data mismatch')
    except (ValueError, EOFError, TypeError) as error:
        raise ValueError('Staged cache code differs from declared source: ' + relative) from error
    return {'relative': relative, 'source_relative': source_relative, 'bytes': len(data),
            'sha256': digest(cache), 'flags': flags, 'invalidation_verified': invalidation,
            'code_matches_staged_source': True}


def verify_release(work: Path) -> dict:
    work = work.resolve(strict=True)
    plan_path = checked(work / 'plan.json', work)
    plan = json.loads(plan_path.read_text(encoding='utf-8-sig'))
    if plan.get('schema_version') != 1 or Path(plan.get('work', '')).resolve() != work:
        raise ValueError('Freeze plan identity/schema mismatch')
    version = plan.get('appVersion', '')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or any(int(part) > 65535 for part in version.split('.')):
        raise ValueError('Invalid authoritative Windows version in freeze plan')
    if plan.get('includePlayer') is not True or plan.get('rendererIncluded') is not True:
        raise ValueError('Complete native player/renderer creator release required')
    if plan.get('applicationExecuted') is not False or plan.get('signed') is not False:
        raise ValueError('Freeze plan static scope mismatch')
    spec = checked(work / 'AI_BS_GameRelease.spec', work)
    if digest(spec) != plan.get('specSha256'):
        raise ValueError('Frozen package specification changed')
    source = checked(work / 'source', work, file=False)
    output = Path(plan['output']).resolve(strict=True)
    if output.name != 'v' + version:
        raise ValueError('Package output directory/version mismatch')
    package = checked(output / 'AI_BS_Studio', output, file=False)
    internal = checked(package / '_internal', package, file=False)
    executable = checked(package / 'AI_BS_Studio.exe', package)
    modules = plan.get('modules')
    if not isinstance(modules, list) or len(set(modules)) != len(modules):
        raise ValueError('Unique declared module list required')
    module_paths = {relative: module for module in modules if (relative := module_relative(module)) is not None}
    namespaces = {module for module in modules if module_relative(module) is None}
    declared_namespaces = plan.get('namespaceModules', [])
    if not isinstance(declared_namespaces, list) or len(set(declared_namespaces)) != len(declared_namespaces) or set(declared_namespaces) != namespaces:
        raise ValueError('Declared namespace packages differ from reviewed source layout')
    for namespace in namespaces:
        directory = checked(source / namespace.replace('.', '/'), source, file=False)
        if (directory / '__init__.py').exists():
            raise ValueError('Generated UI namespace must not invent an initializer')
    asset_profile = plan.get('assetPipelineIncluded', False)
    if type(asset_profile) is not bool or plan.get('referencePartIncluded', False) is not asset_profile:
        raise ValueError('Reference asset profile flags must be truthful matching booleans')
    capabilities=read_native_capabilities(internal/'game_assets/player/aibs_capabilities.json')
    saved_required, saved_profile = validate_saved_play_profile(plan, capabilities, modules)
    placement_profile=plan.get('persistentAssetPlacementIncluded',False)
    if (type(placement_profile) is not bool or placement_profile is not (asset_profile and placement_capable(capabilities))):
        raise ValueError('Persistent placement profile differs from included SDK capability and asset tools')
    opening_profile = plan.get('warmOpeningIncluded', False)
    if type(opening_profile) is not bool:
        raise ValueError('Opening profile must be an explicit boolean')
    opening = None
    if opening_profile:
        require_opening_capabilities(capabilities)
        safe_relative(plan.get('openingAssetsRoot'))
        if type(plan.get('openingAssets')) is not dict:
            raise ValueError('Opening profile requires a frozen bundle declaration')
        opening = validate_opening_bundle(source / OPENING_PREFIX, plan['openingAssets'])
        require_opening_payload_capabilities(capabilities,opening)
    elif plan.get('openingAssets') is not None or plan.get('openingAssetsRoot') is not None:
        raise ValueError('Opening assets require their explicit profile')
    required_modules = REQUIRED_MODULES | ({ASSET_VIEW_MODULE, 'native_studio.asset_release_smoke'} if asset_profile else set()) | (PLACEMENT_MODULES if placement_profile else set()) | (OPENING_MODULES if opening_profile else set()) | (SAVED_PLAY_MODULES if saved_profile else set())
    if not required_modules.issubset(modules):
        raise ValueError('Missing required native creator modules: ' + ', '.join(sorted(required_modules - set(modules))))
    terminal_profile = validate_terminal_helper_profile(plan, modules)
    allowed_assets = set(ALLOWED_ASSETS)
    if terminal_profile:
        allowed_assets.update(TERMINAL_HELPER_FILES.values())
    if warm_asset_profile(capabilities):
        allowed_assets.update('game_assets/player/'+name for name in WARM_PLAYER_FILES)
    if opening is not None:
        allowed_assets.add(OPENING_FACTORY)
        allowed_assets.update(OPENING_PREFIX + row['relative'] for row in opening['files'])
    reference = None
    if asset_profile:
        for key in ('nativeSdk', 'assetPack'):
            safe_relative(plan.get(key))
        reference = plan.get('referencePart')
        if (type(reference) is not dict or set(reference) != {'asset_id', 'sha256', 'file'}):
            raise ValueError('Reference identity must be declared in the source plan')
        reference = validate_reference_pack(source / REFERENCE_PREFIX, reference)
        allowed_assets.add('game_assets/player/aibs_assetc.exe')
        allowed_assets.update(REFERENCE_PREFIX + name for name in
                              ('catalog.aibcat', reference['file'], 'LICENSE.txt', 'provenance.json'))
    elif plan.get('referencePart') is not None or plan.get('assetPack') is not None:
        raise ValueError('Reference assets require the explicit asset profile')
    rows = {}
    for row in plan['files']:
        relative = safe_relative(row['relative'])
        if relative in rows:
            raise ValueError('Duplicate freeze plan path: ' + relative)
        if relative not in module_paths and relative not in allowed_assets:
            raise ValueError('Undeclared/private staged input: ' + relative)
        rows[relative] = row
    if not allowed_assets.issubset(rows):
        raise ValueError('Missing required creator assets: ' + ', '.join(sorted(allowed_assets - set(rows))))
    if not set(module_paths).issubset(rows):
        raise ValueError('Missing staged module source')
    if terminal_profile:
        for source_name, helper_name in TERMINAL_HELPER_FILES.items():
            if rows[source_name]['sha256'] != rows[helper_name]['sha256']:
                raise ValueError('Terminal DATA helper differs from its frozen module source')
    observed_source = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
    if set(rows) - observed_source:
        raise ValueError('Absent staged source files: ' + ', '.join(sorted(set(rows) - observed_source)))
    generated_caches = [verify_generated_cache(source / relative, source, rows)
                        for relative in sorted(observed_source - set(rows))]
    staged_rows, assets = [], []
    for relative, row in rows.items():
        staged = checked(source / relative, source)
        staged_hash = digest(staged)
        if staged.stat().st_size != row.get('bytes') or staged_hash != row.get('sha256'):
            raise ValueError('Frozen staged input changed: ' + relative)
        reason = private_reason(relative)
        if reason or (staged.suffix.lower() in {'.py', '.json', '.html', '.js', '.txt'} and
                      SECRET_PATTERN.search(staged.read_bytes())):
            raise ValueError('Private/credential staged input: ' + relative)
        staged_rows.append({'relative': relative, 'bytes': row['bytes'], 'sha256': staged_hash})
        if relative in allowed_assets:
            packaged = checked(internal / relative, internal)
            packaged_hash = digest(packaged)
            if packaged.stat().st_size != row['bytes'] or packaged_hash != staged_hash:
                raise ValueError('Packaged asset differs from staged input: ' + relative)
            assets.append({'relative': relative, 'bytes': row['bytes'], 'sha256': packaged_hash,
                           'matches_frozen_input': True})
    local_imports_verified = verify_local_import_closure(source, module_paths, set(modules))
    metadata = json.loads((internal / 'game_release.json').read_text(encoding='utf-8'))
    validate_terminal_helper_profile(plan, modules, metadata)
    validate_saved_play_profile(plan, capabilities, modules, metadata)
    required_metadata = {'schema_version': 1, 'app_version': version, 'build_kind': 'native-pc-game-hub',
        'backend_bundled': False, 'web_parity_verified': False, 'signed': False,
        'requires_existing_services': True, 'player_included': True, 'renderer_included': True,
        'creator_included': True, 'typed_creator_included': True, 'creator_viewport_included': True,
        'local_ai_authoring_included': True, 'local_ai_model_weights_bundled': False,
        'local_ai_requires_existing_service': True, 'playground_values': 'simulated',
        'native_save_access_from_playground': False}
    for key in ('asset_pipeline_included', 'reference_part_included'):
        if asset_profile or key in metadata:
            required_metadata[key] = asset_profile
    if placement_profile or 'persistent_asset_placement_included' in metadata:
        required_metadata['persistent_asset_placement_included']=placement_profile
    if asset_profile:
        required_metadata['reference_part'] = reference
        validate_reference_pack(internal / REFERENCE_PREFIX, reference)
    elif metadata.get('reference_part') is not None:
        raise ValueError('Reference metadata requires included reference assets')
    for key in ('warm_opening_included', 'opening_workshop_included'):
        if opening_profile or key in metadata:
            required_metadata[key] = opening_profile
    if opening_profile:
        required_metadata['opening_assets_manifest_sha256'] = opening['manifest_sha256']
        validate_opening_bundle(internal / OPENING_PREFIX, opening)
    elif metadata.get('opening_assets_manifest_sha256') is not None:
        raise ValueError('Opening metadata requires its included curated assets')
    if any(metadata.get(key) != value or type(metadata.get(key)) is not type(value)
           for key, value in required_metadata.items()):
        raise ValueError('Native creator release metadata contract mismatch')
    if (internal / 'version.txt').read_text(encoding='utf-8-sig').strip().removeprefix('v') != version:
        raise ValueError('Packaged version.txt mismatch')
    inventory = []
    allowed_executables = {'AI_BS_Studio.exe'} | {'_internal/' + path for path in allowed_assets if path.endswith('.exe')}
    for path in package.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('Redirected package file/directory')
        if not path.is_file():
            continue
        checked(path, package)
        relative = path.relative_to(package).as_posix()
        reason = private_reason(relative)
        if reason:
            raise ValueError(reason + ': ' + relative)
        if path.suffix.lower() == '.exe' and relative not in allowed_executables:
            raise ValueError('Undeclared package executable: ' + relative)
        if relative.startswith(('_internal/game_assets/', '_internal/assets/')) and relative.removeprefix('_internal/') not in allowed_assets:
            raise ValueError('Undeclared package asset: ' + relative)
        if path.suffix.lower() == '.zip':
            if relative != '_internal/base_library.zip':
                raise ValueError('Undeclared/private package archive: ' + relative)
            with zipfile.ZipFile(path) as archive:
                if any(private_reason(name) for name in archive.namelist()):
                    raise ValueError('Private input in base library archive')
        if path.suffix.lower() == '.pem' and (relative != '_internal/certifi/cacert.pem' or
                b'PRIVATE KEY' in path.read_bytes() or b'BEGIN CERTIFICATE' not in path.read_bytes()):
            raise ValueError('Private/undeclared PEM input: ' + relative)
        inventory.append({'relative': relative, 'bytes': path.stat().st_size})
    for relative in ('PyQt6/QtNetwork.pyd', 'PyQt6/Qt6/bin/Qt6Network.dll'):
        if not (internal / relative).is_file():
            raise ValueError('Missing required QtNetwork dependency: ' + relative)
    collected, collection_hash = collection_paths(work)
    observed = {row['relative'] for row in inventory}
    if observed != collected:
        raise ValueError('Undeclared or missing package files versus collection inventory: extra=' +
                         ', '.join(sorted(observed - collected)) + '; missing=' + ', '.join(sorted(collected - observed)))
    pe = read_pe_metadata(executable)
    expected_version = [*map(int, version.split('.')), 0]
    if (pe['file_version'] != expected_version or pe['product_version'] != expected_version or
            any(pe['strings'].get(key) != version for key in ('FileVersion', 'ProductVersion'))):
        raise ValueError('Studio PE Windows version metadata mismatch')
    if pe['machine'] != 0x8664 or pe['subsystem'] != 2:
        raise ValueError('Expected Windows x64 GUI executable')
    frozen = read_frozen_archive(executable, modules)
    forbidden = {'backend', 'torch', 'tensorflow', 'transformers', 'sentence_transformers', 'chromadb'}
    leaked = sorted(name for name in frozen['names'] if name.split('.')[0] in forbidden)
    if leaked:
        raise ValueError('Private/backend/model modules in frozen package: ' + ', '.join(leaked))
    unexpected_native = {name for name in frozen['names'] if name.split('.')[0] in {'native_studio', 'ui_modernization'}} - set(modules)
    if unexpected_native:
        raise ValueError('Undeclared frozen native modules: ' + ', '.join(sorted(unexpected_native)))
    if namespaces != set(frozen.get('namespace_packages', set())):
        raise ValueError('Frozen namespace package types differ from reviewed layout')
    equivalence = {name: {'status': 'NamespacePackage', 'source_path': name.replace('.', '/'), 'initializer_created': False} for name in namespaces}
    for relative, module in module_paths.items():
        if module not in frozen['code']:
            raise ValueError('Missing frozen code: ' + module)
        staged_code = compile((source / relative).read_bytes(), relative, 'exec', dont_inherit=True, optimize=0)
        expected_hash = code_fingerprint(staged_code)
        frozen_hash = code_fingerprint(frozen['code'][module])
        if expected_hash != frozen_hash:
            raise ValueError('Frozen code differs from staged source: ' + module)
        equivalence[module] = {'status': 'StagedSourceEquivalent', 'code_sha256': frozen_hash,
                               'staged_source_sha256': rows[relative]['sha256']}
    if code_fingerprint(frozen['entry_code']) != equivalence['native_studio.app']['code_sha256']:
        raise ValueError('Frozen app entry script differs from staged source')
    return {'schema_version': 1, 'status': 'passed', 'completed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Static PE, staged source, PYZ code equivalence, declared assets and package path/privacy checks only',
        'limitations': ['No application or native executable execution', 'No runtime, AI inference, signing or web parity validation',
                        'Privacy checks cover allowlisted staged inputs, known credential signatures and package/archive/module paths; not semantic inspection of all dependency binaries'],
        'application_executed': False, 'web_parity_verified': False, 'signed': False,
        'app_version': version, 'work': str(work), 'package': str(package),
        'plan_sha256': digest(plan_path), 'spec_sha256': digest(spec),
        'collection_manifest_sha256': collection_hash, 'inventory_matches_collection_manifest': True,
        'executable_sha256': digest(executable), 'pe_metadata': pe,
        'staged_inputs_verified': staged_rows, 'asset_readback': assets,
        'staged_local_import_dependencies_verified': local_imports_verified, 'namespace_modules_verified': sorted(namespaces),
        'generated_staged_caches_verified': generated_caches,
        'frozen_module_equivalence': equivalence, 'frozen_module_code_matches_staged_source': True,
        'entry_script_matches_staged_source': True, 'qt_network_included': True,
        'asset_pipeline_included': asset_profile, 'reference_part_included': asset_profile,
        'persistent_asset_placement_included':placement_profile,
        'reference_part': reference,
        'warm_opening_included': opening_profile, 'opening_assets': opening,
        'require_saved_play': saved_required, 'saved_chapter_play_included': saved_profile,
        'capabilities':capabilities,
        'native_terminal_helpers_included': terminal_profile,
        'package_files': len(inventory), 'package_bytes': sum(row['bytes'] for row in inventory),
        'package_inventory': sorted(inventory, key=lambda row: row['relative']), 'private_artifacts': []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path, help='Directory containing plan.json and immutable source/')
    parser.add_argument('--report', required=True, type=Path, help='Fresh JSON report path; existing evidence is preserved')
    args = parser.parse_args(argv)
    if args.report.exists():
        parser.error('Preserve existing evidence; choose a fresh report path')
    try:
        report = verify_release(args.work)
    except Exception as error:
        report = {'schema_version': 1, 'status': 'failed', 'completed_at': datetime.now(timezone.utc).isoformat(),
                  'scope': 'Static release verification only', 'application_executed': False,
                  'error_type': type(error).__name__, 'error': str(error), 'work': str(args.work)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'report': str(args.report), 'application_executed': False,
                      **({'error': report['error']} if report['status'] == 'failed' else {})}))
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
