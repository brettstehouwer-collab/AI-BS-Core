"""Static saved-play release admission; synthetic fixtures, no app/runtime."""
import ast,copy,hashlib,json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.tests import test_native_game_release as build_fixtures
from scripts.tests import test_native_creator_verification as verify_fixtures

builder=build_fixtures.builder
verifier=verify_fixtures.verifier
MODULES=frozenset('native_studio.game_engine.'+name for name in ('saved_play','saved_play_storage','saved_chapter_export'))
FLAGS=('durable_world','first_boot_chapter','first_boot_content_play','chapter_content_export_v2',
    'chapter_content_v3','chapter_asset_surfaces','mesh_asset_v1','character_asset_v2','audio_asset_v2',
    'chapter-memory-audio-v1','chapter-authored-inspections-v1','chapter-initial-view-v1',
    'chapter-workshop-commissioning-v1','chapter-saved-play-v1')
def caps():return {'schema_version':1,'sdk_version':'0.16.0','target':'windows-x64','features':dict.fromkeys(FLAGS,True)}

class SavedReleaseBuilder(unittest.TestCase):
    def setUp(self):
        self.case=build_fixtures.NativeGameReleaseTests('test_player_is_opt_in');self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root,self.work,self.release=self.case.root,self.case.work,self.case.release
        self.sdk=self.case.modern_sdk(complete=True)
        package=self.root/'native_studio/game_engine';package.mkdir()
        (package/'__init__.py').write_text('# synthetic package\n')
        for name in ('saved_play','saved_play_storage','saved_chapter_export'):
            (package/(name+'.py')).write_text('# synthetic '+name+'; no application execution\n')
        builder.native_modules.return_value += ['native_studio.game_engine',*sorted(MODULES)]
        self.cap=self.sdk/'bin/aibs_capabilities.json';self.write_caps(caps())
    def write_caps(self,value):self.cap.write_text(json.dumps(value))
    def stage(self,**kwargs):return self.case.stage(include_player=True,native_sdk=self.sdk,require_saved_play=True,**kwargs)
    def absent(self):self.assertFalse(self.work.exists());self.assertFalse(self.release.exists())
    def test_require_saved_play_requires_exact_include_player_before_writes(self):
        for value in (False,1,None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                builder.stage(self.work,self.release,include_player=value,native_sdk=self.sdk,require_saved_play=True)
            self.absent()
    def test_new_requirement_is_a_strict_boolean(self):
        for value in (1,None,'true'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                builder.stage(self.work,self.release,include_player=True,native_sdk=self.sdk,require_saved_play=value)
            self.absent()
    def test_invalid_or_old_sdk_rejects_before_stage(self):
        for version in ('0.15.9','0.16','00.16.0',True,None):
            value=caps();value['sdk_version']=version;self.write_caps(value)
            with self.subTest(version=version),self.assertRaises(ValueError):self.stage()
            self.absent()
    def test_false_missing_or_nonboolean_capability_rejects_before_stage(self):
        for key in FLAGS:
            value=caps();value['features'][key]=False;self.write_caps(value)
            with self.subTest(key=key),self.assertRaises(ValueError):self.stage()
            self.absent()
        for value in (1,None):
            data=caps();data['features']['chapter-saved-play-v1']=value;self.write_caps(data)
            with self.assertRaises(ValueError):self.stage()
            self.absent()
    def test_wrong_target_and_missing_flag_reject_before_stage(self):
        value=caps();value['target']='linux';self.write_caps(value)
        with self.assertRaises(ValueError):self.stage()
        self.absent();value=caps();del value['features']['chapter-saved-play-v1'];self.write_caps(value)
        with self.assertRaises(ValueError):self.stage()
        self.absent()
    def test_required_modules_must_be_declared_and_exist_before_stage(self):
        original=list(builder.native_modules.return_value)
        for module in MODULES:
            builder.native_modules.return_value=[m for m in original if m!=module]
            with self.subTest(module=module),self.assertRaises(ValueError):self.stage()
            self.absent()
        builder.native_modules.return_value=original
        (self.root/'native_studio/game_engine/saved_play.py').unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):self.stage()
        self.absent()
    def test_complete_runtime_assets_required_before_stage(self):
        (self.sdk/'bin/aibs_assetc.exe').unlink()
        with self.assertRaises(FileNotFoundError):self.stage()
        self.absent()
    def test_valid_profile_freezes_sources_and_truthful_metadata(self):
        plan=self.stage();metadata=json.loads((self.work/'source/game_release.json').read_text())
        self.assertIs(plan['requireSavedPlay'],True);self.assertIs(plan['savedChapterPlayIncluded'],True)
        self.assertIs(metadata['require_saved_play'],True);self.assertIs(metadata['saved_chapter_play_included'],True)
        self.assertFalse(plan['applicationExecuted']);self.assertNotIn('saved_play_verified',metadata)
        for module in MODULES:
            relative=module.replace('.','/')+'.py'
            self.assertEqual((self.work/'source'/relative).read_bytes(),(self.root/relative).read_bytes())
            self.assertIn(module,plan['modules'])
        self.assertEqual(builder.validate_build(self.work),plan);self.assertFalse(self.release.exists())
    def test_optional_complete016_inclusion_is_truthful_without_requirement(self):
        plan=builder.stage(self.work,self.release,include_player=True,native_sdk=self.sdk)
        self.assertIs(plan['requireSavedPlay'],False);self.assertIs(plan['savedChapterPlayIncluded'],True)
    def test_legacy_default_profile_remains_usable_without_saved_claim(self):
        self.write_caps({'schema_version':1,'sdk_version':'0.15.0','features':{'chapter_content_v3':True}})
        plan=builder.stage(self.work,self.release,include_player=True,native_sdk=self.sdk)
        self.assertIs(plan['requireSavedPlay'],False);self.assertIs(plan['savedChapterPlayIncluded'],False)
    def test_validate_build_rejects_rehashed_profile_flag_tampering(self):
        plan=self.stage();plan['requireSavedPlay']=False
        (self.work/'plan.json').write_text(json.dumps(plan))
        with patch.object(builder.subprocess,'run')as run,self.assertRaisesRegex(ValueError,'saved|Saved'):
            builder.validate_build(self.work)
        run.assert_not_called();self.assertFalse(self.release.exists())
    def test_copy_failure_preserves_existing_sources_and_never_publishes_plan_or_release(self):
        before=self.cap.read_bytes()
        with patch.object(builder.shutil,'copyfile',side_effect=OSError('synthetic freeze interruption')):
            with self.assertRaises(OSError):self.stage()
        self.assertFalse(self.release.exists());self.assertFalse((self.work/'plan.json').exists())
        self.assertEqual(self.cap.read_bytes(),before)
    def test_capabilities_changed_between_admission_and_freeze_never_publish_plan(self):
        original=builder.shutil.copyfile;changed=[]
        def copy(source,target):
            if not changed:
                value=caps();value['features']['chapter-saved-play-v1']=False
                self.write_caps(value);changed.append(True)
            return original(source,target)
        with patch.object(builder.shutil,'copyfile',side_effect=copy),self.assertRaisesRegex(ValueError,'capabilit|saved|Saved'):
            self.stage()
        self.assertFalse(self.release.exists());self.assertFalse((self.work/'plan.json').exists())
    def test_all_three_clients_are_explicit_normal_graph_dependencies(self):
        with patch.object(builder._graph,'native_modules',return_value=['native_studio','native_studio.app']):
            # The fixture patches the public graph function; inspect the
            # canonical function through the class's original module spec.
            import importlib.util
            spec=importlib.util.spec_from_file_location('saved_explicit_graph',build_fixtures.ROOT/'scripts/build_native_game_release.py')
            actual=importlib.util.module_from_spec(spec);spec.loader.exec_module(actual)
        self.assertTrue(MODULES<=actual.CREATOR_MODULES)

class SavedReleaseVerifier(unittest.TestCase):
    def setUp(self):
        self.case=verify_fixtures.CreatorVerificationTests('test_complete_fixture_passes_and_claims_only_static_scope')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        c=self.case;c.plan['modules']=list(c.plan['modules'])
        for module in sorted(MODULES):
            relative=module.replace('.','/')+'.py';content=b'def fixture():\n    return "saved client static fixture"\n'
            c.write_staged(relative,content);c.codes[module]=compile(content,relative,'exec');c.plan['modules'].append(module)
        for name in verifier.WARM_PLAYER_FILES:c.write_staged('game_assets/player/'+name,b'bounded SDK016 fixture',packaged=True)
        self.write_caps(caps())
        c.plan.update(requireSavedPlay=True,savedChapterPlayIncluded=True)
        c.metadata.update(require_saved_play=True,saved_chapter_play_included=True);c.update_metadata()
        self.collection()
    def collection(self):
        c=self.case;c.collection.write_text(repr(([((p.relative_to(c.package).as_posix().removeprefix('_internal/')),
            str(p),'EXECUTABLE'if p==c.exe else'DATA')for p in c.package.rglob('*')if p.is_file()],)))
    def write_caps(self,value):
        c=self.case;relative='game_assets/player/aibs_capabilities.json';data=json.dumps(value).encode()
        for root in (c.source,c.internal):(root/relative).write_bytes(data)
        next(row for row in c.rows if row['relative']==relative).update(bytes=len(data),sha256=verifier.digest(c.source/relative))
        c.write_plan()
    def verify(self):return verifier.verify_release(self.case.work)
    def test_complete_profile_verifies_static_presence_without_runtime_claim(self):
        r=self.verify();self.assertEqual(r['status'],'passed')
        self.assertIs(r['require_saved_play'],True);self.assertIs(r['saved_chapter_play_included'],True)
        self.assertFalse(r['application_executed']);self.assertIn('Static',r['scope'])
    def test_omitted_plan_or_metadata_flags_cannot_hide_complete016_feature(self):
        c=self.case
        for key in ('requireSavedPlay','savedChapterPlayIncluded'):
            value=c.plan.pop(key);c.write_plan()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'saved|Saved'):self.verify()
            c.plan[key]=value
        for key in ('require_saved_play','saved_chapter_play_included'):
            value=c.metadata.pop(key);c.update_metadata()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'saved|Saved|metadata'):self.verify()
            c.metadata[key]=value;c.update_metadata()
    def test_typed_profile_flags_are_checked_independently(self):
        c=self.case
        for key in ('requireSavedPlay','savedChapterPlayIncluded'):
            for value in (1,None,'true',False):
                original=c.plan[key];c.plan[key]=value;c.write_plan()
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.verify()
                c.plan[key]=original
        c.write_plan()
    def test_missing_saved_module_cannot_be_hidden_by_plan_omission(self):
        c=self.case
        for module in MODULES:
            c.plan['modules'].remove(module);c.write_plan()
            with self.subTest(module=module),self.assertRaisesRegex(ValueError,'saved|Saved|module'):self.verify()
            c.plan['modules'].append(module)
    def test_rehashed_native_caps_downgrade_cannot_keep_saved_claim(self):
        for key in FLAGS:
            data=caps();data['features'][key]=False;self.write_caps(data)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'saved|Saved|capabilit'):self.verify()
        self.write_caps(caps());self.assertEqual(self.verify()['status'],'passed')
    def test_omitting_all_new_flags_from_complete_profile_rejects(self):
        c=self.case
        for key in ('requireSavedPlay','savedChapterPlayIncluded'):del c.plan[key]
        for key in ('require_saved_play','saved_chapter_play_included'):del c.metadata[key]
        c.update_metadata()
        with self.assertRaisesRegex(ValueError,'saved|Saved'):self.verify()
    def test_changed_frozen_module_code_rejected(self):
        module='native_studio.game_engine.saved_play_storage';self.case.codes[module]=compile('raise ValueError("tampered")',module,'exec')
        with self.assertRaisesRegex(ValueError,'Frozen code differs'):self.verify()

if __name__=='__main__':unittest.main()
