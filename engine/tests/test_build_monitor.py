import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_studio.game_build_monitor import read_build_progress
import native_studio.game_build_monitor as monitor


class BuildMonitorTests(unittest.TestCase):
    def test_persistent_placement_evidence_is_bounded_independent_and_keeps_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(read_build_progress(root)['persistent_placement_verification'],{'status':'not_run','checks':[]})
            report=root/'engine/out/persistent_placement_verification.json';report.parent.mkdir(parents=True)
            fixture={'schema_version':1,'status':'passed','verified_at':'2026-11-02T01:00:00+00:00',
                'sdk_version':'0.10.0','studio_version':'5.329.97',
                'checks':['New native owner reopens immutable placement references'],
                'limitations':['Presentation-only; no mesh collider or texture/PBR editing'],
                'proof_paths':['engine/out/placement-ui/verification.json'],'metrics':{'debug_errors':0},
                'next_step':'Additional authoring tools remain planned','drive_checkpoint':'Retained milestones preserved'}
            report.write_text(json.dumps(fixture),encoding='utf-8')
            result=read_build_progress(root)
            actual=result['persistent_placement_verification']
            for key in ('status','verified_at','sdk_version','studio_version','checks','limitations','proof_paths','metrics','next_step','drive_checkpoint'):
                self.assertEqual(actual[key],fixture[key])
            self.assertEqual(result['asset_pipeline_verification']['status'],'not_run')
            for invalid in ({**fixture,'limitations':'none'}, {**fixture,'proof_paths':['']},
                    {**fixture,'verified_at':'2026-11-02T01:00:00'}, {**fixture,'schema_version':True},
                    {**fixture,'sdk_version':True}, {**fixture,'metrics':{'value':float('nan')}},
                    {**fixture,'checks':[]}):
                report.write_text(json.dumps(invalid),encoding='utf-8')
                self.assertEqual(read_build_progress(root)['persistent_placement_verification']['status'],'unreadable')
            report.write_bytes(b' '*(1024*1024+1))
            self.assertEqual(read_build_progress(root)['persistent_placement_verification']['status'],'unreadable')

    def test_asset_pipeline_uses_its_own_bounded_actual_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(read_build_progress(root)['asset_pipeline_verification'],
                             {'status': 'not_run', 'checks': []})
            report = root / 'engine/out/asset_pipeline_verification.json'
            report.parent.mkdir(parents=True)
            proof = {'schema_version': 1, 'status': 'passed',
                     'completed_at': '2026-11-01T23:50:00+00:00',
                     'checks': ['Cooked mesh and materials changed actual native GPU pixels'],
                     'metrics': {'triangles': 4788, 'materials': 8, 'debug_errors': 0}}
            report.write_text(json.dumps(proof), encoding='utf-8')
            actual = read_build_progress(root)['asset_pipeline_verification']
            self.assertEqual(actual['status'], 'passed')
            self.assertEqual(actual['metrics']['triangles'], 4788)
            report.write_text('{broken', encoding='utf-8')
            self.assertEqual(read_build_progress(root)['asset_pipeline_verification']['status'], 'unreadable')
            report.write_bytes(b' ' * (1024 * 1024 + 1))
            self.assertEqual(read_build_progress(root)['asset_pipeline_verification']['status'], 'unreadable')

    def test_live_ai_authoring_proof_is_bounded_and_independent_of_native_play(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(read_build_progress(root)['ai_authoring_verification'],
                {'status': 'not_run', 'checks': []})
            report = root / 'engine/out/ai_authoring_verification.json'
            report.parent.mkdir(parents=True)
            fixture = {'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-02T01:00:00+00:00',
                'checks': ['Actual installed-model response reaches native Preview without mutating the head',
                    'Explicit Apply, history, Save and reopen preserve the accepted field edit'],
                'metrics': {'selected_model': 'fixture:local', 'endpoint': 'http://127.0.0.1:11434',
                    'actual_model_runs': 1, 'python_tests': 152,
                    'limits': ['One live model verified', 'Exposed field edits only',
                        'Session metadata is not durable provenance']},
                'origin': 'Recorded selected local model and real native authoring proof'}
            report.write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)
            for field in ('status', 'checks', 'completed_at', 'metrics', 'origin'):
                self.assertEqual(actual['ai_authoring_verification'][field], fixture[field])
            for other in ('chapter_creator_verification', 'chapter_play_verification',
                    'first_boot_chapter_verification'):
                self.assertEqual(actual[other]['status'], 'not_run')
            for invalid in ('{broken', json.dumps({**fixture, 'metrics': []}),
                    json.dumps({**fixture, 'checks': []}),
                    json.dumps({**fixture, 'completed_at': '2026-11-02T01:00:00'}),
                    json.dumps({**fixture, 'metrics': {'seconds': float('nan')}}),
                    json.dumps(fixture) + ' ' * (1024 * 1024)):
                with self.subTest(invalid=invalid[:100]):
                    report.write_text(invalid, encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['ai_authoring_verification']['status'], 'unreadable')
            fixture['status'] = 'failed'
            report.write_text(json.dumps(fixture), encoding='utf-8')
            self.assertEqual(read_build_progress(root)['ai_authoring_verification']['status'], 'failed')

    def test_chapter_play_report_is_distinct_from_creator_and_campaign_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=read_build_progress(root)
            self.assertEqual(result['chapter_play_verification'],{'status':'not_run','checks':[]})
            report=root/'engine/out/chapter_play_verification.json';report.parent.mkdir(parents=True)
            fixture={'schema_version':1,'status':'passed','completed_at':'2026-11-02T00:30:00+00:00',
                'checks':['Pinned native AIBD export and GPU preview','Isolated native Play drains before scratch cleanup'],
                'metrics':{'native_play':True,'temporary_play':True,'debug_errors':0}}
            report.write_text(json.dumps(fixture),encoding='utf-8')
            result=read_build_progress(root)
            for key in ('status','checks','completed_at','metrics'):self.assertEqual(result['chapter_play_verification'][key],fixture[key])
            self.assertEqual(result['chapter_creator_verification']['status'],'not_run')
            self.assertEqual(result['first_boot_chapter_verification']['status'],'not_run')
            for bad in ('{broken',json.dumps({**fixture,'status':'running'}),json.dumps({**fixture,'checks':[]}),
                        json.dumps({**fixture,'metrics':[]}),json.dumps({**fixture,'completed_at':'2026-11-02T00:30:00'})):
                with self.subTest(bad=bad):
                    report.write_text(bad,encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['chapter_play_verification']['status'],'unreadable')
            fixture['status']='failed';report.write_text(json.dumps(fixture),encoding='utf-8')
            self.assertEqual(read_build_progress(root)['chapter_play_verification']['status'],'failed')

    def test_chapter_creator_proof_is_separate_bounded_and_preserves_named_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(read_build_progress(root)['chapter_creator_verification'],{'status':'not_run','checks':[]})
            report=root/'engine/out/chapter_creator_verification.json';report.parent.mkdir(parents=True)
            fixture={'schema_version':1,'status':'passed','completed_at':'2026-11-01T22:00:00+00:00',
                'checks':['Native typed endpoint and client','Qt chapter inspector and process close','Scoped proposal-job admission'],
                'metrics':{'widget_tests':5,'live_inference':False},'origin':'Recorded native endpoint and Qt authoring proof'}
            report.write_text(json.dumps(fixture),encoding='utf-8')
            result=read_build_progress(root)
            self.assertEqual(result['chapter_creator_verification']['status'],'passed')
            for key in ('checks','completed_at','metrics','origin'):self.assertEqual(result['chapter_creator_verification'][key],fixture[key])
            self.assertEqual(result['first_boot_chapter_verification']['status'],'not_run')
            self.assertEqual(result['content_authoring_verification']['status'],'not_run')
            fixture['status']='failed';fixture['metrics']['widget_tests']=0
            report.write_text(json.dumps(fixture),encoding='utf-8')
            self.assertEqual(read_build_progress(root)['chapter_creator_verification']['status'],'failed')
            invalid=['{broken',json.dumps([]),json.dumps({**fixture,'schema_version':True}),
                json.dumps({**fixture,'completed_at':'2026-11-01T22:00:00'}),json.dumps({**fixture,'checks':[]}),
                json.dumps({**fixture,'checks':['   ']}),json.dumps({**fixture,'metrics':[]}),
                json.dumps({**fixture,'metrics':{'seconds':float('nan')}}),
                json.dumps({**fixture,'checks':['x'*8193]}),json.dumps({**fixture,'checks':['x']*257}),
                json.dumps(fixture)+' '*(1024*1024)]
            for content in invalid:
                with self.subTest(content=content[:100]):
                    report.write_text(content,encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['chapter_creator_verification']['status'],'unreadable')

    def test_content_definition_evidence_is_independent_of_native_chapter_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(read_build_progress(root)['first_boot_content_verification']['status'],'not_run')
            path=root/'engine/out/first_boot_content_verification.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'schema_version':1,'status':'passed',
                'completed_at':'2026-11-01T20:00:00+00:00','checks':['Content-bound SQLite restart'],
                'origin':'SDK runtime verified; visual chapter authoring/native Play unfinished'}),encoding='utf-8')
            report=read_build_progress(root)
            self.assertEqual(report['first_boot_content_verification']['status'],'passed')
            self.assertEqual(report['first_boot_chapter_verification']['status'],'not_run')
            self.assertIn('visual chapter authoring',report['first_boot_content_verification']['origin'])
            malformed={'schema_version':1,'status':'passed','completed_at':'2026-11-01T20:00:00+00:00','checks':['Scope'], 'origin':{'unexpected':'object'}}
            path.write_text(json.dumps(malformed),encoding='utf-8')
            self.assertEqual(read_build_progress(root)['first_boot_content_verification']['status'],'unreadable')
            typed=path.with_name('content_authoring_verification.json')
            typed.write_text(json.dumps({'schema_version':1,'status':'passed','completed_at':'2026-11-01T20:00:00+00:00','checks':['Scoped proposal fixture'], 'origin':'Admission verified; no live model connection'}),encoding='utf-8')
            self.assertEqual(read_build_progress(root)['content_authoring_verification']['origin'],'Admission verified; no live model connection')
            path.write_text('{',encoding='utf-8')
            self.assertEqual(read_build_progress(root)['first_boot_content_verification']['status'],'unreadable')

    @staticmethod
    def chapter_proof_fixture():
        coverage = ('native_gpu', 'actual_player_pov', 'actual_hud_fits', 'repair_route', 'bypass_route',
                    'occupied_door_close', 'optional_help', 'optional_decline', 'depart_return',
                    'feed_build_dismantle', 'latched_unpowered_return', 'restart_pixels_identity',
                    'actual_f9_reload', 'hazard_pause', 'hazard_recovery', 'critical_backpressure',
                    'recovery_consumes_old_input', 'stale_activation_rejected', 'empty_socket_survives',
                    'remote_node_reach', 'translated_board_supported', 'reload_failure_retains_live',
                    'live_f5_held_contact', 'close_drains_held_contact', 'explicit_m2_upgrade',
                    'm2_history_preserved', 'original_import_preserved')
        return {'schema_version': 1, 'status': 'passed',
                'executablePath': 'C:/proof/Release/aibs_motherboard.exe', 'executableSha256': 'a1' * 32,
                'work_directory': 'C:/proof/chapter-run', 'completed_at': '2026-11-01T13:22:42.195016+00:00',
                'checks': ['Actual repair/bypass traversal and player-view/HUD pixels',
                           'Held contact save/reload and original imports preserve exact history'],
                'metrics': {**{key: True for key in coverage}, 'processes': 36,
                            'debug_layer': True, 'debug_errors': 0}}

    def test_native_chapter_proof_requires_recorded_report(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['first_boot_chapter_verification'],
                             {'status': 'not_run', 'checks': []})

    def test_native_chapter_proof_preserves_exact_identity_and_debug_layer_observation(self):
        fixture = self.chapter_proof_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/first_boot_chapter_verification.json'
            report.parent.mkdir(parents=True)
            for debug_layer in (True, False):
                current = {**fixture, 'metrics': {**fixture['metrics'], 'debug_layer': debug_layer}}
                report.write_text(json.dumps(current), encoding='utf-8')
                actual = read_build_progress(root)['first_boot_chapter_verification']
                for field in fixture:
                    self.assertEqual(actual[field], current[field])
                self.assertEqual(actual['source_path'], str(report))
                self.assertEqual(read_build_progress(root)['durable_world_verification']['status'], 'not_run')
                self.assertEqual(read_build_progress(root)['registry_migration_verification']['status'], 'not_run')

    def test_native_chapter_proof_rejects_false_missing_or_malformed_pass(self):
        fixture = self.chapter_proof_fixture()
        invalid = ['{broken', json.dumps([]), json.dumps({**fixture, 'schema_version': True}),
                   json.dumps({**fixture, 'schema_version': 2}), json.dumps({**fixture, 'status': 'running'}),
                   json.dumps({**fixture, 'checks': []}), json.dumps({**fixture, 'metrics': []}),
                   json.dumps({**fixture, 'completed_at': '2026-11-01T13:22:42'}),
                   json.dumps({**fixture, 'error': 'Cannot pass with this error'})]
        for field in ('executablePath', 'executableSha256', 'work_directory'):
            invalid.append(json.dumps({k: v for k, v in fixture.items() if k != field}))
            for bad in ('', False, []):
                invalid.append(json.dumps({**fixture, field: bad}))
        invalid.extend(json.dumps({**fixture, 'executableSha256': value}) for value in ('a' * 63, 'g' * 64))
        for key, value in fixture['metrics'].items():
            if type(value) is bool and key != 'debug_layer':
                for bad in (False, 1, 'true'):
                    invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: bad}}))
                invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != key}}))
        for key, bad in (('processes', 35), ('processes', True), ('processes', '36'),
                         ('debug_errors', 1), ('debug_errors', -1), ('debug_errors', True),
                         ('debug_layer', 1), ('debug_layer', 'false')):
            invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: bad}}))
        for key in ('processes', 'debug_errors', 'debug_layer'):
            invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != key}}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/first_boot_chapter_verification.json'
            report.parent.mkdir(parents=True)
            for content in invalid:
                with self.subTest(content=content[:200]):
                    report.write_text(content, encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['first_boot_chapter_verification']['status'], 'unreadable')

    def test_native_chapter_proof_preserves_failed_run_and_partial_diagnostics(self):
        fixture = self.chapter_proof_fixture()
        fixture.update(status='failed', error='Held contact failed to drain',
                       metrics={'close_drains_held_contact': False, 'processes': 8, 'debug_errors': 1, 'debug_layer': False})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/first_boot_chapter_verification.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['first_boot_chapter_verification']
            self.assertEqual(actual['status'], 'failed')
            self.assertEqual(actual['error'], fixture['error'])
            self.assertEqual(actual['metrics'], fixture['metrics'])
            fixture['metrics']['close_drains_held_contact'] = 'false'
            report.write_text(json.dumps(fixture), encoding='utf-8')
            self.assertEqual(read_build_progress(root)['first_boot_chapter_verification']['status'], 'unreadable')

    def test_native_chapter_capability_requires_existing_executable_and_adjacent_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'aibs_motherboard.exe'
            descriptor = binary.with_name('aibs_capabilities.json')
            self.assertFalse(monitor.read_native_player_capabilities(binary)['chapter_capable'])
            descriptor.write_text(json.dumps({'schema_version': 1, 'sdk_version': '0.8.0',
                                              'features': {'first_boot_chapter': True}}), encoding='utf-8')
            self.assertFalse(monitor.read_native_player_capabilities(binary)['chapter_capable'])
            binary.write_bytes(b'fixture-not-executed')
            actual = monitor.read_native_player_capabilities(binary)
            self.assertEqual(actual['status'], 'available')
            self.assertEqual(actual['sdk_version'], '0.8.0')
            self.assertTrue(actual['chapter_capable'])
            descriptor.unlink()
            self.assertFalse(monitor.read_native_player_capabilities(binary)['chapter_capable'])

    def test_native_chapter_capability_version_and_feature_are_strict(self):
        fixture = {'schema_version': 1, 'sdk_version': '0.8.0', 'features': {'first_boot_chapter': True}}
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'aibs_motherboard.exe'
            binary.write_bytes(b'fixture-not-executed')
            descriptor = binary.with_name('aibs_capabilities.json')
            for version in ('0.8.0', '0.9.0', '0.10.0', '1.0.0'):
                descriptor.write_text(json.dumps({**fixture, 'sdk_version': version}), encoding='utf-8')
                self.assertTrue(monitor.read_native_player_capabilities(binary)['chapter_capable'])
            for version in ('0.7.0', '0.7.99'):
                descriptor.write_text(json.dumps({**fixture, 'sdk_version': version}), encoding='utf-8')
                self.assertFalse(monitor.read_native_player_capabilities(binary)['chapter_capable'])
            for features in ({}, {'first_boot_chapter': False}):
                descriptor.write_text(json.dumps({**fixture, 'features': features}), encoding='utf-8')
                actual = monitor.read_native_player_capabilities(binary)
                self.assertEqual(actual['status'], 'available')
                self.assertFalse(actual['chapter_capable'])
            invalid = ['{broken', '[]', 'x' * (16 * 1024 + 1)]
            for field, bad in (('schema_version', True), ('schema_version', 2), ('sdk_version', True),
                               ('sdk_version', '0.8'), ('sdk_version', '00.8.0'), ('features', []),
                               ('features', {'first_boot_chapter': 1}),
                               ('features', {'first_boot_chapter': 'true'})):
                invalid.append(json.dumps({**fixture, field: bad}))
            for content in invalid:
                with self.subTest(content=content[:100]):
                    descriptor.write_text(content, encoding='utf-8')
                    actual = monitor.read_native_player_capabilities(binary)
                    self.assertEqual(actual['status'], 'unreadable')
                    self.assertFalse(actual['chapter_capable'])

    @staticmethod
    def registry_migration_fixture():
        return {'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-01T12:23:44.210688+00:00',
                'checks': ['Actual before/after COMMIT exits preserve original M2 evidence'],
                'scope': {'project_id': 'registry-proof', 'world_id': 'registry-world',
                          'branch_id': 'main', 'timeline_id': 'registry-timeline', 'context': 'player_world'},
                'revision': 3, 'original_checkpoint_id': 'original-checkpoint',
                'work_directory': 'C:/proof/registry',
                'metrics': {**{key: True for key in (
                    'before_commit_recovery', 'after_commit_recovery', 'atomic_registry_receipts',
                    'preserved_m2_evidence', 'exact_migration_retry', 'conflicting_migration_rejected',
                    'stale_registry_connection')}, 'processes': 10, 'old_studio92_rejected': True}}

    def test_registry_migration_requires_recorded_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['registry_migration_verification'],
                             {'status': 'not_run', 'checks': []})

    def test_registry_migration_preserves_scope_and_optional_compatibility_observation(self):
        fixture = self.registry_migration_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/registry_migration_verification.json'
            report.parent.mkdir(parents=True)
            for observation in (True, False, None):
                with self.subTest(observation=observation):
                    metrics = dict(fixture['metrics'])
                    if observation is None:
                        del metrics['old_studio92_rejected']
                    else:
                        metrics['old_studio92_rejected'] = observation
                    current = {**fixture, 'metrics': metrics}
                    report.write_text(json.dumps(current), encoding='utf-8')
                    actual = read_build_progress(root)['registry_migration_verification']
                    for field in ('status', 'checks', 'completed_at', 'scope', 'revision',
                                  'original_checkpoint_id', 'work_directory', 'metrics'):
                        self.assertEqual(actual[field], current[field])
                    self.assertEqual(actual['source_path'], str(report))
                    self.assertEqual(read_build_progress(root)['durable_world_verification']['status'], 'not_run')

    def test_registry_migration_rejects_missing_false_or_malformed_pass_coverage(self):
        fixture = self.registry_migration_fixture()
        invalid = ['{broken', json.dumps([]), json.dumps({**fixture, 'schema_version': True}),
                   json.dumps({**fixture, 'schema_version': 2}), json.dumps({**fixture, 'checks': []}),
                   json.dumps({**fixture, 'status': 'running'}),
                   json.dumps({**fixture, 'completed_at': '2026-11-01T12:23:44'}),
                   json.dumps({**fixture, 'revision': True}), json.dumps({**fixture, 'revision': 2**64}),
                   json.dumps({**fixture, 'scope': []}), json.dumps({**fixture, 'metrics': []}),
                   json.dumps({**fixture, 'error': 'Contradicts passed status'}),
                   json.dumps({**fixture, 'original_checkpoint_id': []})]
        for key in fixture['metrics']:
            if key in ('processes', 'old_studio92_rejected'):
                continue
            for bad in (False, 1, 'true'):
                invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: bad}}))
            invalid.append(json.dumps({**fixture, 'metrics': {
                k: v for k, v in fixture['metrics'].items() if k != key}}))
        for key, bad in (('old_studio92_rejected', 1), ('old_studio92_rejected', 'true'),
                         ('processes', True), ('processes', -1), ('processes', 0)):
            invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: bad}}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/registry_migration_verification.json'
            report.parent.mkdir(parents=True)
            for content in invalid:
                with self.subTest(content=content):
                    report.write_text(content, encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['registry_migration_verification']['status'], 'unreadable')

    def test_registry_migration_preserves_failed_evidence_without_claiming_pass(self):
        fixture = self.registry_migration_fixture()
        fixture.update(status='failed', error='Stale registry connection unexpectedly wrote')
        fixture['metrics'] = {'stale_registry_connection': False, 'old_studio92_rejected': False}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/registry_migration_verification.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['registry_migration_verification']
            self.assertEqual(actual['status'], 'failed')
            self.assertEqual(actual['error'], fixture['error'])
            self.assertEqual(actual['metrics'], fixture['metrics'])
            fixture['metrics']['stale_registry_connection'] = 'false'
            report.write_text(json.dumps(fixture), encoding='utf-8')
            self.assertEqual(read_build_progress(root)['registry_migration_verification']['status'], 'unreadable')

    @staticmethod
    def durable_world_fixture():
        return {'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-01T19:00:00+00:00',
                'checks': ['Native input and GPU restart pixels match', 'Real failure retry and close drain'],
                'scope': {'project_id': 'first-boot-world', 'world_id': 'native-world',
                          'branch_id': 'main', 'timeline_id': 'native-timeline', 'context': 'player_world'},
                'revision': 3, 'durable_events': 3,
                'metrics': {**{key: True for key in (
                    'native_gpu', 'repair_build_dismantle', 'restart_pixels_identical', 'stable_uuids',
                    'semantic_event_equality', 'tombstone_persistence', 'before_commit_recovery',
                    'after_commit_recovery', 'exact_retry', 'live_retry', 'close_drained',
                    'import_preserves_original')}, 'processes': 23, 'debug_layer': True, 'debug_errors': 0}}

    def test_durable_world_requires_recorded_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['durable_world_verification'],
                             {'status': 'not_run', 'checks': []})

    def test_durable_world_preserves_actual_native_evidence(self):
        fixture = self.durable_world_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/durable_world_verification.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['durable_world_verification']
            for field in ('status', 'checks', 'completed_at', 'scope', 'revision', 'durable_events', 'metrics'):
                self.assertEqual(actual[field], fixture[field])

    def test_durable_world_rejects_missing_or_contradictory_pass_coverage(self):
        fixture = self.durable_world_fixture()
        invalid = ['{broken', json.dumps({**fixture, 'schema_version': True}),
                   json.dumps({**fixture, 'schema_version': 2}), json.dumps({**fixture, 'checks': []}),
                   json.dumps({**fixture, 'status': 'running'}),
                   json.dumps({**fixture, 'completed_at': '2026-11-01T19:00:00'}),
                   json.dumps({**fixture, 'revision': True}), json.dumps({**fixture, 'revision': 2**64}),
                   json.dumps({**fixture, 'durable_events': -1}), json.dumps({**fixture, 'scope': []}),
                   json.dumps({**fixture, 'scope': {**fixture['scope'], 'timeline_id': ''}}),
                   json.dumps({**fixture, 'metrics': []})]
        for key, value in fixture['metrics'].items():
            if type(value) is bool and key != 'debug_layer':
                for contradictory in (False, 1, 'true'):
                    invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: contradictory}}))
                invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != key}}))
        for bad_errors in (1, -1, True, '0'):
            invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], 'debug_errors': bad_errors}}))
        invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != 'debug_errors'}}))
        invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], 'processes': True}}))
        invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], 'debug_layer': 'true'}}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/durable_world_verification.json'
            report.parent.mkdir(parents=True)
            for content in invalid:
                with self.subTest(content=content):
                    report.write_text(content, encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['durable_world_verification']['status'], 'unreadable')

    def test_durable_world_preserves_real_failed_run_and_diagnostics(self):
        fixture = self.durable_world_fixture()
        failed = {**fixture, 'status': 'failed', 'checks': ['FAILED: native restart pixel mismatch'],
                  'error': 'native restart pixel mismatch',
                  'metrics': {**fixture['metrics'], 'restart_pixels_identical': False, 'debug_errors': 2}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/durable_world_verification.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(failed), encoding='utf-8')
            actual = read_build_progress(root)['durable_world_verification']
            self.assertEqual(actual['status'], 'failed')
            self.assertEqual(actual['checks'], failed['checks'])
            self.assertEqual(actual['error'], failed['error'])
            self.assertFalse(actual['metrics']['restart_pixels_identical'])
            self.assertEqual(actual['metrics']['debug_errors'], 2)

    def test_durable_world_failed_metadata_still_requires_valid_types(self):
        fixture = self.durable_world_fixture()
        invalid = [
            {**fixture, 'error': 'Fatal proof failure contradicts a passed status'},
            {**fixture, 'status': 'failed', 'metrics': None},
            {**fixture, 'status': 'failed', 'metrics': {**fixture['metrics'], 'debug_errors': None}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'engine/out/durable_world_verification.json'
            report.parent.mkdir(parents=True)
            for data in invalid:
                with self.subTest(data=data):
                    report.write_text(json.dumps(data), encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['durable_world_verification']['status'], 'unreadable')

    @staticmethod
    def gameplay_store_fixture():
        return {'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-01T16:00:00+00:00',
                'checks': ['Actual process exits before and after SQLite COMMIT'],
                'world_id': 'store-fixture-world', 'revision': 2,
                'metrics': {**{key: True for key in ('process_recovery', 'atomic_components_events',
                    'exact_retry', 'stale_writer', 'scope_isolation')}, 'durable_events': 2}}

    def test_gameplay_store_requires_recorded_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['gameplay_store_verification'],
                             {'status': 'not_run', 'checks': []})

    def test_gameplay_store_preserves_process_evidence_and_rejects_false_passes(self):
        fixture = self.gameplay_store_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            output.mkdir(parents=True)
            report = output / 'gameplay_store_verification.json'
            report.write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['gameplay_store_verification']
            for field in ('status', 'completed_at', 'checks', 'world_id', 'revision', 'metrics'):
                self.assertEqual(actual[field], fixture[field])
            invalid = ['{broken', json.dumps({**fixture, 'revision': True}),
                       json.dumps({**fixture, 'revision': 2**64}),
                       json.dumps({**fixture, 'completed_at': '2026-11-01T16:00:00'}),
                       json.dumps({**fixture, 'metrics': {**fixture['metrics'], 'durable_events': -1}})]
            for key in ('process_recovery', 'atomic_components_events', 'exact_retry', 'stale_writer', 'scope_isolation'):
                for value in (False, 1, 'true'):
                    invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: value}}))
                invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != key}}))
            for content in invalid:
                with self.subTest(content=content):
                    report.write_text(content, encoding='utf-8')
                    self.assertEqual(read_build_progress(root)['gameplay_store_verification']['status'], 'unreadable')
            failed = {**fixture, 'status': 'failed', 'metrics': {**fixture['metrics'], 'process_recovery': False}}
            report.write_text(json.dumps(failed), encoding='utf-8')
            actual = read_build_progress(root)['gameplay_store_verification']
            self.assertEqual(actual['status'], 'failed')
            self.assertFalse(actual['metrics']['process_recovery'])

    @staticmethod
    def obstacle_fixture():
        return {'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-01T16:00:00+00:00',
                'checks': ['Native GPU course covers traversal, focus and restart'],
                'adapter': 'Fixture GPU', 'world_id': 'fixture-world', 'checkpoint_id': 'fixture-checkpoint',
                'metrics': {'steps': True, 'slopes': True, 'walls': True, 'falls': True,
                            'focus': True, 'restart': True, 'interaction': True,
                            'walkable_slope_degrees': 20, 'steep_slope_degrees': 60, 'debug_errors': 0}}

    def test_obstacle_course_is_unverified_until_evidence_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['obstacle_course_verification'],
                             {'status': 'not_run', 'checks': []})

    def test_obstacle_course_preserves_successful_traversal_and_restart_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            output.mkdir(parents=True)
            fixture = self.obstacle_fixture()
            (output / 'obstacle_course_verification.json').write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['obstacle_course_verification']
            for field in ('status', 'completed_at', 'checks', 'adapter', 'world_id', 'checkpoint_id', 'metrics'):
                self.assertEqual(actual[field], fixture[field])

    def test_obstacle_course_rejects_incomplete_or_contradictory_pass_claims(self):
        fixture = self.obstacle_fixture()
        invalid = ['{broken', json.dumps({**fixture, 'metrics': []}),
                   json.dumps({**fixture, 'completed_at': '2026-11-01T16:00:00'}),
                   json.dumps({**fixture, 'world_id': []}),
                   json.dumps({**fixture, 'metrics': {**fixture['metrics'], 'debug_errors': 1}})]
        for key in ('steps', 'slopes', 'walls', 'falls', 'focus', 'restart', 'interaction'):
            for bad_value in (False, 1, 'true'):
                invalid.append(json.dumps({**fixture, 'metrics': {**fixture['metrics'], key: bad_value}}))
            invalid.append(json.dumps({**fixture, 'metrics': {k: v for k, v in fixture['metrics'].items() if k != key}}))
        without_metrics = dict(fixture)
        without_metrics.pop('metrics')
        invalid.append(json.dumps(without_metrics))
        for content in invalid:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / 'engine/out'
                output.mkdir(parents=True)
                (output / 'obstacle_course_verification.json').write_text(content, encoding='utf-8')
                actual = read_build_progress(root)
                self.assertEqual(actual['obstacle_course_verification']['status'], 'unreadable')
                self.assertEqual(actual['movement_verification']['status'], 'not_run')

    def test_obstacle_course_failure_keeps_named_checks_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            output.mkdir(parents=True)
            fixture = self.obstacle_fixture()
            fixture['status'] = 'failed'
            fixture['metrics']['restart'] = False
            (output / 'obstacle_course_verification.json').write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['obstacle_course_verification']
            self.assertEqual(actual['status'], 'failed')
            self.assertFalse(actual['metrics']['restart'])

    @staticmethod
    def queue_fixture():
        return {'schema_version': 1, 'updated_at': '2026-11-01T12:00:00+00:00',
                'current_milestone': 'M1',
                'milestones': [
                    {'id': 'M0', 'title': 'Baseline', 'status': 'complete', 'gates': [
                        {'id': 'M0-G01', 'status': 'VERIFIED', 'description': 'Baseline recorded', 'evidence': ['engine/BUILD_STATUS.md']}]},
                    {'id': 'M1', 'title': 'Grounded movement', 'status': 'in_progress', 'gates': [
                        {'id': 'M1-G01', 'status': 'UNVERIFIED', 'description': 'Capsule course', 'evidence': []}]}],
                'next_slices': [
                    {'id': 'S1', 'title': 'Movement', 'milestone': 'M1', 'status': 'in_progress'},
                    {'id': 'S2', 'title': 'World durability', 'milestone': 'M1', 'status': 'planned'},
                    {'id': 'S3', 'title': 'Power fault', 'milestone': 'M1', 'status': 'planned'}]}

    def test_missing_queue_does_not_imply_planned_work_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_build_progress(Path(directory))['milestone_queue']['status'], 'not_found')

    def test_queue_preserves_declared_status_and_gate_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'engine').mkdir()
            fixture = self.queue_fixture()
            (root / 'engine/milestone_queue.json').write_text(json.dumps(fixture), encoding='utf-8')
            actual = read_build_progress(root)['milestone_queue']
            self.assertEqual(actual['status'], 'loaded')
            for field in ('current_milestone', 'milestones', 'next_slices', 'updated_at'):
                self.assertEqual(actual[field], fixture[field])
            self.assertIn('engine/milestone_queue.json', [f['path'] for f in read_build_progress(root)['recent_files']])

    def test_invalid_queue_is_reported_without_losing_other_monitor_data(self):
        invalid = ['{broken', json.dumps({**self.queue_fixture(), 'current_milestone': 'M99'}),
                   json.dumps({**self.queue_fixture(), 'updated_at': '2026-11-01T12:00:00'}),
                   json.dumps({**self.queue_fixture(), 'next_slices': [{'id': 'S1', 'title': 'Wrong', 'milestone': 'M99', 'status': 'planned'}]}),
                   json.dumps({**self.queue_fixture(), 'milestones': [{'id': 'M1', 'title': 'Bad state', 'status': 'verified'}]})]
        for content in invalid:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'engine').mkdir()
                (root / 'engine/milestone_queue.json').write_text(content, encoding='utf-8')
                actual = read_build_progress(root)
                self.assertEqual(actual['milestone_queue']['status'], 'unreadable')
                self.assertEqual(actual['movement_verification']['status'], 'not_run')

    def test_missing_movement_evidence_is_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            actual = read_build_progress(Path(directory))['movement_verification']
            self.assertEqual(actual, {'status': 'not_run', 'checks': []})

    def test_movement_evidence_preserves_physics_and_measured_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            output.mkdir(parents=True)
            evidence = {
                'schema_version': 1, 'status': 'passed',
                'completed_at': '2026-11-01T11:00:00+00:00',
                'checks': ['Capsule stops at wall', 'Focus loss clears held movement'],
                'engine': 'Jolt', 'engine_version': 'fixture', 'fixed_hz': 60,
                'metrics': {'steps': 120, 'grounded': True}
            }
            (output / 'movement_verification.json').write_text(json.dumps(evidence), encoding='utf-8')
            actual = read_build_progress(root)['movement_verification']
            for field in ('status', 'checks', 'completed_at', 'engine', 'engine_version', 'fixed_hz', 'metrics'):
                self.assertEqual(actual[field], evidence[field])

    def test_invalid_movement_evidence_cannot_claim_success(self):
        base = {'schema_version': 1, 'status': 'passed', 'checks': ['Collision check'],
                'completed_at': '2026-11-01T11:00:00+00:00'}
        invalid = ['{broken', json.dumps({**base, 'fixed_hz': 0}),
                   json.dumps({**base, 'fixed_hz': True}), json.dumps({**base, 'metrics': []}),
                   json.dumps({**base, 'engine': []}), json.dumps({**base, 'checks': []}),
                   json.dumps({**base, 'completed_at': '2026-11-01T11:00:00'})]
        for content in invalid:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / 'engine/out'
                output.mkdir(parents=True)
                (output / 'movement_verification.json').write_text(content, encoding='utf-8')
                self.assertEqual(read_build_progress(root)['movement_verification']['status'], 'unreadable')

    def test_world_scene_evidence_is_missing_until_a_real_report_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_build_progress(Path(directory))
            self.assertEqual(status['world_scene_verification'], {'status': 'not_run', 'checks': []})

    def test_world_scene_evidence_preserves_identity_and_revision_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            output.mkdir(parents=True)
            evidence = {
                'schema_version': 1, 'status': 'passed',
                'checks': ['Repaired world renders differently', 'Reload preserves identities'],
                'completed_at': '2026-11-01T07:30:00+00:00',
                'world_id': 'fixture-world-id', 'checkpoint_id': 'fixture-checkpoint-id',
                'revision': 4, 'restored_revision': 4, 'entity_count': 12,
                'object_count': 31, 'memory_events': 4,
                'entity_ids': ['fixture-core-id', 'fixture-relay-id'],
                'adapter': 'Fixture GPU', 'metrics': {'changed_pixels': 123}
            }
            (output / 'world_scene_verification.json').write_text(json.dumps(evidence), encoding='utf-8')
            actual = read_build_progress(root)['world_scene_verification']
            for field in ('status', 'checks', 'world_id', 'checkpoint_id', 'revision', 'restored_revision',
                          'entity_count', 'object_count', 'memory_events', 'entity_ids', 'adapter', 'metrics'):
                self.assertEqual(actual[field], evidence[field])

    def test_invalid_world_scene_evidence_is_unreadable(self):
        invalid = [
            '{bad',
            json.dumps({'schema_version': 1, 'status': 'passed', 'checks': [], 'completed_at': '2026-11-01T07:30:00+00:00'}),
            json.dumps({'schema_version': 1, 'status': 'passed', 'checks': ['draw'], 'completed_at': '2026-11-01T07:30:00'}),
            json.dumps({'schema_version': 1, 'status': 'passed', 'checks': ['draw'], 'completed_at': '2026-11-01T07:30:00+00:00', 'revision': -1}),
        ]
        for text in invalid:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / 'engine/out'
                output.mkdir(parents=True)
                (output / 'world_scene_verification.json').write_text(text, encoding='utf-8')
                self.assertEqual(read_build_progress(root)['world_scene_verification']['status'], 'unreadable')

    def test_game_module_sources_are_tracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'engine/games'
            source.mkdir(parents=True)
            (source / 'first_boot.cpp').write_text('// fixture game module', encoding='utf-8')
            self.assertEqual(read_build_progress(root)['recent_files'][0]['path'], 'engine/games/first_boot.cpp')

    def test_missing_renderer_and_hosting_evidence_is_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_build_progress(Path(directory))
            self.assertEqual(status['renderer_verification']['status'], 'not_run')
            self.assertEqual(status['hosting_verification']['status'], 'not_run')

    def test_renderer_and_hosting_evidence_are_read_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            (output / 'site-verification').mkdir(parents=True)
            (output / 'renderer_verification.json').write_text(json.dumps({
                'schema_version': 1, 'status': 'passed', 'checks': ['draw and resize'],
                'completed_at': '2026-11-01T06:00:00+00:00',
                'adapter': {'description': 'Test adapter', 'software': False}
            }), encoding='utf-8')
            (output / 'site-verification/hosting_verification.json').write_text(json.dumps({
                'schema_version': 1, 'status': 'passed', 'checks': ['HTTP assets verified'],
                'origin': 'https://example.test', 'version': 'fixture',
                'verified_at': '2026-11-01T06:00:00+00:00'
            }), encoding='utf-8')
            status = read_build_progress(root)
            self.assertEqual(status['renderer_verification']['adapter']['description'], 'Test adapter')
            self.assertEqual(status['hosting_verification']['origin'], 'https://example.test')
            (output / 'renderer_verification.json').write_text('{bad', encoding='utf-8')
            (output / 'site-verification/hosting_verification.json').write_text('{bad', encoding='utf-8')
            status = read_build_progress(root)
            self.assertEqual(status['renderer_verification']['status'], 'unreadable')
            self.assertEqual(status['hosting_verification']['status'], 'unreadable')

    def test_missing_report_never_claims_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_build_progress(Path(directory))
            self.assertEqual(status['status'], 'not_run')

    def test_report_and_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'engine/out').mkdir(parents=True)
            (root / 'engine/src').mkdir()
            (root / 'engine/src/core.cpp').write_text('// change', encoding='utf-8')
            (root / 'engine/out/build_progress.json').write_text(json.dumps({
                'schema_version': 1, 'status': 'passed', 'configuration': 'Debug',
                'completed_at': '2000-01-01T00:00:00+00:00', 'events': []
            }), encoding='utf-8')
            status = read_build_progress(root)
            self.assertEqual(status['status'], 'passed')
            self.assertTrue(status['source_changed_since_build'])
            self.assertEqual(status['recent_files'][0]['path'], 'engine/src/core.cpp')

    def test_invalid_report_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'engine/out').mkdir(parents=True)
            (root / 'engine/out/build_progress.json').write_text('{bad', encoding='utf-8')
            self.assertEqual(read_build_progress(root)['status'], 'unreadable')

    def test_absent_checkpoint_evidence_never_claims_success(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_build_progress(Path(directory))
            self.assertEqual(status['checkpoint_verification']['status'], 'not_run')
            self.assertEqual(status['checkpoints'], [])

    def test_browser_concept_sources_are_visible_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'docs/game_engine/concept_playground'
            source.mkdir(parents=True)
            (source / 'first_boot_playground.html').write_text('<!DOCTYPE html>', encoding='utf-8')
            (source / 'extra.js').write_text('// concept fixture', encoding='utf-8')
            status = read_build_progress(root)
            self.assertEqual({entry['path'] for entry in status['recent_files']}, {
                'docs/game_engine/concept_playground/first_boot_playground.html',
                'docs/game_engine/concept_playground/extra.js'
            })

    def test_checkpoint_evidence_and_artifact_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'engine/out'
            checkpoints = output / 'checkpoints'
            checkpoints.mkdir(parents=True)
            checkpoint = checkpoints / 'first-boot.aibs'
            checkpoint.write_bytes(b'checkpoint-test-bytes')
            (output / 'outside.aibs').write_bytes(b'not-a-listed-checkpoint')
            evidence = {
                'schema_version': 1, 'status': 'passed',
                'checks': ['separate-process-restart', 'interrupted-save'],
                'completed_at': '2026-11-01T06:00:00+00:00'
            }
            (output / 'checkpoint_verification.json').write_text(json.dumps(evidence), encoding='utf-8')
            status = read_build_progress(root)
            self.assertEqual(status['checkpoint_verification']['status'], 'passed')
            self.assertEqual(status['checkpoint_verification']['checks'], evidence['checks'])
            self.assertEqual(len(status['checkpoints']), 1)
            self.assertEqual(status['checkpoints'][0]['path'], 'engine/out/checkpoints/first-boot.aibs')
            self.assertEqual(status['checkpoints'][0]['bytes'], checkpoint.stat().st_size)
            self.assertEqual(status['tracked_file_count'], 0)

    def test_invalid_checkpoint_evidence_is_unreadable(self):
        for evidence in ('{bad', json.dumps({'schema_version': 1, 'status': 'passed', 'checks': []}),
                         json.dumps({'schema_version': 2, 'status': 'passed', 'checks': ['restart'], 'completed_at': 'now'})):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / 'engine/out'
                output.mkdir(parents=True)
                (output / 'checkpoint_verification.json').write_text(evidence, encoding='utf-8')
                self.assertEqual(read_build_progress(root)['checkpoint_verification']['status'], 'unreadable')

    def test_storage_metrics_and_checkpoint_list_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoints = root / 'engine/out/checkpoints'
            install = root / 'engine/install'
            checkpoints.mkdir(parents=True)
            install.mkdir()
            for index in range(25):
                (checkpoints / f'{index:02}.aibs').write_bytes(b'123')
            (install / 'sdk.lib').write_bytes(b'1234567')
            status = read_build_progress(root)
            self.assertEqual(len(status['checkpoints']), 20)
            self.assertEqual(status['engine_storage']['generated']['bytes'], 75)
            self.assertEqual(status['engine_storage']['installed']['bytes'], 7)
            self.assertFalse(status['engine_storage']['generated']['partial'])


class BuildFreshnessTests(unittest.TestCase):
    def fixture(self, root, files):
        output = root / 'engine/out'
        output.mkdir(parents=True)
        (output / 'build_progress.json').write_text(json.dumps({
            'schema_version': 1, 'status': 'passed', 'events': [],
            'completed_at': '2001-01-01T00:00:00+00:00'}), encoding='utf-8')
        for relative, updated in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture', encoding='utf-8')
            os.utime(path, (updated, updated))

    def test_documentation_changes_do_not_invalidate_runtime_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, {'engine/src/core.cpp': 946684800,
                'engine/BUILD_STATUS.md': 1009843200,
                'docs/game_engine/AI_BS_GAME_ARCHITECTURAL_BUILDER_LEDGER.md': 1009843200,
                'docs/game_engine/checkpoints/checkpoint/source_manifest.json': 1009843200,
                'engine/milestone_queue.json': 1009843200})
            status = read_build_progress(root)
            self.assertFalse(status['source_changed_since_build'])
            self.assertTrue(status['documentation_changed_since_build'])
            self.assertEqual(status['source_freshness']['status'], 'current')
            self.assertEqual(status['documentation_freshness']['status'], 'changed')

    def test_runtime_include_shader_and_asset_inputs_invalidate_build(self):
        for relative in ('engine/src/render_textures.inl', 'engine/shaders/textured.hlsl',
                'engine/assets/cooked/pack/LICENSE.txt', 'engine/assets/part.png',
                'engine/tools/workshop/connection.py', 'native_studio/game_engine/content_view.py'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, {relative: 1009843200})
                status = read_build_progress(root)
                self.assertTrue(status['source_changed_since_build'])
                self.assertEqual(status['source_freshness']['status'], 'changed')
                self.assertEqual(status['recent_runtime_files'][0]['path'], relative)
                self.assertFalse(status['documentation_changed_since_build'])

    def test_unknown_inputs_are_conservatively_runtime_relevant(self):
        for relative in ('engine/src/new_input.custom', 'docs/game_engine/new_runtime_contract.json'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, {relative: 1009843200})
                status = read_build_progress(root)
                self.assertTrue(status['source_changed_since_build'])
                self.assertEqual(status['recent_runtime_files'][0]['kind'], 'unknown_input')

    def test_incomplete_scan_never_claims_current_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, {'engine/src/core.cpp': 946684800})
            scan = monitor.os.scandir
            def blocked(path):
                if Path(path) == root / 'engine/src':
                    raise PermissionError('fixture unreadable source')
                return scan(path)
            with patch.object(monitor.os, 'scandir', side_effect=blocked):
                status = read_build_progress(root)
            self.assertTrue(status['source_changed_since_build'])
            self.assertTrue(status['source_inventory_partial'])
            self.assertEqual(status['source_freshness']['status'], 'unknown')

    def test_unverified_or_naive_timestamps_cannot_claim_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(read_build_progress(root)['source_freshness']['status'], 'not_verified')
            self.fixture(root, {'engine/src/core.cpp': 946684800})
            report = root / 'engine/out/build_progress.json'
            data = json.loads(report.read_text(encoding='utf-8'))
            data['completed_at'] = '2001-01-01T00:00:00'
            report.write_text(json.dumps(data), encoding='utf-8')
            status = read_build_progress(root)
            self.assertTrue(status['source_changed_since_build'])
            self.assertEqual(status['source_freshness']['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
