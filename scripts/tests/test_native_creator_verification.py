"""Static creator release checks using synthetic packages; never launch an app."""
import importlib.util
import json
from pathlib import Path
import py_compile
import struct
import hashlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'native_creator_verifier', ROOT / 'scripts/verify_native_creator_release.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

GAME_MODULES = [
    'native_studio.game_engine' + suffix for suffix in (
        '', '.project_model', '.creator_wire', '.creator_viewport', '.creator_view',
        '.creator_payload', '.creator_commands', '.creator_client', '.content_view',
        '.content_proposals', '.content_preview', '.content_play', '.content_jobs',
        '.content_commands', '.content_client', '.content_ai')]
MODULES = ['native_studio', 'native_studio.app', 'native_studio.game_build_view',
           'native_studio.game_build_monitor', 'native_studio.game_release_smoke', *GAME_MODULES]
ASSETS = [
    'version.txt', 'assets/psychedelic_theme.jpg', 'assets/favicon.ico',
    'game_assets/playground/index.html', 'game_assets/playground/vendor/three-r128.min.js',
    'game_assets/playground/vendor/THREE-LICENSE.txt',
    *('game_assets/player/' + name for name in (
        'aibs_player.exe', 'aibs_motherboard.exe', 'aibs_creator_host.exe',
        'aibs_content_host.exe', 'aibs_creator_viewport.exe', 'aibs_capabilities.json',
        'shaders/motherboard.vs.cso', 'shaders/motherboard.ps.cso',
        'Jolt-LICENSE.txt', 'SQLite-NOTICE.txt'))]


class CreatorVerificationTests(unittest.TestCase):
    def test_modern_shader_cooker_and_notice_payloads_are_required_and_verified(self):
        relative='game_assets/player/aibs_capabilities.json'
        content=json.dumps({'schema_version':1,'sdk_version':'0.11.0','features':{'chapter_content_v3':True}}).encode()
        for base in (self.source,self.internal):(base/relative).write_bytes(content)
        next(row for row in self.rows if row['relative']==relative).update(bytes=len(content),sha256=verifier.digest(self.source/relative))
        self.write_plan()
        with self.assertRaisesRegex(ValueError,'Missing required creator assets'):verifier.verify_release(self.work)
        for name in verifier.WARM_PLAYER_FILES:
            self.write_staged('game_assets/player/'+name,b'bounded modern runtime fixture',packaged=True)
        self.write_plan()
        self.collection.write_text(repr(([((path.relative_to(self.package).as_posix().removeprefix('_internal/')),
            str(path), 'EXECUTABLE' if path == self.exe else 'DATA')
            for path in self.package.rglob('*') if path.is_file()],)))
        report=verifier.verify_release(self.work)
        self.assertEqual(report['status'],'passed')
        target=self.internal/'game_assets/player/shaders/character.ps.cso'
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Packaged asset differs'):verifier.verify_release(self.work)

    def add_placement_profile(self,*,capable=True):
        self.add_asset_profile()
        for module in ('native_studio.game_engine.project_assets','native_studio.placement_release_smoke'):
            code='def fixture():\n    return "placement"\n'
            self.write_staged(module.replace('.','/')+'.py',code.encode())
            self.codes[module]=compile(code,'/build-machine/'+module+'.py','exec')
            self.plan['modules'].append(module)
        relative='game_assets/player/aibs_capabilities.json'
        content=json.dumps({'schema_version':1,'sdk_version':'0.10.0' if capable else '0.9.0',
            'features':{'chapter_asset_placement_v1':capable}}).encode()
        for base in (self.source,self.internal):(base/relative).write_bytes(content)
        next(row for row in self.rows if row['relative']==relative).update(bytes=len(content),sha256=verifier.digest(self.source/relative))
        self.plan.update(persistentAssetPlacementIncluded=True,nativeSdk='engine/install/0.10.0/release')
        self.metadata['persistent_asset_placement_included']=True
        self.update_metadata()

    def test_placement_profile_requires_capability_modules_and_matching_metadata(self):
        self.add_placement_profile()
        report=verifier.verify_release(self.work)
        self.assertTrue(report['persistent_asset_placement_included'])
        module='native_studio.game_engine.project_assets'
        self.plan['modules'].remove(module);self.write_plan()
        with self.assertRaisesRegex(ValueError,'project_assets'):
            verifier.verify_release(self.work)
        self.plan['modules'].append(module)
        self.metadata['persistent_asset_placement_included']=False;self.update_metadata()
        with self.assertRaisesRegex(ValueError,'metadata|placement'):
            verifier.verify_release(self.work)

    def test_placement_claim_cannot_be_added_to_a_legacy_sdk(self):
        self.add_placement_profile(capable=False)
        with self.assertRaisesRegex(ValueError,'capabilit|placement'):
            verifier.verify_release(self.work)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'freeze'
        self.source = self.work / 'source'
        self.output = self.root / 'v5.329.95'
        self.package = self.output / 'AI_BS_Studio'
        self.internal = self.package / '_internal'
        self.internal.mkdir(parents=True)
        self.source.mkdir(parents=True)
        self.exe = self.package / 'AI_BS_Studio.exe'
        self.exe.write_bytes(b'MZ synthetic studio')
        self.codes = {}
        self.rows = []
        for index, module in enumerate(MODULES):
            relative = ('native_studio/__init__.py' if module == 'native_studio' else
                        'native_studio/game_engine/__init__.py' if module.endswith('.game_engine') else
                        module.replace('.', '/') + '.py')
            source = 'def fixture():\n    return ' + str(index) + '\n'
            self.write_staged(relative, source.encode())
            self.codes[module] = compile(source, '/build-machine/' + relative, 'exec')
        for relative in ASSETS:
            content = ('v5.329.95' if relative == 'version.txt' else 'asset fixture').encode()
            if relative.endswith('aibs_capabilities.json'):
                content = json.dumps({'schema_version': 1, 'features': {
                    'durable_world': True, 'first_boot_chapter': True,
                    'creator_numeric_authoring': True}}).encode()
            self.write_staged(relative, content, packaged=True)
        self.metadata = {
            'schema_version': 1, 'app_version': '5.329.95', 'build_kind': 'native-pc-game-hub',
            'backend_bundled': False, 'web_parity_verified': False, 'signed': False,
            'requires_existing_services': True, 'player_included': True,
            'renderer_included': True, 'creator_included': True,
            'typed_creator_included': True, 'creator_viewport_included': True,
            'local_ai_authoring_included': True,
            'local_ai_model_weights_bundled': False, 'local_ai_requires_existing_service': True,
            'playground_values': 'simulated', 'native_save_access_from_playground': False}
        self.write_staged('game_release.json', json.dumps(self.metadata).encode(), packaged=True)
        for relative in ('PyQt6/QtNetwork.pyd', 'PyQt6/Qt6/bin/Qt6Network.dll'):
            file = self.internal / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'MZ Qt fixture')
        spec = self.work / 'AI_BS_GameRelease.spec'
        spec.write_text('# synthetic non-executed freeze specification\n')
        self.plan = {'schema_version': 1, 'work': str(self.work), 'output': str(self.output),
                     'appVersion': '5.329.95', 'files': self.rows, 'modules': MODULES,
                     'includePlayer': True, 'rendererIncluded': True,
                     'creatorIncluded': True, 'typedCreatorIncluded': True,
                     'creatorViewportIncluded': True, 'localAiAuthoringIncluded': True,
                     'applicationExecuted': False, 'signed': False,
                     'specSha256': verifier.digest(spec)}
        self.write_plan()
        self.collection = self.work / 'pyinstaller/AI_BS_GameRelease/COLLECT-00.toc'
        self.collection.parent.mkdir(parents=True)
        self.collection.write_text(repr(([((path.relative_to(self.package).as_posix().removeprefix('_internal/')),
            str(path), 'EXECUTABLE' if path == self.exe else 'DATA')
            for path in self.package.rglob('*') if path.is_file()],)))
        self.addCleanup(patch.stopall)
        self.pe = {'machine': 0x8664, 'subsystem': 2,
                   'file_version': [5, 329, 95, 0], 'product_version': [5, 329, 95, 0],
                   'strings': {'FileVersion': '5.329.95', 'ProductVersion': '5.329.95'}}
        patch.object(verifier, 'read_pe_metadata', return_value=self.pe).start()
        patch.object(verifier, 'read_frozen_archive', side_effect=self.archive).start()

    def write_staged(self, relative, content, packaged=False):
        file = self.source / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
        self.rows.append({'relative': relative, 'bytes': len(content),
                          'sha256': verifier.digest(file)})
        if packaged:
            file = self.internal / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)

    def write_plan(self):
        (self.work / 'plan.json').write_text(json.dumps(self.plan))

    def archive(self, *_args):
        return {'names': set(self.codes), 'code': self.codes,
                'entry_code': self.codes['native_studio.app']}

    def test_complete_fixture_passes_and_claims_only_static_scope(self):
        report = verifier.verify_release(self.work)
        self.assertEqual(report['status'], 'passed')
        self.assertFalse(report['application_executed'])
        self.assertIn('static', report['scope'].lower())
        self.assertEqual(len(report['frozen_module_equivalence']), len(MODULES))
        self.assertEqual(len(report['asset_readback']), len(ASSETS) + 1)
        self.assertTrue(report['qt_network_included'])

    def test_different_build_paths_are_allowed_but_nested_code_changes_are_rejected(self):
        self.codes['native_studio.game_engine.content_ai'] = compile(
            'def fixture():\n    return -999\n', '/another-machine/content_ai.py', 'exec')
        with self.assertRaisesRegex(ValueError, 'code.*content_ai'):
            verifier.verify_release(self.work)

    def test_actual_entry_script_must_match_staged_app(self):
        data = self.archive()
        data['entry_code'] = compile('raise RuntimeError("stale")', 'app.py', 'exec')
        with patch.object(verifier, 'read_frozen_archive', return_value=data):
            with self.assertRaisesRegex(ValueError, 'entry'):
                verifier.verify_release(self.work)

    def test_missing_required_game_module_is_rejected(self):
        self.codes.pop('native_studio.game_engine.content_ai')
        with self.assertRaisesRegex(ValueError, 'content_ai'):
            verifier.verify_release(self.work)

    def test_asset_tampering_and_missing_licenses_are_rejected(self):
        for relative in ('game_assets/player/aibs_content_host.exe',
                         'game_assets/player/SQLite-NOTICE.txt'):
            file = self.internal / relative
            before = file.read_bytes()
            with self.subTest(relative=relative):
                file.write_bytes(before + b'wrong')
                with self.assertRaisesRegex(ValueError, 'asset'):
                    verifier.verify_release(self.work)
                file.write_bytes(before)
        (self.internal / 'game_assets/player/Jolt-LICENSE.txt').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            verifier.verify_release(self.work)

    def test_plan_cannot_omit_required_creator_asset(self):
        self.plan['files'] = [row for row in self.rows if not row['relative'].endswith('aibs_creator_viewport.exe')]
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'required.*asset|asset.*required'):
            verifier.verify_release(self.work)

    def test_undeclared_assets_and_secret_or_model_files_are_rejected(self):
        for relative in ('game_assets/player/extra.json', '.env', 'models/private.gguf',
                         'pytorch_model.bin', 'unrelated.exe', 'memoir/chapter.txt',
                         'untracked-public.txt'):
            file = self.internal / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            with self.subTest(relative=relative):
                file.write_bytes(b'private fixture')
                with self.assertRaisesRegex(ValueError, '(?i)undeclared|private|model'):
                    verifier.verify_release(self.work)
                file.unlink()

    def test_even_declared_collection_cannot_contain_model_weights(self):
        file = self.internal / 'pytorch_model.bin'
        file.write_bytes(b'weight fixture')
        import ast
        collection = ast.literal_eval(self.collection.read_text())[0]
        collection.append(('pytorch_model.bin', str(file), 'DATA'))
        self.collection.write_text(repr((collection,)))
        with self.assertRaisesRegex(ValueError, '(?i)private|model'):
            verifier.verify_release(self.work)

    def test_collection_manifest_must_account_for_every_packaged_file(self):
        self.collection.write_text(repr(([],)))
        with self.assertRaisesRegex(ValueError, '(?i)collection|inventory'):
            verifier.verify_release(self.work)

    def test_staged_secret_inputs_cannot_be_admitted_by_editing_plan(self):
        self.write_staged('private/memoir.txt', b'never include')
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'declared|private'):
            verifier.verify_release(self.work)

    def add_cache(self, source_relative='native_studio/__init__.py', invalidation_mode=None):
        source = self.source / source_relative
        options = {} if invalidation_mode is None else {'invalidation_mode': invalidation_mode}
        cache = Path(py_compile.compile(str(source), doraise=True, **options))
        return source, cache

    def test_generated_cache_requires_matching_timestamp_or_source_hash_and_code(self):
        for mode in (py_compile.PycInvalidationMode.TIMESTAMP,
                     py_compile.PycInvalidationMode.CHECKED_HASH,
                     py_compile.PycInvalidationMode.UNCHECKED_HASH):
            with self.subTest(mode=mode):
                source, cache = self.add_cache(invalidation_mode=mode)
                report = verifier.verify_release(self.work)
                self.assertEqual(report['status'], 'passed')
                rows = report['generated_staged_caches_verified']
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['source_relative'], 'native_studio/__init__.py')
                self.assertTrue(rows[0]['code_matches_staged_source'])
                cache.unlink()

    def test_generated_cache_rejects_altered_header_or_code(self):
        source, cache = self.add_cache()
        original = cache.read_bytes()
        wrong_source = self.root / 'unrelated.py'
        wrong_source.write_text('raise RuntimeError("must never run")\n')
        wrong_cache = Path(py_compile.compile(str(wrong_source), doraise=True))
        variants = {
            'magic': b'bad!' + original[4:],
            'flags': original[:4] + struct.pack('<I', 4) + original[8:],
            'timestamp': original[:8] + b'\0' * 4 + original[12:],
            'length': original[:12] + struct.pack('<I', len(source.read_bytes()) + 1) + original[16:],
            'code': original[:16] + wrong_cache.read_bytes()[16:],
            'trailing': original + b'unrelated appended data'}
        for label, content in variants.items():
            with self.subTest(label=label):
                cache.write_bytes(content)
                with self.assertRaisesRegex(ValueError, '(?i)cache'):
                    verifier.verify_release(self.work)
        cache.write_bytes(original)

    def test_hash_cache_rejects_wrong_source_hash(self):
        source, cache = self.add_cache(invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
        original = cache.read_bytes()
        cache.write_bytes(original[:8] + b'\0' * 8 + original[16:])
        with self.assertRaisesRegex(ValueError, '(?i)cache'):
            verifier.verify_release(self.work)

    def test_cache_for_undeclared_source_or_wrong_cache_tag_is_rejected(self):
        _, cache = self.add_cache()
        extra = cache.with_name('unrelated.cpython-312.pyc')
        extra.write_bytes(cache.read_bytes())
        with self.assertRaisesRegex(ValueError, '(?i)cache|undeclared'):
            verifier.verify_release(self.work)
        extra.unlink()
        cache.rename(cache.with_name('__init__.cpython-999.pyc'))
        with self.assertRaisesRegex(ValueError, '(?i)cache|undeclared'):
            verifier.verify_release(self.work)

    def test_staged_bytes_must_match_freeze_plan_including_length(self):
        self.plan['files'][0]['bytes'] += 1
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'staged'):
            verifier.verify_release(self.work)

    def test_path_traversal_and_duplicate_plan_rows_are_rejected(self):
        for row in ({'relative': '../escape.py', 'bytes': 0, 'sha256': '0' * 64}, self.rows[0]):
            with self.subTest(relative=row['relative']):
                self.plan['files'] = [*self.rows, row]
                self.write_plan()
                with self.assertRaisesRegex(ValueError, 'path|duplicate'):
                    verifier.verify_release(self.work)

    def test_wrong_pe_versions_are_rejected(self):
        self.pe['strings']['ProductVersion'] = '5.329.94'
        with self.assertRaisesRegex(ValueError, 'version'):
            verifier.verify_release(self.work)

    def test_absent_qt_network_and_backend_pyz_are_rejected(self):
        (self.internal / 'PyQt6/QtNetwork.pyd').unlink()
        with self.assertRaisesRegex(ValueError, 'QtNetwork'):
            verifier.verify_release(self.work)
        (self.internal / 'PyQt6/QtNetwork.pyd').write_bytes(b'MZ fixture')
        data = self.archive()
        data['names'].add('backend.private_source')
        with patch.object(verifier, 'read_frozen_archive', return_value=data):
            with self.assertRaisesRegex(ValueError, 'backend'):
                verifier.verify_release(self.work)

    def test_metadata_cannot_claim_backend_bundle_or_omit_creator(self):
        self.metadata['backend_bundled'] = True
        content = json.dumps(self.metadata).encode()
        row = next(row for row in self.rows if row['relative'] == 'game_release.json')
        for base in (self.source, self.internal):
            (base / 'game_release.json').write_bytes(content)
        row.update(bytes=len(content), sha256=verifier.digest(self.source / 'game_release.json'))
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'metadata'):
            verifier.verify_release(self.work)

    def test_cli_writes_failed_report_and_nonzero_for_missing_work(self):
        report = self.root / 'failure.json'
        code = verifier.main(['--work', str(self.root / 'missing'), '--report', str(report)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(report.read_text())['status'], 'failed')
        self.assertFalse(json.loads(report.read_text())['application_executed'])

    def add_asset_profile(self):
        identity = '11111111-1111-4111-8111-111111111111'
        payload = b'CPU package envelope fixture'
        mesh = b'AIBMesh1' + struct.pack('<II', 1, len(payload)) + hashlib.sha256(payload).digest() + payload
        sha = hashlib.sha256(mesh).hexdigest()
        reference = {'asset_id': identity, 'sha256': sha, 'file': sha + '.aibmesh'}
        license_bytes = b'Self-authored synthetic fixture.\n'
        provenance = {'schema_version': 1, 'asset_id': identity, 'name': 'Reference part',
            'source': {'sha256': 'a' * 64, 'bytes': 20}, 'materials': {'sha256': 'b' * 64, 'bytes': 30},
            'license': {'sha256': hashlib.sha256(license_bytes).hexdigest(), 'bytes': len(license_bytes)},
            'license_review': 'Supplied declaration copied verbatim; ownership/permission not inferred',
            'importer': {'name': 'aibs-obj', 'format_version': 1},
            'options': {'units': 'meters', 'up_axis': '+Y', 'axis_conversion': 'none',
                'material_model': 'opaque-base-color-emission-v1',
                'external_material_libraries': 'ignored-explicit-material-table-only'},
            'cooked': {'file': reference['file'], 'sha256': sha, 'bytes': len(mesh)}}
        values = {'catalog.aibcat': f'AIBCAT 1\n{identity} {sha} {sha}.aibmesh\n'.encode(),
                  reference['file']: mesh, 'LICENSE.txt': license_bytes,
                  'provenance.json': json.dumps(provenance).encode()}
        for name, content in values.items():
            self.write_staged('game_assets/reference_part/' + name, content, packaged=True)
        self.write_staged('game_assets/player/aibs_assetc.exe', b'MZ explicit cooker', packaged=True)
        module = 'native_studio.game_engine.asset_view'
        source = 'def fixture():\n    return "assets tab"\n'
        self.write_staged(module.replace('.', '/') + '.py', source.encode())
        self.codes[module] = compile(source, '/build-machine/asset_view.py', 'exec')
        helper = 'native_studio.asset_release_smoke'
        helper_source = 'def fixture():\n    return "explicit asset smoke"\n'
        self.write_staged(helper.replace('.', '/') + '.py', helper_source.encode())
        self.codes[helper] = compile(helper_source, '/build-machine/asset_release_smoke.py', 'exec')
        self.plan['modules'] = [*MODULES, module, helper]
        self.plan.update(assetPipelineIncluded=True, referencePartIncluded=True, referencePart=reference,
                         nativeSdk='engine/install/0.9.0/release', assetPack='engine/assets/cooked/reference')
        self.metadata.update(asset_pipeline_included=True, reference_part_included=True, reference_part=reference)
        self.update_metadata()
        self.collection.write_text(repr(([((path.relative_to(self.package).as_posix().removeprefix('_internal/')),
            str(path), 'EXECUTABLE' if path == self.exe else 'DATA')
            for path in self.package.rglob('*') if path.is_file()],)))
        return reference

    def update_metadata(self):
        content = json.dumps(self.metadata).encode()
        for base in (self.source, self.internal):
            (base / 'game_release.json').write_bytes(content)
        row = next(row for row in self.rows if row['relative'] == 'game_release.json')
        row.update(bytes=len(content), sha256=verifier.digest(self.source / 'game_release.json'))
        self.write_plan()

    def test_new_explicit_asset_profile_verifies_22_assets_and_asset_view(self):
        reference = self.add_asset_profile()
        report = verifier.verify_release(self.work)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(len(report['asset_readback']), 22)
        self.assertTrue(report['asset_pipeline_included'])
        self.assertEqual(report['reference_part'], reference)
        self.assertFalse(report['application_executed'])

    def test_asset_profile_requires_declared_asset_view_and_exact_digest_identity(self):
        reference = self.add_asset_profile()
        module = 'native_studio.game_engine.asset_view'
        self.plan['modules'].remove(module)
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'asset_view'):
            verifier.verify_release(self.work)
        self.plan['modules'].append(module)
        self.plan['referencePart'] = dict(reference, sha256='0' * 64)
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'reference|digest|catalog'):
            verifier.verify_release(self.work)

    def test_asset_profile_rejects_missing_license_extra_mesh_and_false_metadata(self):
        self.add_asset_profile()
        self.metadata['asset_pipeline_included'] = False
        self.update_metadata()
        with self.assertRaisesRegex(ValueError, 'metadata'):
            verifier.verify_release(self.work)
        self.metadata['asset_pipeline_included'] = True
        self.update_metadata()
        extra = self.internal / 'game_assets/reference_part/undeclared.aibmesh'
        extra.write_bytes(b'cannot admit a wildcard mesh')
        with self.assertRaisesRegex(ValueError, 'undeclared|exact|asset'):
            verifier.verify_release(self.work)
        extra.unlink()
        (self.source / 'game_assets/reference_part/LICENSE.txt').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            verifier.verify_release(self.work)


if __name__ == '__main__':
    unittest.main()
