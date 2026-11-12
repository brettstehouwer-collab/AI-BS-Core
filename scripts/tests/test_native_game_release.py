"""Scoped native game package admission tests; no application execution."""
import importlib.util
import ast
import json
import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('native_game_builder', ROOT / 'scripts/build_native_game_release.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class NativeGameReleaseTests(unittest.TestCase):
    def test_terminal_module_freezes_only_reviewed_helper_data_with_identical_bytes(self):
        modules = ['native_studio', 'native_studio.app', 'native_studio.game_build_view',
                   'native_studio.game_build_monitor', 'native_studio.ai_bs_ide_terminal',
                   'native_studio.owned_process']
        (self.root/'native_studio/ai_bs_ide_terminal.py').write_text('def helper():\n    return 1\n')
        (self.root/'native_studio/owned_process.py').write_text('class OwnedProcess:\n    pass\n')
        with patch.object(builder, 'native_modules', return_value=modules):
            plan = self.stage()
        rows = {row['relative']: row for row in plan['files']}
        self.assertTrue(plan['nativeTerminalHelpersIncluded'])
        for source, data in builder._asset_contract.TERMINAL_HELPER_FILES.items():
            self.assertEqual(rows[source]['sha256'], rows[data]['sha256'])
            self.assertEqual((self.work/'source'/source).read_bytes(),
                             (self.work/'source'/data).read_bytes())
        metadata = json.loads((self.work/'source/game_release.json').read_text())
        self.assertTrue(metadata['native_terminal_helpers_included'])
        spec = (self.work/'AI_BS_GameRelease.spec').read_text()
        self.assertIn('native_helpers/ai_bs_ide_terminal.py', spec)
        self.assertIn('native_helpers/owned_process.py', spec)
        self.assertIn("excludes=['backend'", spec)

    def test_terminal_profile_missing_owned_mechanics_rejects_before_staging(self):
        modules = ['native_studio', 'native_studio.app', 'native_studio.game_build_view',
                   'native_studio.game_build_monitor', 'native_studio.ai_bs_ide_terminal']
        (self.root/'native_studio/ai_bs_ide_terminal.py').write_text('def helper():\n    return 1\n')
        with patch.object(builder, 'native_modules', return_value=modules):
            with self.assertRaisesRegex(ValueError, 'reviewed native owned-process'):
                self.stage()
        self.assertFalse(self.work.exists())

    def test_terminal_profile_preserves_older_release_contract_and_rejects_false_flags(self):
        validate = builder._asset_contract.validate_terminal_helper_profile
        self.assertFalse(validate({}, {'native_studio.app'}))
        self.assertFalse(validate({'nativeTerminalHelpersIncluded': False}, {'native_studio.app'}, {}))
        modules = {'native_studio.ai_bs_ide_terminal', 'native_studio.owned_process'}
        with self.assertRaisesRegex(ValueError, 'inclusion'):
            validate({}, modules)
        with self.assertRaisesRegex(ValueError, 'metadata'):
            validate({'nativeTerminalHelpersIncluded': True}, modules,
                     {'native_terminal_helpers_included': False})
        self.assertTrue(validate({'nativeTerminalHelpersIncluded': True}, modules,
                                 {'native_terminal_helpers_included': True}))

    def modern_sdk(self, *, complete=False):
        self.add_creator_fixture()
        sdk=self.root/'engine/install/release'
        (sdk/'bin/aibs_capabilities.json').write_text(json.dumps({'schema_version':1,'sdk_version':'0.11.0','features':{'chapter_content_v3':True}}))
        if complete:
            for name in ('textured.vs.cso','textured.ps.cso','shadow.vs.cso','character.vs.cso','character.ps.cso'):
                (sdk/'bin/shaders'/name).write_bytes(b'current shader fixture')
            (sdk/'bin/aibs_assetc.exe').write_bytes(b'MZ current cooker fixture')
            license_file=sdk/'share/licenses/AIBS/cgltf/LICENSE.txt'
            license_file.parent.mkdir(parents=True)
            license_file.write_text('MIT cgltf fixture')
        return sdk

    def test_modern_sdk_requires_complete_shaders_cooker_and_notice_before_staging(self):
        self.modern_sdk()
        with self.assertRaises(FileNotFoundError):self.stage(include_player=True)
        self.assertFalse(self.work.exists())

    def test_modern_sdk_stages_exact_extended_render_dependencies(self):
        self.modern_sdk(complete=True)
        plan=self.stage(include_player=True)
        paths={row['relative'] for row in plan['files']}
        for name in ('shaders/textured.vs.cso','shaders/textured.ps.cso','shaders/shadow.vs.cso','shaders/character.vs.cso','shaders/character.ps.cso','aibs_assetc.exe','cgltf-LICENSE.txt'):
            self.assertIn('game_assets/player/'+name,paths)
        self.assertEqual(len(paths),len(plan['files']))

    def test_placement_modules_are_explicit_without_importing_the_application(self):
        patch.stopall()
        with patch.object(builder._graph,'native_modules',return_value=['native_studio','native_studio.app']):
            modules=builder.native_modules()
        self.assertIn('native_studio.game_engine.project_assets',modules)
        self.assertIn('native_studio.placement_release_smoke',modules)

    def test_opening_workshop_modules_are_explicit_without_application_imports(self):
        patch.stopall()
        required={'native_studio.game_engine.opening_fields','native_studio.game_engine.workshop_fields'}
        with patch.object(builder._graph,'native_modules',return_value=['native_studio','native_studio.app']),patch.dict(sys.modules,{name:None for name in required|{'native_studio.app'}}):
            modules=builder.native_modules()
        self.assertTrue(required<=builder.CREATOR_MODULES)
        self.assertTrue(required<=set(modules))

    def test_actual_creator_source_graph_has_complete_relative_import_closure(self):
        patch.stopall()
        modules=set(builder.native_modules())
        paths={relative:module for module in modules if (relative:=builder.module_source(module))is not None}
        self.assertIn('native_studio/game_engine/opening_fields.py',paths)
        self.assertIn('native_studio/game_engine/workshop_fields.py',paths)
        self.assertGreater(builder._asset_contract.verify_local_import_closure(ROOT,paths,modules),0)
        self.assertNotIn('backend',modules)
        self.assertNotIn('tools',modules)

    def workshop_source_fixture(self):
        modules=['native_studio','native_studio.app','native_studio.game_build_view','native_studio.game_build_monitor',
            'native_studio.game_engine','native_studio.game_engine.creator_payload',
            'native_studio.game_engine.opening_fields','native_studio.game_engine.workshop_fields']
        package=self.root/'native_studio/game_engine';package.mkdir()
        (package/'__init__.py').write_text('# synthetic package\n')
        (package/'creator_payload.py').write_text('def _uuid(value):\n    return value\n')
        (package/'workshop_fields.py').write_text("from .creator_payload import _uuid\nWORKSHOP_CAPABILITY='chapter-workshop-commissioning-v1'\n")
        (package/'opening_fields.py').write_text('from .workshop_fields import WORKSHOP_CAPABILITY\n')
        (self.root/'native_studio/app.py').write_text('from native_studio.game_engine.opening_fields import WORKSHOP_CAPABILITY\n')
        return modules

    def test_missing_workshop_relative_dependency_rejects_before_staging(self):
        modules=self.workshop_source_fixture()
        modules.remove('native_studio.game_engine.workshop_fields')
        with patch.object(builder,'native_modules',return_value=modules),self.assertRaisesRegex(ValueError,'Missing declared local import: native_studio.game_engine.workshop_fields'):
            self.stage()
        self.assertFalse(self.work.exists());self.assertFalse(self.release.exists())

    def test_frozen_plan_retains_workshop_source_hiddenimports_and_isolated_import(self):
        modules=self.workshop_source_fixture()
        with patch.object(builder,'native_modules',return_value=modules):plan=self.stage()
        paths={row['relative']for row in plan['files']}
        for name in ('opening_fields','workshop_fields'):
            relative='native_studio/game_engine/'+name+'.py'
            self.assertIn(relative,paths)
            self.assertEqual((self.work/'source'/relative).read_bytes(),(self.root/relative).read_bytes())
        tree=ast.parse((self.work/'AI_BS_GameRelease.spec').read_text())
        analysis=next(node for node in ast.walk(tree)if isinstance(node,ast.Call)and isinstance(node.func,ast.Name)and node.func.id=='Analysis')
        hidden=ast.literal_eval(next(node.value for node in analysis.keywords if node.arg=='hiddenimports'))
        self.assertIn('native_studio.game_engine.opening_fields',hidden)
        self.assertIn('native_studio.game_engine.workshop_fields',hidden)
        script="""import importlib.abc,importlib.machinery,json,sys
from pathlib import Path
stage=Path(sys.argv[1]).resolve();sys.path.insert(0,str(stage));sys.dont_write_bytecode=True
class OnlyStaged(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0]=='native_studio':
   spec=importlib.machinery.PathFinder.find_spec(fullname,path)
   if spec is None or not Path(spec.origin).resolve().is_relative_to(stage):raise ImportError('Unstaged dependency '+fullname)
   return spec
sys.meta_path.insert(0,OnlyStaged())
from native_studio.game_engine.opening_fields import WORKSHOP_CAPABILITY
assert WORKSHOP_CAPABILITY=='chapter-workshop-commissioning-v1'
assert not any(name.startswith('PyQt')for name in sys.modules)
print(json.dumps({'status':'passed','application_constructed':False}))
"""
        process=subprocess.run([sys.executable,'-I','-B','-c',script,str(self.work/'source')],cwd=self.work,
            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32'else 0)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(json.loads(process.stdout),{'status':'passed','application_constructed':False})

    def test_placement_profile_requires_capable_sdk_and_included_asset_tools(self):
        sdk,pack,_=self.add_asset_profile()
        declaration=sdk/'bin/aibs_capabilities.json'
        declaration.write_text(json.dumps({'schema_version':1,'sdk_version':'0.10.0','features':{'chapter_asset_placement_v1':True}}))
        plan=self.stage(include_player=True,native_sdk=sdk,asset_pack=pack)
        self.assertTrue(plan['persistentAssetPlacementIncluded'])
        metadata=json.loads((self.work/'source/game_release.json').read_text())
        self.assertTrue(metadata['persistent_asset_placement_included'])
        self.assertNotIn('placement_verified',metadata)

    def test_legacy_sdk_profile_does_not_claim_persistent_placement(self):
        sdk,pack,_=self.add_asset_profile()
        plan=self.stage(include_player=True,native_sdk=sdk,asset_pack=pack)
        self.assertFalse(plan['persistentAssetPlacementIncluded'])
        metadata=json.loads((self.work/'source/game_release.json').read_text())
        self.assertFalse(metadata['persistent_asset_placement_included'])

    def test_capable_sdk_without_asset_profile_does_not_claim_placement_tools(self):
        sdk,_,_=self.add_asset_profile()
        (sdk/'bin/aibs_capabilities.json').write_text(json.dumps({'schema_version':1,'sdk_version':'0.10.0','features':{'chapter_asset_placement_v1':True}}))
        plan=self.stage(include_player=True,native_sdk=sdk)
        self.assertFalse(plan['persistentAssetPlacementIncluded'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Production ROOT is canonical (__file__.resolve()); match it even
        # when Windows supplies TEMP through an 8.3 administrator alias.
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / 'backups/game87'
        self.release = self.root / 'native_studio/releases/v5.329.87'
        self.work.parent.mkdir(parents=True)
        self.release.parent.mkdir(parents=True)
        fixtures = {
            'version.txt': 'v5.329.87',
            'native_studio/__init__.py': '__version__="5.329.87"\n',
            'native_studio/app.py': 'print("fixture only")\n',
            'native_studio/game_build_view.py': '# fixture\n',
            'native_studio/game_build_monitor.py': '# fixture\n',
            'frontend/public/psychedelic_theme.jpg': 'theme',
            'frontend/public/favicon.ico': 'icon',
            'frontend/public/bs-game/index.html': '<script src="./vendor/three-r128.min.js"></script>',
            'frontend/public/bs-game/vendor/three-r128.min.js': '// pinned renderer fixture',
            'frontend/public/bs-game/vendor/THREE-LICENSE.txt': 'MIT fixture',
            'engine/install/release/bin/aibs_player.exe': 'MZ fixture only',
        }
        for name, content in fixtures.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        self.addCleanup(patch.stopall)
        patch.object(builder, 'ROOT', self.root).start()
        patch.object(builder, 'native_modules', return_value=['native_studio', 'native_studio.app', 'native_studio.game_build_view', 'native_studio.game_build_monitor']).start()

    def stage(self, **kwargs):
        return builder.stage(self.work, self.release, **kwargs)

    def test_collects_only_declared_game_assets_and_complete_native_tools(self):
        self.add_creator_fixture()
        plan = self.stage(include_player=True)
        paths = {item['relative'] for item in plan['files']}
        self.assertIn('game_assets/playground/index.html', paths)
        self.assertIn('game_assets/playground/vendor/three-r128.min.js', paths)
        self.assertIn('game_assets/player/aibs_player.exe', paths)
        self.assertIn('native_studio/game_build_view.py', paths)
        self.assertFalse(self.release.exists())
        self.assertFalse(plan['applicationExecuted'])
        self.assertFalse(plan['webParityVerified'])
        self.assertTrue(plan['requiresExistingServices'])
        metadata = json.loads((self.work / 'source/game_release.json').read_text())
        self.assertTrue(metadata['renderer_included'])
        self.assertTrue(metadata['creator_included'])
        self.assertTrue(metadata['typed_creator_included'])
        self.assertTrue(metadata['creator_viewport_included'])
        self.assertTrue(metadata['local_ai_authoring_included'])
        self.assertTrue(metadata['local_ai_requires_existing_service'])
        self.assertFalse(metadata['local_ai_model_weights_bundled'])

    def add_renderer_fixture(self, *, both_shaders=True):
        binary = self.root / 'engine/install/release/bin/aibs_motherboard.exe'
        binary.write_text('MZ renderer fixture')
        (binary.parent / 'aibs_capabilities.json').write_text(json.dumps({
            'schema_version': 1, 'sdk_version': '0.8.0', 'target': 'windows-x64',
            'features': {'durable_world': True, 'first_boot_chapter': True}}))
        license_path = self.root / 'engine/install/release/share/AIBS/licenses/Jolt-LICENSE.txt'
        license_path.parent.mkdir(parents=True)
        license_path.write_text('Jolt MIT fixture')
        (license_path.parent / 'SQLite-NOTICE.txt').write_text('SQLite public-domain fixture')
        shaders = binary.parent / 'shaders'
        shaders.mkdir()
        (shaders / 'motherboard.vs.cso').write_bytes(b'vertex fixture')
        if both_shaders:
            (shaders / 'motherboard.ps.cso').write_bytes(b'pixel fixture')

    def add_creator_fixture(self, *, both_shaders=True):
        self.add_renderer_fixture(both_shaders=both_shaders)
        for executable in ('aibs_creator_host.exe', 'aibs_content_host.exe', 'aibs_creator_viewport.exe'):
            (self.root / 'engine/install/release/bin' / executable).write_text('MZ creator fixture')

    def test_include_player_collects_complete_native_renderer_and_creator(self):
        self.add_creator_fixture()
        plan = self.stage(include_player=True)
        paths = {item['relative'] for item in plan['files']}
        self.assertIn('game_assets/player/aibs_player.exe', paths)
        self.assertIn('game_assets/player/aibs_motherboard.exe', paths)
        self.assertIn('game_assets/player/aibs_creator_host.exe', paths)
        self.assertIn('game_assets/player/aibs_content_host.exe', paths)
        self.assertIn('game_assets/player/aibs_creator_viewport.exe', paths)
        self.assertIn('game_assets/player/shaders/motherboard.vs.cso', paths)
        self.assertIn('game_assets/player/shaders/motherboard.ps.cso', paths)
        self.assertIn('game_assets/player/Jolt-LICENSE.txt', paths)
        self.assertIn('game_assets/player/SQLite-NOTICE.txt', paths)
        self.assertIn('game_assets/player/aibs_capabilities.json', paths)
        self.assertTrue(json.loads((self.work / 'source/game_assets/player/aibs_capabilities.json').read_text())
                        ['features']['first_boot_chapter'])
        self.assertEqual((self.work / 'source/game_assets/player/SQLite-NOTICE.txt').read_text(),
                         'SQLite public-domain fixture')
        metadata = json.loads((self.work / 'source/game_release.json').read_text())
        self.assertTrue(metadata['renderer_included'])
        spec = (self.work / 'AI_BS_GameRelease.spec').read_text()
        for executable in ('aibs_creator_host.exe', 'aibs_content_host.exe', 'aibs_creator_viewport.exe'):
            self.assertIn('game_assets/player/' + executable, spec)
        self.assertIn('PyQt6.QtNetwork', spec)
        self.assertTrue(plan['creatorIncluded'])
        self.assertTrue(plan['typedCreatorIncluded'])
        self.assertTrue(plan['localAiAuthoringIncluded'])

    def test_include_player_rejects_player_only_bundle_before_staging(self):
        with self.assertRaises(FileNotFoundError):
            self.stage(include_player=True)
        self.assertFalse(self.work.exists())
        self.assertFalse(self.release.exists())

    def test_include_player_requires_every_native_release_asset_before_staging(self):
        self.add_creator_fixture()
        relative_paths = [
            'engine/install/release/bin/' + name for name in (
                'aibs_player.exe', 'aibs_motherboard.exe', 'aibs_creator_host.exe',
                'aibs_content_host.exe', 'aibs_creator_viewport.exe', 'aibs_capabilities.json',
                'shaders/motherboard.vs.cso', 'shaders/motherboard.ps.cso')
        ] + ['engine/install/release/share/AIBS/licenses/' + name
             for name in ('Jolt-LICENSE.txt', 'SQLite-NOTICE.txt')]
        for relative in relative_paths:
            path = self.root / relative
            contents = path.read_bytes()
            path.unlink()
            with self.subTest(asset=relative):
                with self.assertRaises(FileNotFoundError):
                    self.stage(include_player=True)
                self.assertFalse(self.work.exists())
                self.assertFalse(self.release.exists())
            path.write_bytes(contents)

    def test_source_graph_explicitly_contains_all_creator_modules_without_importing_them(self):
        expected = {'native_studio.game_engine', *(f'native_studio.game_engine.{name}' for name in (
            'project_model', 'creator_wire', 'creator_client', 'creator_payload', 'creator_commands',
            'creator_view', 'creator_viewport', 'content_commands', 'content_client', 'content_jobs',
            'content_proposals', 'content_preview', 'content_play', 'content_view', 'content_ai', 'asset_view'))}
        patch.stopall()
        with patch.object(builder._graph, 'native_modules', return_value=['native_studio', 'native_studio.app']):
            with patch.dict('sys.modules', {name: None for name in expected}):
                modules = builder.native_modules()
        self.assertTrue(expected.issubset(modules), expected.difference(modules))
        self.assertIn('native_studio.game_release_smoke', modules)
        self.assertIn('native_studio.asset_release_smoke', modules)

    def test_stages_creator_package_init_as_package_source(self):
        modules = ['native_studio', 'native_studio.app', 'native_studio.game_build_view',
                   'native_studio.game_build_monitor', 'native_studio.game_engine',
                   'native_studio.game_engine.content_ai']
        package = self.root / 'native_studio/game_engine'
        package.mkdir()
        (package / '__init__.py').write_text('# package fixture')
        (package / 'content_ai.py').write_text('from PyQt6.QtNetwork import QNetworkAccessManager')
        with patch.object(builder, 'native_modules', return_value=modules):
            plan = self.stage()
        paths = {item['relative'] for item in plan['files']}
        self.assertIn('native_studio/game_engine/__init__.py', paths)
        self.assertIn('native_studio/game_engine/content_ai.py', paths)

    def test_native_renderer_requires_both_shaders_before_staging(self):
        self.add_creator_fixture(both_shaders=False)
        with self.assertRaises(FileNotFoundError):
            self.stage(include_player=True)
        self.assertFalse(self.work.exists())

    def test_native_renderer_requires_sqlite_notice_before_staging(self):
        self.add_creator_fixture()
        (self.root / 'engine/install/release/share/AIBS/licenses/SQLite-NOTICE.txt').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage(include_player=True)
        self.assertFalse(self.work.exists())
        self.assertFalse(self.release.exists())

    def test_renderer_is_not_collected_without_include_player(self):
        self.add_creator_fixture()
        plan = self.stage()
        self.assertFalse(any(item['relative'].endswith('.exe') for item in plan['files']))
        metadata = json.loads((self.work / 'source/game_release.json').read_text())
        for flag in ('player_included', 'renderer_included', 'creator_included',
                     'typed_creator_included', 'creator_viewport_included', 'local_ai_authoring_included'):
            self.assertIs(metadata[flag], False)

    def test_native_renderer_requires_adjacent_capabilities_before_staging(self):
        self.add_creator_fixture()
        (self.root / 'engine/install/release/bin/aibs_capabilities.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage(include_player=True)
        self.assertFalse(self.work.exists())
        self.assertFalse(self.release.exists())

    def test_preserves_existing_release_and_staging(self):
        self.release.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse(self.work.exists())

    def test_missing_asset_stops_before_staging(self):
        (self.root / 'frontend/public/bs-game/vendor/three-r128.min.js').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage()
        self.assertFalse(self.work.exists())

    def test_player_is_opt_in(self):
        plan = self.stage()
        self.assertFalse(any(item['relative'].endswith('aibs_player.exe') for item in plan['files']))

    def test_does_not_collect_private_source_files(self):
        self.add_creator_fixture()
        (self.root / '.env').write_text('secret-fixture')
        private = self.root / 'frontend/public/bs-game/private-save.aibs'
        private.write_text('private fixture')
        for name in ('original-book.docx', 'family-photo.jpg', 'private-save.sqlite',
                     'model.gguf', 'model.safetensors', 'local-config.json', 'undeclared-helper.exe'):
            (self.root / 'engine/install/release/bin' / name).write_text('private fixture')
        plan = self.stage(include_player=True)
        contents = '\n'.join(item['relative'] for item in plan['files'])
        self.assertNotIn('.env', contents)
        self.assertNotIn('.aibs', contents)
        self.assertNotIn('ledger', contents.lower())
        self.assertNotIn('original-book', contents)
        self.assertNotIn('family-photo', contents)
        self.assertNotIn('private-save', contents)
        self.assertNotIn('model.', contents)
        self.assertNotIn('local-config', contents)
        self.assertNotIn('undeclared-helper', contents)

    def test_version_and_output_must_agree(self):
        self.release = self.root / 'native_studio/releases/v5.329.86'
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse(self.work.exists())

    def test_changed_frozen_input_is_rejected_before_build(self):
        self.stage()
        (self.work / 'source/native_studio/app.py').write_text('# changed')
        with self.assertRaises(ValueError):
            builder.validate_build(self.work)

    def test_public_hosting_receipt_excludes_unrecognized_keys(self):
        evidence = self.root / 'public-hosting.json'
        evidence.write_text(json.dumps({'status':'passed','origin':'https://ai-bs-dashboard.web.app',
            'verified_at':'2026-11-01T00:00:00Z','private_token':'never copy'}))
        self.stage(hosting_verification=evidence)
        metadata = json.loads((self.work / 'source/game_release.json').read_text())
        self.assertEqual(metadata['hosting']['status'], 'passed')
        self.assertNotIn('private_token', json.dumps(metadata))

    def add_asset_profile(self):
        self.add_creator_fixture()
        sdk = self.root / 'engine/install/0.9.0/release'
        shutil.copytree(self.root / 'engine/install/release', sdk)
        (sdk / 'bin/aibs_assetc.exe').write_bytes(b'MZ explicit new SDK cooker')
        (sdk / 'bin/aibs_motherboard.exe').write_bytes(b'MZ explicit new SDK player')
        pack = self.root / 'engine/assets/cooked/reference'
        pack.mkdir(parents=True)
        identity = '11111111-1111-4111-8111-111111111111'
        payload = b'CPU envelope fixture; native decoder is separately verified'
        mesh = b'AIBMesh1' + struct.pack('<II', 1, len(payload)) + hashlib.sha256(payload).digest() + payload
        sha = hashlib.sha256(mesh).hexdigest()
        (pack / (sha + '.aibmesh')).write_bytes(mesh)
        (pack / 'catalog.aibcat').write_text(f'AIBCAT 1\n{identity} {sha} {sha}.aibmesh\n', newline='')
        license_bytes = b'Self-authored test fixture; no external source rights claimed.\n'
        (pack / 'LICENSE.txt').write_bytes(license_bytes)
        info = {'schema_version': 1, 'asset_id': identity, 'name': 'Reference part',
            'source': {'sha256': 'a' * 64, 'bytes': 20},
            'materials': {'sha256': 'b' * 64, 'bytes': 30},
            'license': {'sha256': hashlib.sha256(license_bytes).hexdigest(), 'bytes': len(license_bytes)},
            'license_review': 'Supplied declaration copied verbatim; ownership/permission not inferred',
            'importer': {'name': 'aibs-obj', 'format_version': 1},
            'options': {'units': 'meters', 'up_axis': '+Y', 'axis_conversion': 'none',
                'material_model': 'opaque-base-color-emission-v1',
                'external_material_libraries': 'ignored-explicit-material-table-only'},
            'cooked': {'file': sha + '.aibmesh', 'sha256': sha, 'bytes': len(mesh)}}
        (pack / 'provenance.json').write_text(json.dumps(info))
        return sdk, pack, sha

    def test_explicit_sdk_and_reference_profile_stages_only_22_declared_assets(self):
        sdk, pack, sha = self.add_asset_profile()
        old = (self.root / 'engine/install/release/bin/aibs_motherboard.exe').read_bytes()
        plan = self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
        paths = {item['relative'] for item in plan['files']}
        self.assertIn('game_assets/player/aibs_assetc.exe', paths)
        expected = {'game_assets/reference_part/' + name for name in
            ('catalog.aibcat', sha + '.aibmesh', 'LICENSE.txt', 'provenance.json')}
        self.assertTrue(expected.issubset(paths))
        self.assertEqual(len([path for path in paths if not path.startswith('native_studio/')]), 22)
        self.assertEqual((self.work / 'source/game_assets/player/aibs_motherboard.exe').read_bytes(),
                         b'MZ explicit new SDK player')
        self.assertEqual((self.root / 'engine/install/release/bin/aibs_motherboard.exe').read_bytes(), old)
        self.assertEqual(plan['nativeSdk'], 'engine/install/0.9.0/release')
        self.assertEqual(plan['assetPack'], 'engine/assets/cooked/reference')
        self.assertEqual(plan['referencePart']['sha256'], sha)
        metadata = json.loads((self.work / 'source/game_release.json').read_text())
        self.assertTrue(metadata['asset_pipeline_included'])
        self.assertTrue(metadata['reference_part_included'])
        self.assertNotIn(str(sdk), json.dumps(metadata))

    def test_asset_profile_requires_player_and_cooker_before_any_staging_write(self):
        sdk, pack, _ = self.add_asset_profile()
        with self.assertRaisesRegex(ValueError, 'include.player'):
            self.stage(native_sdk=sdk, asset_pack=pack)
        self.assertFalse(self.work.exists())
        (sdk / 'bin/aibs_assetc.exe').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
        self.assertFalse(self.work.exists())

    def test_reference_profile_rejects_hash_traversal_extra_private_or_malformed_files(self):
        sdk, pack, sha = self.add_asset_profile()
        catalog = pack / 'catalog.aibcat'
        original = catalog.read_bytes()
        variants = [original.replace((sha + '.aibmesh').encode(), ('../' + sha + '.aibmesh').encode()),
                    original + original.split(b'\n')[1] + b'\n', original.replace(b'AIBCAT 1', b'AIBCAT 2')]
        for value in variants:
            with self.subTest(value=value[:20]):
                catalog.write_bytes(value)
                with self.assertRaises(ValueError):
                    self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
                self.assertFalse(self.work.exists())
        catalog.write_bytes(original)
        mesh = pack / (sha + '.aibmesh')
        original_mesh = mesh.read_bytes()
        mesh.write_bytes(original_mesh + b'tampered')
        with self.assertRaisesRegex(ValueError, 'hash|digest|mesh'):
            self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
        mesh.write_bytes(original_mesh)
        (pack / 'original.obj').write_text('private source OBJ must not enter package')
        with self.assertRaisesRegex(ValueError, 'exact|undeclared'):
            self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
        (pack / 'original.obj').unlink()
        provenance = pack / 'provenance.json'
        info = json.loads(provenance.read_text())
        info['source']['path'] = 'C:/private/original.obj'
        provenance.write_text(json.dumps(info))
        with self.assertRaisesRegex(ValueError, 'provenance|private'):
            self.stage(include_player=True, native_sdk=sdk, asset_pack=pack)
        self.assertFalse(self.work.exists())

    def test_sdk_root_must_remain_inside_project_and_unredirected(self):
        sdk, _, _ = self.add_asset_profile()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.stage(include_player=True, native_sdk=self.root.parent)
        linked = self.root / 'engine/install/linked-sdk'
        with patch.object(Path, 'is_junction', lambda path: path == linked):
            with self.assertRaisesRegex(ValueError, 'Redirected'):
                self.stage(include_player=True, native_sdk=linked)
        self.assertFalse(self.work.exists())

    def test_explicit_sdk_without_reference_pack_keeps_legacy_asset_profile(self):
        sdk, _, _ = self.add_asset_profile()
        plan = self.stage(include_player=True, native_sdk=sdk)
        paths = {row['relative'] for row in plan['files']}
        self.assertNotIn('game_assets/player/aibs_assetc.exe', paths)
        self.assertFalse(any(path.startswith('game_assets/reference_part/') for path in paths))
        self.assertFalse(plan['assetPipelineIncluded'])
        self.assertFalse(plan['referencePartIncluded'])

    def test_reference_provenance_requires_integer_importer_version(self):
        _, pack, _ = self.add_asset_profile()
        file = pack / 'provenance.json'
        info = json.loads(file.read_text())
        info['importer']['format_version'] = True
        file.write_text(json.dumps(info))
        with self.assertRaisesRegex(ValueError, 'provenance|importer'):
            builder._asset_contract.validate_reference_pack(pack)


if __name__ == '__main__':
    unittest.main()
