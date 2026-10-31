"""Strict local coordinator intent fixtures; no profile, windows or live IPC."""
from __future__ import annotations
import importlib
import json
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from contextlib import contextmanager
import sys


class SecondaryControlTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('backend.core.broadcast_secondary');self.session='a'*32
    def command(self,**changes):
        result={'version':2,'request_id':'b'*32,'session_id':self.session,'action':'select_source',
                'source_mode':'auto_game','source':None};result.update(changes);return result
    def test_exact_session_source_schema_and_no_extra_credentials(self):
        self.assertEqual(self.m.validate_control_command(self.command(),self.session),self.command())
        variants=[self.command(session_id='c'*32),self.command(version=True),self.command(request_id='nothex'),
                  self.command(action='shell'),self.command(source_mode='desktop'),self.command(api_key='fixture'),
                  self.command(source={'hwnd':1}),self.command(source_mode='window',source={'hwnd':True,'pid':1,'title':'x'}),
                  self.command(source_mode='window',source={'hwnd':1,'pid':2,'title':'x','exe':'untrusted'}),
                  self.command(source_mode='screen',source={'screen_id':''})]
        for value in variants:
            with self.subTest(value=value):
                with self.assertRaises(self.m.SecondaryError):self.m.validate_control_command(value,self.session)
    def test_window_and_screen_intents_remain_exact_manual_no_audio_fields(self):
        for mode,source in [('window',{'hwnd':207,'pid':900,'title':'Fixture  '}),('screen',{'screen_id':'display-1'})]:
            request=self.command(source_mode=mode,source=source)
            self.assertEqual(self.m.validate_control_command(request,self.session)['source'],source)
        payload=self.m.follow_payload([])
        self.assertEqual(payload['sources'],[{'type':'game','enabled':True,'capture_policy':'verified_game_follow'}])
        self.assertNotIn('hwnd',payload['sources'][0]);self.assertEqual(payload['audio_bitrate'],'128k')
    def test_bounded_reader_rejects_duplicate_nonfinite_and_oversize_json(self):
        with tempfile.TemporaryDirectory(prefix='aibs-control207-') as temp:
            path=Path(temp)/'command.json'
            with patch.object(self.m,'COMMAND',path),patch.object(self.m._ipc,'validate_private_path'):
                for raw in ['{"version":2,"version":2}','{"x":NaN}',' '*16385]:
                    path.write_text(raw,encoding='utf-8')
                    with self.subTest(raw=raw[:25]):
                        with self.assertRaises(self.m.SecondaryError):self.m.read_control_command(self.session)
                path.write_text(json.dumps(self.command()),encoding='utf-8')
                self.assertEqual(self.m.read_control_command(self.session)['request_id'],'b'*32)
    def test_stop_request_is_scoped_and_legacy_or_stale_content_does_not_stop_new_session(self):
        with tempfile.TemporaryDirectory(prefix='aibs-stop207-') as temp:
            path=Path(temp)/'stop.json'
            with patch.object(self.m,'STOP',path),patch.object(self.m._ipc,'validate_private_path'):
                for value in ['stop',json.dumps({'version':2,'session_id':'c'*32,'request_id':'b'*32})]:
                    path.write_text(value,encoding='utf-8');self.assertIsNone(self.m.read_stop_request(self.session))
                path.write_text(json.dumps({'version':2,'session_id':self.session,'request_id':'b'*32}),encoding='utf-8')
                self.assertEqual(self.m.read_stop_request(self.session),'b'*32)
    def test_manual_pending_and_screen_block_auto_without_any_provider_start(self):
        from backend.core.game_capture_selection import SelectionDecision
        sampler=SimpleNamespace(start=Mock(return_value=True),stop=Mock(return_value=True),set_intent=Mock(return_value=True),
                                latest=Mock(return_value=SelectionDecision(None,'NO_VERIFIED_GAME',True)),resolve_window=Mock(return_value=None))
        runtime=self.m.FollowRuntime('auto_game',None,sampler=sampler)
        self.addCleanup(runtime.stop)
        result=runtime.apply_source('window',{'hwnd':207,'pid':900,'title':'Fixture  '})
        self.assertEqual(result,('held','WINDOW_EVIDENCE_PENDING'));self.assertTrue(runtime.select().manual)
        self.assertIsNone(runtime.select().source)
        self.assertEqual(runtime.apply_source('screen',{'screen_id':'display-1'}),('held','MANUAL_SCREEN_UNSUPPORTED'))
        self.assertTrue(runtime.select().manual);self.assertIsNone(runtime.select().source)
        self.assertEqual(runtime.apply_source('auto_game',None),('applied',None))

    def test_follow_constructor_invalid_or_failed_intent_cleans_owned_sampler(self):
        sampler=SimpleNamespace(start=Mock(return_value=True),stop=Mock(return_value=True),set_intent=Mock(side_effect=RuntimeError('fixture')))
        with self.assertRaises(self.m.SecondaryError):self.m.FollowRuntime('invalid',None,sampler=sampler)
        sampler.start.assert_not_called()
        with self.assertRaises(self.m.SecondaryError):self.m.FollowRuntime('auto_game',None,sampler=sampler)
        sampler.stop.assert_called()

    def test_follow_stop_cleans_sampler_even_when_provider_cleanup_raises(self):
        sampler=SimpleNamespace(start=Mock(return_value=True),stop=Mock(return_value=True),set_intent=Mock(return_value=True))
        runtime=self.m.FollowRuntime('auto_game',None,sampler=sampler)
        runtime.capture.stop=Mock(side_effect=RuntimeError('fixture'))
        self.assertFalse(runtime.stop());sampler.stop.assert_called()

    def test_control_ack_is_session_bound_idempotent_and_does_not_expose_source(self):
        controller=self.m.SecondaryBroadcast();controller._session_id=self.session
        controller._follow=SimpleNamespace(apply_source=Mock(return_value=('held','MANUAL_SCREEN_UNSUPPORTED')),
            capture=SimpleNamespace(metadata=lambda:{'capture_state':'holding','game_frame_verified':True,
                'holding_reason':'MANUAL_SCREEN_UNSUPPORTED','title':'private title','exe':'private process path'}))
        command=self.command(source_mode='screen',source={'screen_id':'display-1'})
        with patch.object(self.m,'read_control_command',return_value=command):
            controller._handle_control();controller._handle_control()
        controller._follow.apply_source.assert_called_once()
        status=controller.status();self.assertEqual(status['last_command_id'],'b'*32)
        self.assertEqual(status['command_status'],'held');self.assertFalse(status['game_frame_verified'])
        self.assertEqual(status['protocol_version'],2)
        self.assertNotIn('private',json.dumps(status))
        controller._follow.apply_source.reset_mock()
        with patch.object(self.m,'read_control_command',side_effect=self.m.SecondaryError('INVALID_CONTROL_COMMAND')):
            controller._handle_control()
        controller._follow.apply_source.assert_not_called()

    def test_auto_cli_accepts_no_window_identity_and_does_not_start_on_parser_read(self):
        controller=Mock(_lease_acquired=False);controller.start.return_value={'status':'failed','error_code':'SECONDARY_ALREADY_RUNNING'}
        with patch.object(self.m,'SecondaryBroadcast',return_value=controller),patch.object(sys,'argv',[
                'sender','--source-mode','auto_game','--targets','youtube','twitch','kick','facebook']):
            self.assertEqual(self.m.main(),1)
        self.assertEqual(controller.start.call_args.args,(None,None,None))
        self.assertEqual(controller.start.call_args.kwargs['source_mode'],'auto_game')

    def test_unsafe_ipc_fails_before_discovery_capture_or_encoder_creation(self):
        controller=self.m.SecondaryBroadcast();controller._generation=1
        @contextmanager
        def guard(_):yield
        with patch.object(self.m,'_secondary_guard',guard),patch.object(self.m,'_load_targets',return_value=[]), \
             patch.object(self.m,'_process_start',return_value=1000.), \
             patch.object(self.m,'_prepare_private_ipc',side_effect=self.m.SecondaryError('IPC_OWNER_MISMATCH')), \
             patch.object(self.m,'_new_follow') as follow,patch.object(self.m,'_new_engine') as engine:
            controller._run(None,None,None,('youtube',),1,'auto_game')
        follow.assert_not_called();engine.assert_not_called()
        self.assertEqual(controller.status()['error_code'],'IPC_OWNER_MISMATCH')

    def test_unprovable_controller_identity_fails_before_credentials_or_dispatch(self):
        controller=self.m.SecondaryBroadcast();controller._generation=1
        @contextmanager
        def guard(_):yield
        with patch.object(self.m,'_secondary_guard',guard),patch.object(self.m,'_process_start',return_value=None), \
             patch.object(self.m,'_load_targets') as targets,patch.object(self.m,'_new_follow') as follow:
            controller._run(None,None,None,('youtube',),1,'auto_game')
        targets.assert_not_called();follow.assert_not_called()
        self.assertEqual(controller.status()['error_code'],'CONTROLLER_IDENTITY_UNAVAILABLE')

    def test_terminal_worker_failure_prints_only_sanitized_status_and_error(self):
        for error in ('IPC_OWNER_MISMATCH','rtmps://fixture/private-key'):
            controller=Mock(_lease_acquired=True)
            controller.start.return_value=controller.status.return_value={'status':'failed','error_code':error,
                'session_id':'private_session','source':{'title':'private title'},'private_path':'C:/private'}
            output=io.StringIO()
            with patch.object(self.m,'SecondaryBroadcast',return_value=controller),patch.object(sys,'stdout',output), \
                 patch.object(sys,'argv',['sender','--source-mode','auto_game','--targets','youtube']):
                self.assertEqual(self.m.main(),1)
            result=json.loads(output.getvalue())
            self.assertEqual(set(result),{'status','error_code'})
            self.assertEqual(result['status'],'failed')
            self.assertNotIn('private',output.getvalue())
            if error=='IPC_OWNER_MISMATCH':self.assertEqual(result['error_code'],error)


class SecondaryProviderHookTests(unittest.TestCase):
    def test_secondary_internal_follow_holding_provider_bypasses_all_window_desktop_and_obs_paths(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,ns,_,_=load_daemon();daemon._secondary_outputs=True;ns['os'].environ={}
        provider=SimpleNamespace(width=2,height=2,fps=30,start=Mock(return_value={'capture_state':'holding'}),
            read_frame=Mock(return_value=b'\0\0\0\xff'*4),stop=Mock(return_value=True))
        daemon._capture_provider_override=provider
        self.assertTrue(daemon.start_stream([],fps=30,resolution='2x2',sources=[{'type':'game','enabled':True,'capture_policy':'verified_game_follow'}]))
        command=ns['subprocess'].Popen.call_args.args[0]
        self.assertIn('rawvideo',command);self.assertIn('pipe:0',command)
        self.assertNotIn('gdigrab',command);ns['NativeWindowCapture'].assert_not_called()
    def test_http_marker_without_internal_secondary_provider_is_held(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,ns,_,_=load_daemon()
        self.assertFalse(daemon.start_stream([],sources=[{'type':'game','enabled':True,'capture_policy':'verified_game_follow'}]))
        ns['subprocess'].Popen.assert_not_called()


if __name__=='__main__':unittest.main()
