"""Static curated-opening admission; fixtures are envelopes, not native geometry."""
import importlib.util
import json
import hashlib
import shutil
import struct
import uuid
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.tests.test_native_game_release import NativeGameReleaseTests, builder


class OpeningReleaseBundleTests(NativeGameReleaseTests):
    def setup_opening(self):
        sdk = self.modern_sdk(complete=True)
        capabilities = {'schema_version': 1, 'sdk_version': '0.15.0', 'features': {
            'chapter_content_v3': True, 'character_asset_v2': True,
            'chapter-initial-view-v1': True, 'chapter-workshop-commissioning-v1': True}}
        (sdk/'bin/aibs_capabilities.json').write_text(json.dumps(capabilities))
        (sdk/'bin/aibs_warm_opening_project.exe').write_bytes(b'MZ synthetic factory fixture')
        modules = ['native_studio', 'native_studio.app', 'native_studio.game_build_view',
                   'native_studio.game_build_monitor', 'native_studio.game_engine',
                   'native_studio.game_engine.opening_assets', 'native_studio.game_engine.opening_project']
        package = self.root/'native_studio/game_engine'; package.mkdir()
        for name in ('__init__', 'opening_assets', 'opening_project'):
            (package/(name+'.py')).write_text('# synthetic static module only\n')
        builder.native_modules.return_value = modules
        self.opening = self.root/'engine/assets/curated-opening'; self.opening.mkdir(parents=True)
        self.manifest = {'version': 1, 'roles': {}}
        for role in builder._asset_contract.OPENING_ROLES:
            identity = str(uuid.uuid4()); character = role == 'adam'; surface = role == 'nook'
            body = b'SYNTHETIC_ENVELOPE_ONLY_NO_NATIVE_DECODE\n' + role.encode()
            payload = (b'AIBChar2' if character else b'AIBSurf2' if surface else b'AIBMesh1') + struct.pack('<II', 2 if character or surface else 1, len(body)) + hashlib.sha256(body).digest() + body
            asset_sha = hashlib.sha256(payload).hexdigest(); filename = asset_sha + ('.aibchar' if character else '.aibsurf' if surface else '.aibmesh')
            license_bytes = b'Synthetic static test license\n'
            provenance = json.dumps({'schema_version': 2 if character or surface else 1, 'asset_id': identity,
                'license': {'sha256': hashlib.sha256(license_bytes).hexdigest(), 'bytes': len(license_bytes)},
                'cooked': {'file': filename, 'sha256': asset_sha, 'bytes': len(payload)}}).encode()
            raw = {'catalog.aibcat': ((b'AIBCAT 2\ncharacter ' if character else b'AIBCAT 2\nsurface ' if surface else b'AIBCAT 1\n') + (identity+' '+asset_sha+' '+filename+'\n').encode()),
                   filename: payload, 'LICENSE.txt': license_bytes, 'provenance.json': provenance}
            directory = self.opening/'packs'/role; directory.mkdir(parents=True)
            manifest = 'AIBPACK '+('2' if character or surface else '1')+'\n'
            for name, value in sorted(raw.items()):
                (directory/name).write_bytes(value)
                manifest += name+' '+str(len(value))+' '+hashlib.sha256(value).hexdigest()+'\n'
            self.manifest['roles'][role] = {'directory': 'packs/'+role, 'asset_id': identity,
                'asset_sha256': asset_sha, 'pack_sha256': hashlib.sha256(manifest.encode()).hexdigest()}
        self.write_manifest()
        return sdk

    def write_manifest(self):
        (self.opening/'opening-assets.json').write_text(json.dumps(self.manifest)+'\n')

    def inspect(self):
        return builder._asset_contract.validate_opening_bundle(self.opening)

    def set_wire_version(self, role, version):
        entry=self.manifest['roles'][role];folder=self.opening/entry['directory']
        old=next(p for p in folder.iterdir() if p.suffix in ('.aibchar','.aibmesh','.aibsurf'))
        payload=bytearray(old.read_bytes());struct.pack_into('<I',payload,8,version)
        digest=hashlib.sha256(payload).hexdigest();name=digest+old.suffix
        old.unlink();(folder/name).write_bytes(payload)
        entry['asset_sha256']=digest
        header=b'AIBCAT 2\ncharacter ' if role=='adam' else b'AIBCAT 2\nsurface ' if old.suffix=='.aibsurf' else b'AIBCAT 1\n'
        (folder/'catalog.aibcat').write_bytes(header+(entry['asset_id']+' '+digest+' '+name+'\n').encode())
        provenance=json.loads((folder/'provenance.json').read_text());provenance['cooked']={'file':name,'sha256':digest,'bytes':len(payload)}
        (folder/'provenance.json').write_text(json.dumps(provenance))
        pack='AIBPACK '+('1' if old.suffix=='.aibmesh' else '2')+'\n'
        for child in sorted(folder.iterdir(),key=lambda p:p.name):
            data=child.read_bytes();pack+=child.name+' '+str(len(data))+' '+hashlib.sha256(data).hexdigest()+'\n'
        entry['pack_sha256']=hashlib.sha256(pack.encode()).hexdigest();self.write_manifest()

    def test_character_surface_v3_is_admitted_without_claiming_native_decode(self):
        self.setup_opening();self.set_wire_version('adam',3);result=self.inspect()
        self.assertEqual(result['character_payload_version'],3)
        self.assertFalse(result['native_decoded_validation_claimed'])

    def test_character_surface_v3_requires_matching_sdk_before_any_stage_write(self):
        sdk=self.setup_opening();self.set_wire_version('adam',3);caps=sdk/'bin/aibs_capabilities.json';data=json.loads(caps.read_text());data['sdk_version']='0.16.6';caps.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'SDK0.17.0'):
            self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        self.assertFalse(self.work.exists());self.assertFalse(self.release.exists())
        data['sdk_version']='0.17.0';caps.write_text(json.dumps(data))
        plan=self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        self.assertEqual(plan['openingAssets']['character_payload_version'],3)
        self.assertEqual(builder._asset_contract.validate_opening_bundle(self.work/'source/game_assets/opening',plan['openingAssets']),plan['openingAssets'])

    def test_unknown_character_version_and_surface_v3_are_rejected(self):
        self.setup_opening();self.set_wire_version('adam',4)
        with self.assertRaisesRegex(ValueError,'envelope/digest'):self.inspect()
        self.set_wire_version('adam',2);self.set_wire_version('nook',3)
        with self.assertRaisesRegex(ValueError,'envelope/digest'):self.inspect()

    def test_opening_validates_exact_six_pack_envelopes_without_native_decode_claim(self):
        self.setup_opening(); result = self.inspect()
        self.assertEqual(len(result['files']), 25)
        self.assertEqual(result['kinds']['adam'], 'character')
        self.assertEqual(result['kinds']['nook'], 'surface')
        self.assertFalse(result['native_decoded_validation_claimed'])
        self.assertEqual(result['total_bytes'], sum(row['bytes'] for row in result['files']))

    def test_opening_manifest_rejects_unknown_roles_fields_types_and_traversal(self):
        self.setup_opening(); original = json.loads(json.dumps(self.manifest))
        changes = [lambda x: x.update(version=True), lambda x: x['roles'].update(audio=x['roles']['adam']),
                   lambda x: x['roles']['nook'].update(extra=True),
                   lambda x: x['roles']['nook'].update(directory='packs/../../escape'),
                   lambda x: x['roles']['nook'].update(directory='C:/outside'),
                   lambda x: x['roles']['nook'].update(directory='packs/nook\n'),
                   lambda x: x['roles']['nook'].update(asset_id='not-a-uuid'),
                   lambda x: x['roles']['nook'].update(asset_sha256='A'*64)]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                self.manifest=json.loads(json.dumps(original)); change(self.manifest); self.write_manifest()
                with self.assertRaises((ValueError, OSError)): self.inspect()
        self.manifest=original; self.write_manifest(); self.inspect()

    def test_opening_manifest_matches_runtime_16k_limit_before_staging(self):
        sdk=self.setup_opening(); path=self.opening/'opening-assets.json'; raw=path.read_bytes()
        path.write_bytes(raw+b' '*(16*1024-len(raw)+1))
        with self.assertRaisesRegex(ValueError,'byte bound'):
            self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        self.assertFalse(self.work.exists()); self.assertFalse(self.release.exists())

    def test_opening_duplicate_json_key_rejects(self):
        self.setup_opening(); path=self.opening/'opening-assets.json'
        path.write_text(path.read_text().replace('"version": 1', '"version": 1, "version": 1'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.inspect()

    def test_opening_wrong_typed_role_rejects(self):
        self.setup_opening()
        roles=self.manifest['roles']; roles['adam'],roles['fault']=roles['fault'],roles['adam']; self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'type mismatch'): self.inspect()

    def test_opening_payload_corruption_rejects_before_staging(self):
        sdk=self.setup_opening(); entry=self.manifest['roles']['adam']; path=self.opening/entry['directory']/(entry['asset_sha256']+'.aibchar')
        path.write_bytes(path.read_bytes()[:-1]+b'!')
        with self.assertRaisesRegex(ValueError, 'envelope/digest'): self.stage(include_player=True, native_sdk=sdk, opening_assets_root=self.opening)
        self.assertFalse(self.work.exists()); self.assertFalse(self.release.exists())

    def test_opening_changed_license_and_pack_reference_reject(self):
        self.setup_opening(); license_path=self.opening/'packs/nook/LICENSE.txt'; original=license_path.read_bytes()
        license_path.write_bytes(original+b'changed')
        with self.assertRaisesRegex(ValueError,'provenance'): self.inspect()
        license_path.write_bytes(original); self.manifest['roles']['nook']['pack_sha256']='0'*64; self.write_manifest()
        with self.assertRaisesRegex(ValueError,'pack digest'): self.inspect()

    def test_opening_undeclared_private_file_and_empty_directory_reject(self):
        self.setup_opening(); extra=self.opening/'.env'; extra.write_text('synthetic omitted material')
        with self.assertRaisesRegex(ValueError,'undeclared'): self.inspect()
        extra.unlink(); (self.opening/'extra-empty').mkdir()
        with self.assertRaisesRegex(ValueError,'undeclared directory'): self.inspect()

    def test_opening_oversized_payload_rejected_before_content_read(self):
        self.setup_opening(); entry=self.manifest['roles']['fault']; path=self.opening/entry['directory']/(entry['asset_sha256']+'.aibmesh')
        with path.open('r+b')as stream: stream.truncate(32*1024*1024+1)
        with self.assertRaisesRegex(ValueError,'byte bound'): self.inspect()

    def test_opening_requires_player_capabilities_and_factory_before_staging(self):
        sdk=self.setup_opening()
        with self.assertRaisesRegex(ValueError,'complete native player'): self.stage(opening_assets_root=self.opening)
        caps=sdk/'bin/aibs_capabilities.json'; original=caps.read_bytes(); data=json.loads(original)
        data['features']['chapter-workshop-commissioning-v1']=False; caps.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'capability'): self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        caps.write_bytes(original); (sdk/'bin/aibs_warm_opening_project.exe').unlink()
        with self.assertRaises(FileNotFoundError): self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        self.assertFalse(self.work.exists()); self.assertFalse(self.release.exists())

    def test_opening_freezes_complete_bundle_and_retains_no_runtime_claim(self):
        sdk=self.setup_opening(); plan=self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        paths={row['relative']for row in plan['files']}
        self.assertIn(builder._asset_contract.OPENING_FACTORY,paths)
        self.assertEqual(len([p for p in paths if p.startswith('game_assets/opening/')]),25)
        self.assertTrue(plan['warmOpeningIncluded']); self.assertFalse(plan['applicationExecuted'])
        metadata=json.loads((self.work/'source/game_release.json').read_text())
        self.assertTrue(metadata['warm_opening_included']); self.assertTrue(metadata['opening_workshop_included'])
        self.assertNotIn('pacing_verified', metadata)
        frozen=builder._asset_contract.validate_opening_bundle(self.work/'source/game_assets/opening',plan['openingAssets'])
        self.assertEqual(frozen,plan['openingAssets'])
        first=frozen['files'][0]['relative']; p=self.work/'source/game_assets/opening'/first; p.write_bytes(p.read_bytes()+b'!')
        with self.assertRaisesRegex(ValueError,'Frozen native source changed'): builder.validate_build(self.work)

    def test_opening_requires_declared_creator_module_closure(self):
        sdk=self.setup_opening(); builder.native_modules.return_value.remove('native_studio.game_engine.opening_project')
        with self.assertRaisesRegex(ValueError,'Missing required curated opening modules'): self.stage(include_player=True,native_sdk=sdk,opening_assets_root=self.opening)
        self.assertFalse(self.work.exists())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(OpeningReleaseBundleTests(name) for name in OpeningReleaseBundleTests.__dict__ if name.startswith('test_'))


if __name__=='__main__': unittest.main()
