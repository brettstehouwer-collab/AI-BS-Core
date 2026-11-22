"""Freeze/build a fresh native AI-BS client with explicitly declared game assets.

No application/service launch, web-parity claim, signing or shortcut mutation.
The historical verified-web builder and its baseline guard remain untouched.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('native_game_module_graph', ROOT / 'scripts/build_native_web_parity.py')
_graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_graph)
_asset_spec = importlib.util.spec_from_file_location('native_asset_pack_contract',
    Path(__file__).resolve().with_name('verify_native_creator_release.py'))
_asset_contract = importlib.util.module_from_spec(_asset_spec)
_asset_spec.loader.exec_module(_asset_contract)

# Keep the Creator's package-relative dependencies explicit even when the
# application entry graph changes. Resolve/check source ASTs without importing
# application code or changing the historical web builder's admission policy.
CREATOR_MODULES = {
    'native_studio.game_engine',
    *(f'native_studio.game_engine.{name}' for name in (
        'project_model', 'creator_wire', 'creator_client', 'creator_payload',
        'creator_commands', 'creator_view', 'creator_viewport', 'content_commands',
        'content_client', 'content_jobs', 'content_proposals', 'content_preview',
        'content_play', 'content_view', 'content_ai', 'asset_view', 'project_assets',
        'opening_fields', 'workshop_fields', 'opening_assets', 'opening_project',
        'saved_play', 'saved_play_storage', 'saved_chapter_export')),
}
FROZEN_DYNAMIC_IMPORTS = ['win32timezone', 'PyQt6.QtNetwork']
NATIVE_PLAYER_ASSETS = [
    ('engine/install/release/bin/' + name, 'game_assets/player/' + name)
    for name in ('aibs_player.exe', 'aibs_motherboard.exe', 'aibs_creator_host.exe',
                 'aibs_content_host.exe', 'aibs_creator_viewport.exe',
                 'aibs_capabilities.json', 'shaders/motherboard.vs.cso',
                 'shaders/motherboard.ps.cso')
] + [
    ('engine/install/release/share/AIBS/licenses/' + name, 'game_assets/player/' + name)
    for name in ('Jolt-LICENSE.txt', 'SQLite-NOTICE.txt')
]


def native_modules() -> list[str]:
    """Declare all creator clients and the early frozen smoke entry point."""
    return sorted(set(_graph.native_modules()) | CREATOR_MODULES |
                  {'native_studio.game_release_smoke', 'native_studio.asset_release_smoke','native_studio.placement_release_smoke',
                   'native_studio.saved_play_release_smoke'})


def module_source(module: str) -> str | None:
    """Resolve exact source or an explicitly reviewed namespace package."""
    return _graph.module_source(module, ROOT)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(path: Path, boundary: Path, *, exists: bool = True) -> Path:
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Redirected release/staging inputs are not admitted')
    resolved = path.resolve(strict=exists)
    resolved.relative_to(boundary.resolve(strict=True))
    return resolved


def hosting_summary(path: Path | None) -> dict:
    if path is None:
        return {'status': 'not_supplied', 'origin': 'https://ai-bs-dashboard.web.app'}
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Hosting evidence exceeds 1 MiB')
    evidence = json.loads(path.read_text(encoding='utf-8'))
    if evidence.get('status') != 'passed' or evidence.get('origin') != 'https://ai-bs-dashboard.web.app':
        raise ValueError('Expected successful public hosting verification')
    # Deliberate allowlist: raw verification input may contain local diagnostics.
    return {'status': 'passed', 'origin': evidence['origin'],
            'verified_at': str(evidence.get('verified_at', evidence.get('completed_at', '')))}


def stage(work: Path, output: Path, *, include_player: bool = False,
          hosting_verification: Path | None = None, native_sdk: Path | None = None,
          asset_pack: Path | None = None, opening_assets_root: Path | None = None,
          require_saved_play: bool = False) -> dict:
    """Freeze a client-only package, or the complete native creator/player set.

    ``include_player`` admits one complete installed release asset set; it never
    infers creator availability from a lone player/renderer. Client-only staging
    remains useful for intentionally headless packaging and admission tests.
    Component flags describe included files, not runtime verification results.
    """
    if type(require_saved_play) is not bool:
        raise ValueError('require_saved_play must be an explicit boolean')
    if require_saved_play and include_player is not True:
        raise ValueError('Required saved chapter play needs include_player=True')
    work = plain(work, ROOT / 'backups', exists=False)
    output = plain(output, ROOT / 'native_studio/releases', exists=False)
    version = (ROOT / 'version.txt').read_text(encoding='utf-8').strip().removeprefix('v')
    pieces = version.split('.')
    if len(pieces) != 3 or any(not part.isdecimal() or int(part) > 65535 for part in pieces):
        raise ValueError('Windows-compatible authoritative source version required')
    if output.name != 'v' + version or output.parent != (ROOT / 'native_studio/releases').resolve():
        raise ValueError('Output must be the fresh authoritative version release directory')
    if work.exists() or output.exists():
        raise ValueError('Preserve existing release/staging; choose fresh paths')
    if asset_pack is not None and not include_player:
        raise ValueError('A reference asset pack requires include_player')
    sdk = plain(native_sdk if native_sdk is not None else ROOT / 'engine/install/release', ROOT) if include_player else None
    if native_sdk is not None and sdk is None:
        # Validate explicitly supplied paths even for an intentionally client-only plan.
        plain(native_sdk, ROOT)
    pack = plain(asset_pack, ROOT) if asset_pack is not None else None
    reference = _asset_contract.validate_reference_pack(pack) if pack is not None else None
    capabilities=_asset_contract.read_native_capabilities(sdk/'bin/aibs_capabilities.json') if include_player else {}
    if require_saved_play:
        _asset_contract.require_saved_play_capabilities(capabilities)
    modern_assets=include_player and _asset_contract.warm_asset_profile(capabilities)
    opening_root = plain(opening_assets_root, ROOT) if opening_assets_root is not None else None
    opening = None
    if opening_root is not None:
        if not include_player:
            raise ValueError('A curated opening requires the complete native player set')
        _asset_contract.require_opening_capabilities(capabilities)
        opening = _asset_contract.validate_opening_bundle(opening_root)
        _asset_contract.require_opening_payload_capabilities(capabilities,opening)
    modules = native_modules()
    saved_included = include_player is True and _asset_contract.saved_play_capable(capabilities)
    _asset_contract.validate_saved_play_profile({'includePlayer': include_player,
        'requireSavedPlay': require_saved_play, 'savedChapterPlayIncluded': saved_included}, capabilities, modules)
    if opening is not None and not _asset_contract.OPENING_MODULES.issubset(modules):
        raise ValueError('Missing required curated opening modules')
    required = {'native_studio.game_build_view', 'native_studio.game_build_monitor'}
    if not required.issubset(modules):
        raise ValueError('The game hub and monitor must be reachable in the native import graph')
    sources = []
    module_paths = {}
    for module in modules:
        relative = module_source(module)
        if relative is not None:
            sources.append((plain(ROOT / relative, ROOT / module.split('.')[0]), relative))
            module_paths[relative] = module
    # An undeclared local import must fail before any staging write, including
    # package-relative imports and reviewed generated UI namespaces. Reuse the
    # frozen-release verifier's closed policy; do not infer new allowed roots.
    _asset_contract.verify_local_import_closure(ROOT, module_paths, set(modules))
    terminal_helpers = _asset_contract.validate_terminal_helper_profile(
        {'nativeTerminalHelpersIncluded': 'native_studio.ai_bs_ide_terminal' in modules}, set(modules))
    assets = [
        ('version.txt', 'version.txt'),
        ('frontend/public/psychedelic_theme.jpg', 'assets/psychedelic_theme.jpg'),
        ('frontend/public/favicon.ico', 'assets/favicon.ico'),
        ('frontend/public/bs-game/index.html', 'game_assets/playground/index.html'),
        ('frontend/public/bs-game/vendor/three-r128.min.js', 'game_assets/playground/vendor/three-r128.min.js'),
        ('frontend/public/bs-game/vendor/THREE-LICENSE.txt', 'game_assets/playground/vendor/THREE-LICENSE.txt'),
    ]
    if terminal_helpers:
        assets.extend(_asset_contract.TERMINAL_HELPER_FILES.items())
    if include_player:
        # The hosts, viewport, renderer shaders, capability declaration and
        # notices are a single deployable set. Admission precedes every write.
        assets.extend(((sdk / Path(original).relative_to('engine/install/release')).relative_to(ROOT).as_posix(), relative)
                      for original, relative in NATIVE_PLAYER_ASSETS)
    if modern_assets:
        assets.extend(((sdk/'bin'/name).relative_to(ROOT).as_posix(),'game_assets/player/'+name)
                      for name in _asset_contract.WARM_PLAYER_FILES if name!='cgltf-LICENSE.txt')
        assets.append(((sdk/'share/licenses/AIBS/cgltf/LICENSE.txt').relative_to(ROOT).as_posix(),
                       'game_assets/player/cgltf-LICENSE.txt'))
    if reference is not None:
        if not modern_assets:
            assets.append(((sdk / 'bin/aibs_assetc.exe').relative_to(ROOT).as_posix(), 'game_assets/player/aibs_assetc.exe'))
        assets.extend(((pack / name).relative_to(ROOT).as_posix(), 'game_assets/reference_part/' + name)
                      for name in ('catalog.aibcat', reference['file'], 'LICENSE.txt', 'provenance.json'))
    if opening is not None:
        assets.append(((sdk/'bin/aibs_warm_opening_project.exe').relative_to(ROOT).as_posix(), _asset_contract.OPENING_FACTORY))
        assets.extend(((opening_root/row['relative']).relative_to(ROOT).as_posix(), _asset_contract.OPENING_PREFIX+row['relative']) for row in opening['files'])
    sources.extend((plain(ROOT / original, ROOT), relative) for original, relative in assets)
    hosting = hosting_summary(hosting_verification)
    # Read every input before creating any staging directory.
    for original, _ in sources:
        if not original.is_file():
            raise ValueError('Only declared regular source files can enter this package')
    placement_included=reference is not None and _asset_contract.placement_capable(capabilities)
    if shutil.disk_usage(ROOT).free < 2 * 1024**3:
        raise ValueError('At least 2 GiB free space is required for a fresh native build')
    work.mkdir(parents=True)
    source = work / 'source'
    source.mkdir()
    rows = []
    for original, relative in sources:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(original)
        shutil.copyfile(original, target)
        if digest(target) != before or digest(original) != before:
            raise ValueError('Source changed while freezing the release')
        rows.append({'relative': relative, 'bytes': target.stat().st_size, 'sha256': before})
    if terminal_helpers:
        frozen_rows = {row['relative']: row for row in rows}
        for module_path, helper_path in _asset_contract.TERMINAL_HELPER_FILES.items():
            if frozen_rows[module_path]['sha256'] != frozen_rows[helper_path]['sha256']:
                raise ValueError('Terminal source changed between module and DATA snapshots')
    frozen_capabilities = (_asset_contract.read_native_capabilities(source/'game_assets/player/aibs_capabilities.json')
        if include_player else {})
    if frozen_capabilities != capabilities:
        raise ValueError('Native SDK capabilities changed while freezing the release')
    metadata = {'schema_version': 1, 'app_version': version, 'build_kind': 'native-pc-game-hub',
                'web_parity_verified': False, 'signed': False, 'requires_existing_services': True,
                'backend_bundled': False, 'hosting': hosting, 'player_included': include_player,
                'renderer_included': include_player, 'creator_included': include_player,
                'typed_creator_included': include_player, 'creator_viewport_included': include_player,
                'local_ai_authoring_included': include_player,
                'local_ai_requires_existing_service': True, 'local_ai_model_weights_bundled': False,
                'asset_pipeline_included': reference is not None, 'reference_part_included': reference is not None,
                'persistent_asset_placement_included':placement_included,
                'require_saved_play':require_saved_play, 'saved_chapter_play_included':saved_included,
                'playground_values': 'simulated', 'native_save_access_from_playground': False,
                'native_terminal_helpers_included': terminal_helpers}
    if reference is not None:
        metadata['reference_part'] = reference
    if opening is not None:
        metadata.update(warm_opening_included=True, opening_workshop_included=True, opening_assets_manifest_sha256=opening['manifest_sha256'])
    (source / 'game_release.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    rows.append({'relative': 'game_release.json', 'bytes': (source / 'game_release.json').stat().st_size,
                 'sha256': digest(source / 'game_release.json')})
    data_entries = [(relative, str(Path(relative).parent).replace('\\', '/')) for _, relative in assets]
    data_entries.append(('game_release.json', '.'))
    datas_literal = ','.join(f'(str(source/{relative!r}),{target!r})' for relative, target in data_entries)
    game_executables = [relative for _, relative in assets if relative.endswith('.exe')]
    pe_version = tuple(map(int, pieces)) + (0,)
    spec = f'''from pathlib import Path
from PyInstaller.utils.win32.versioninfo import VSVersionInfo,FixedFileInfo,StringFileInfo,StringTable,StringStruct,VarFileInfo,VarStruct
source=Path({str(source)!r})
info=VSVersionInfo(ffi=FixedFileInfo(filevers={pe_version!r},prodvers={pe_version!r},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904b0',[StringStruct('CompanyName','Stehouwer Publishing'),StringStruct('FileDescription','AI-BS Sovereign Studio'),StringStruct('FileVersion',{version!r}),StringStruct('ProductVersion',{version!r}),StringStruct('ProductName','AI-BS Sovereign Studio'),StringStruct('OriginalFilename','AI_BS_Studio.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])
a=Analysis([str(source/'native_studio/app.py')],pathex=[str(source)],binaries=[],datas=[{datas_literal}],hiddenimports={modules + FROZEN_DYNAMIC_IMPORTS!r},hookspath=[],hooksconfig={{}},runtime_hooks=[],excludes=['backend','PyQt5','PySide2','PySide6','tkinter','IPython','notebook','torch','tensorflow','transformers','sentence_transformers','chromadb'],noarchive=False)
for name,file,kind in a.pure:
 if name=='backend' or name.startswith('backend.'): raise ValueError('Backend code is not native client data')
 if file and not(file=='-' and kind=='PYMODULE') and Path(file).resolve().is_relative_to(Path({str(ROOT)!r})) and not Path(file).resolve().is_relative_to(source): raise ValueError('Repository code escaped the frozen native source graph')
for name,file,kind in list(a.datas)+list(a.binaries):
 if kind in {{'BINARY','EXTENSION','DATA'}} and not any(Path(file).resolve().is_relative_to(base) for base in [source,Path({str(work / 'pyinstaller')!r}),Path({str(Path(sys.executable).parent.resolve())!r}),Path({str(Path(os.environ.get('SystemRoot','C:/Windows')).resolve())!r})]): raise ValueError('Undeclared native dependency root')
 suffix=Path(name).suffix.lower()
 std_zip=name=='base_library.zip' and Path(file).resolve().is_relative_to(Path({str(work / 'pyinstaller')!r}))
 public_ca=name.replace('\\\\','/').endswith('certifi/cacert.pem') and not Path(file).resolve().is_relative_to(Path({str(ROOT)!r})) and b'PRIVATE KEY' not in Path(file).read_bytes() and b'BEGIN CERTIFICATE' in Path(file).read_bytes()
 normalized_name=name.replace('\\\\','/')
 declared_player=normalized_name in {game_executables!r} and Path(file).resolve()==source/normalized_name
 if suffix in {{'.db','.sqlite','.sqlite3','.pfx','.p12','.key','.iso','.aibs'}} or suffix=='.zip' and not std_zip or suffix=='.pem' and not public_ca or suffix=='.exe' and not declared_player or Path(name).name in {{'.env','AGENTS.md','CODEX_HANDOFF.md'}}: raise ValueError('Private/archive/undeclared executable material is not client data')
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='AI_BS_Studio',version=info,icon=str(source/'assets/favicon.ico'),debug=False,strip=False,upx=False,console=False,uac_admin=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='AI_BS_Studio')
'''
    ast.parse(spec)
    (work / 'AI_BS_GameRelease.spec').write_text(spec, encoding='utf-8')
    plan = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
            'work': str(work), 'output': str(output), 'appVersion': version, 'modules': modules,
            'namespaceModules': [name for name in modules if module_source(name) is None],
            'files': rows, 'webParityVerified': False, 'requiresExistingServices': True,
            'nativeTerminalHelpersIncluded': terminal_helpers,
            'applicationExecuted': False, 'signed': False, 'includePlayer': include_player,
            'rendererIncluded': include_player, 'creatorIncluded': include_player,
            'typedCreatorIncluded': include_player, 'creatorViewportIncluded': include_player,
            'localAiAuthoringIncluded': include_player, 'localAiRequiresExistingService': True,
            'localAiModelWeightsBundled': False,
            'assetPipelineIncluded': reference is not None, 'referencePartIncluded': reference is not None,
            'persistentAssetPlacementIncluded':placement_included,
            'requireSavedPlay':require_saved_play, 'savedChapterPlayIncluded':saved_included,
            'nativeSdk': sdk.relative_to(ROOT).as_posix() if sdk is not None else None,
            'assetPack': pack.relative_to(ROOT).as_posix() if pack is not None else None,
            'referencePart': reference,
            'builderSha256': digest(Path(__file__)), 'specSha256': digest(work / 'AI_BS_GameRelease.spec')}
    if opening is not None:
        plan.update(warmOpeningIncluded=True, openingAssetsRoot=opening_root.relative_to(ROOT).as_posix(), openingAssets=opening)
    (work / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    return plan


def validate_build(work: Path) -> dict:
    work = plain(work, ROOT / 'backups')
    plan = json.loads((work / 'plan.json').read_text(encoding='utf-8'))
    if plan['work'] != str(work) or plan['builderSha256'] != digest(Path(__file__)):
        raise ValueError('Builder/staging identity changed')
    output = plain(Path(plan['output']), ROOT / 'native_studio/releases', exists=False)
    if output.exists() or (work / 'pyinstaller').exists() or (work / 'build_result.json').exists():
        raise ValueError('Preserve existing build/release attempts')
    if digest(work / 'AI_BS_GameRelease.spec') != plan['specSha256']:
        raise ValueError('Frozen package specification changed')
    for row in plan['files']:
        if digest(plain(work / 'source' / row['relative'], work / 'source')) != row['sha256']:
            raise ValueError('Frozen native source changed')
    capabilities = (_asset_contract.read_native_capabilities(work/'source/game_assets/player/aibs_capabilities.json')
        if plan.get('includePlayer') is True else {})
    metadata = json.loads((work/'source/game_release.json').read_text(encoding='utf-8'))
    _asset_contract.validate_saved_play_profile(plan, capabilities, set(plan['modules']), metadata)
    _asset_contract.validate_terminal_helper_profile(plan, set(plan['modules']), metadata)
    return plan


def build(work: Path) -> int:
    plan = validate_build(work)
    work = Path(plan['work'])
    output = Path(plan['output'])
    environment = {key: value for key, value in os.environ.items()
                   if key not in {'PYTHONPATH', 'PYTHONHOME'} and not key.upper().endswith(('TOKEN','PASSWORD','SECRET','API_KEY','ADMIN_KEY'))}
    python_root = Path(sys.executable).resolve().parent
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows')).resolve(strict=True)
    environment['PATH'] = os.pathsep.join(map(str, [python_root, python_root/'Scripts', windows/'System32', windows]))
    for key in ('QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QML2_IMPORT_PATH'):
        environment.pop(key, None)
    arguments = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(output),
                 '--workpath', str(work/'pyinstaller'), '--log-level', 'INFO', str(work/'AI_BS_GameRelease.spec')]
    started = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    with (work/'build_stdout.local.txt').open('xb') as stdout, (work/'build_stderr.local.txt').open('xb') as stderr:
        try:
            process = subprocess.run(arguments, cwd=work, env=environment, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
            code = process.returncode
        except subprocess.TimeoutExpired:
            code = 124
    receipt = {'schema_version': 1, 'started_at': started, 'completed_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': code, 'applicationExecuted': False, 'signed': False,
               'output': str(output), 'appVersion': plan['appVersion']}
    (work/'build_result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['stage','build'])
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--include-player', action='store_true',
                        help='Require and bundle the complete installed native player/creator/viewport asset set')
    parser.add_argument('--require-saved-play', action='store_true',
                        help='Require complete SDK0.16 saved-chapter player capabilities and all three managed saved-play clients')
    parser.add_argument('--hosting-verification', type=Path)
    parser.add_argument('--native-sdk', type=Path, help='Explicit installed SDK prefix inside the project')
    parser.add_argument('--asset-pack', type=Path, help='Exact four-file cooked public reference pack; requires --include-player')
    parser.add_argument('--opening-assets-root', type=Path, help='Curated six-pack First Boot bundle inside the project; requires complete SDK0.15 tools')
    args = parser.parse_args()
    if args.mode == 'build':
        return build(args.work)
    if args.output is None:
        parser.error('stage requires --output')
    plan = stage(args.work, args.output, include_player=args.include_player, hosting_verification=args.hosting_verification,
                 native_sdk=args.native_sdk, asset_pack=args.asset_pack, opening_assets_root=args.opening_assets_root,
                 require_saved_play=args.require_saved_play)
    print(json.dumps({'status':'staged','work':plan['work'],'output':plan['output'],
                      'appVersion':plan['appVersion'],'files':len(plan['files']),
                      'applicationExecuted':False,'webParityVerified':False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
