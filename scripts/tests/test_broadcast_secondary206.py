"""Isolated secondary-broadcast contracts; no windows, keys or encoder are used."""
from __future__ import annotations

from contextlib import contextmanager
import importlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def fake_follow(*_):
    return SimpleNamespace(capture=SimpleNamespace(metadata=lambda:{'capture_state':'holding','game_frame_verified':False}),
                           stop=Mock(return_value=True),apply_source=Mock(return_value=('applied',None)))


class SecondaryDaemonOutputTests(unittest.TestCase):
    def test_opt_in_uses_fixed_c_paths_and_preserves_default_constructor(self):
        from scripts.tests.test_broadcast_service205 import daemon_class
        cls,_=daemon_class()
        default=cls()
        self.assertIsNone(getattr(default,'_secondary_hls_dir',None))
        secondary=cls(secondary_outputs=True)
        self.assertEqual(secondary._archive_root_override,'C:/AI-BS/recordings/secondary')
        self.assertEqual(secondary._telemetry_log_override,'C:/AI-BS/logs/secondary_ffmpeg.log')
        self.assertEqual(secondary._secondary_hls_dir,'C:/AI-BS/saved_data/broadcast_hls/secondary')
        with self.assertRaises(ValueError):cls(secondary_outputs='yes')

    def test_secondary_tee_is_c_only_atomic_bounded_hls_without_key_metadata(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,ns,_,_=load_daemon()
        daemon._archive_root_override='C:/AI-BS/recordings/secondary'
        daemon._secondary_hls_dir='C:/AI-BS/saved_data/broadcast_hls/secondary'
        daemon._secondary_outputs=True
        ns['os'].environ={}
        ns['win32gui']=SimpleNamespace(IsWindow=lambda _:True,IsWindowVisible=lambda _:True,
            IsIconic=lambda _:False,GetWindowText=lambda _:'Fortnite  ')
        ns['win32process']=SimpleNamespace(GetWindowThreadProcessId=lambda _:(1,206))
        self.assertTrue(daemon.start_stream([],game_name='Fortnite  ',fps=30,resolution='1280x720',
            sources=[{'type':'window','hwnd':206,'pid':206,'title':'Fortnite  ','enabled':True}]))
        command=ns['subprocess'].Popen.call_args.args[0]
        self.assertIn('recordings/secondary/Fortnite/stream_',command[-1])
        self.assertNotIn('E\\:',command[-1])
        self.assertIn('hls_time=2:hls_list_size=6',command[-1])
        self.assertIn('hls_flags=delete_segments+independent_segments+temp_file',command[-1])
        self.assertIn('broadcast_hls/secondary/index.m3u8',command[-1])
        self.assertIn('segment_',command[-1])
        self.assertNotIn('program_date_time',command[-1]);self.assertNotIn('key_info_file',command[-1])
        self.assertNotEqual(command[0],'ffmpeg')

    def test_secondary_telemetry_never_appends_primary_log(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,ns,process,_=load_daemon()
        daemon._telemetry_log_override='C:/AI-BS/logs/secondary_ffmpeg.log'
        daemon.is_streaming=True;process.stdout=io.StringIO('')
        daemon._telemetry_reader()
        self.assertEqual(ns['open'].call_args.args[0],'C:/AI-BS/logs/secondary_ffmpeg.log')


class SecondaryRunnerContractTests(unittest.TestCase):
    def setUp(self):self.module=importlib.import_module('backend.core.broadcast_secondary')

    def test_payload_is_exact_window_only_silent_bounded_and_never_adds_destinations(self):
        result=self.module.secondary_payload(206,900,'Fortnite  ',[{'name':'youtube','url':'rtmps://a.rtmps.youtube.com:443/live2','key':'test_only_key_206','enabled':True}])
        self.assertEqual(result['sources'],[{'type':'window','enabled':True,'hwnd':206,'pid':900,'title':'Fortnite  ','name':'Fortnite  '}])
        self.assertEqual(result['fps'],30);self.assertEqual(result['resolution'],'1280x720')
        self.assertEqual(result['encoder_choice'],'h264_nvenc');self.assertEqual(result['overlays'],[])
        self.assertEqual([ep['name'] for ep in result['endpoints']],['youtube'])
        with self.assertRaises(self.module.SecondaryError):self.module.secondary_payload(206,900,'Fortnite  ',[{'name':'unknown','url':'rtmps://unapproved.invalid/app','key':'test_only_key_206'}])

    def test_invalid_identity_rejected_before_engine_or_profile_access(self):
        with patch.object(self.module,'_load_targets',side_effect=AssertionError('profile touched')),patch.object(self.module,'_new_engine',side_effect=AssertionError('engine touched')):
            for values in [(True,900,'x'),(0,900,'x'),(206,False,'x'),(206,900,''),(206,900,'x\n')]:
                with self.subTest(values=values):
                    with self.assertRaises(self.module.SecondaryError):self.module.secondary_payload(*values,[])

    def test_twitch_server_is_fixed_official_secure_ingest_no_userinfo_query_or_arbitrary_host(self):
        self.assertEqual(self.module.twitch_server('rtmp://live.twitch.tv/app'),'rtmps://ingest.global-contribute.live-video.net:443/app')
        for value in ['rtmps://evil.invalid/app','rtmps://live.twitch.tv.evil.invalid/app','rtmps://u@live.twitch.tv/app','rtmps://live.twitch.tv/app?q=key']:
            with self.subTest(value=value):
                with self.assertRaises(self.module.SecondaryError):self.module.twitch_server(value)

    def test_load_only_requested_dpapi_targets_never_reads_unrequested_facebook(self):
        data={'destinations':{'youtube':{'enabled':True,'url':'rtmp://a.rtmp.youtube.com/live2','key_dpapi':'ZmFrZQ=='},
                              'facebook':{'enabled':True,'key_dpapi':'must not decrypt'}}}
        with patch.object(self.module,'_read_profile',return_value=data),patch.object(self.module,'_unprotect',return_value='test_only_key_206') as unprotect:
            endpoints=self.module._load_targets(('youtube',))
        self.assertEqual(len(endpoints),1);self.assertEqual(unprotect.call_args.args,('ZmFrZQ==',))
        self.assertNotIn('facebook',json.dumps(endpoints))
        data['destinations']['youtube']={'enabled':True,'url':'rtmp://a.rtmp.youtube.com/live2','key':'test_only_key_206'}
        with patch.object(self.module,'_read_profile',return_value=data):
            with self.assertRaises(self.module.SecondaryError):self.module._load_targets(('youtube',))

    def test_public_status_filters_all_raw_telemetry_and_remote_secrets(self):
        engine=SimpleNamespace(process=SimpleNamespace(pid=206,poll=lambda:None),is_streaming=True,
            telemetry={'frames_encoded':40,'out_time_us':1000000,'capture_error':'rtmps://secret/KEY',
                       'endpoints':{'youtube':'rawsecret'},'fps':'30','speed':'1.0x','last_progress_epoch':100})
        status=self.module.safe_status(engine,'running_unverified',None)
        self.assertEqual(status['frames_encoded'],40);self.assertFalse(status['ingest_verified'])
        self.assertNotIn('secret',json.dumps(status));self.assertNotIn('KEY',json.dumps(status))

    def test_encoder_cleanup_precedes_secondary_mutex_release_even_after_start_failure(self):
        for succeed in (True,False):
            with self.subTest(succeed=succeed):
                controller=self.module.SecondaryBroadcast();controller._generation=1
                events=[]
                @contextmanager
                def guard(_):
                    events.append('acquire')
                    try:yield
                    finally:events.append('release')
                @contextmanager
                def job(_):yield
                engine=SimpleNamespace(process=SimpleNamespace(pid=206,poll=lambda:None),telemetry={},is_streaming=True)
                def start(**_):controller._stop.set();return succeed
                def stop():events.append('encoder_stopped');return {'status':'stopped'}
                engine.start_stream=start;engine.stop_stream=stop
                with patch.object(self.module,'_secondary_guard',side_effect=guard),patch.object(self.module,'_owned_job',side_effect=job), \
                     patch.object(self.module,'_verify_window'),patch.object(self.module,'_load_targets',return_value=[]), \
                     patch.object(self.module,'_prepare_paths'),patch.object(self.module,'_new_engine',return_value=engine), \
                     patch.object(self.module,'_new_follow',side_effect=fake_follow),patch.object(self.module,'_process_start',return_value=1000.):
                    controller._run(206,900,'Fortnite  ',('youtube',),1)
                self.assertLess(events.index('encoder_stopped'),events.index('release'))

    def test_stop_is_bounded_and_does_not_claim_unconfirmed_cleanup(self):
        controller=self.module.SecondaryBroadcast()
        controller._thread=SimpleNamespace(join=Mock(),is_alive=lambda:True)
        self.assertFalse(controller.stop(timeout=.25))
        self.assertEqual(controller._thread.join.call_args.args,(.25,))
        for timeout in (True,0,float('nan'),9):
            with self.assertRaises(self.module.SecondaryError):controller.stop(timeout=timeout)

    def test_competing_controller_never_erases_stop_signal_or_writes_status(self):
        controller=self.module.SecondaryBroadcast();controller._generation=1
        @contextmanager
        def blocked(_):raise self.module.SecondaryError('SECONDARY_ALREADY_RUNNING');yield
        with patch.object(self.module,'_secondary_guard',side_effect=blocked),patch.object(self.module,'_prepare_paths') as prepare, \
             patch.object(self.module.STOP.__class__,'unlink') as unlink:
            controller._run(206,900,'Fortnite  ',('youtube',),1)
        prepare.assert_not_called();unlink.assert_not_called()
        self.assertFalse(getattr(controller,'_lease_acquired',False))
        controller=Mock(_lease_acquired=False)
        controller.start.return_value=controller.status.return_value={'status':'failed','error_code':'SECONDARY_ALREADY_RUNNING'}
        with patch.object(self.module,'SecondaryBroadcast',return_value=controller), \
             patch.object(self.module,'_prepare_paths',side_effect=AssertionError('unowned preparation')), \
             patch.object(self.module,'_write_status') as write,patch.object(sys,'argv',['sender','--hwnd','206','--pid','900','--title','Fortnite  ','--targets','youtube']):
            self.assertEqual(self.module.main(),1)
        write.assert_not_called()

    def test_storage_checks_leaf_log_and_title_archive_before_engine_can_write(self):
        checked=[]
        with patch.object(self.module,'_not_redirected',side_effect=checked.append),patch.object(Path,'mkdir'), \
             patch.object(self.module,'_prepare_private_ipc'):
            self.module._prepare_paths('Fortnite  ')
        self.assertIn(self.module.ARCHIVE/'Fortnite',checked)
        self.assertIn(self.module.LOGS/'secondary_ffmpeg.log',checked)

    def test_watchdog_requires_advancing_frames_and_media_time_despite_fresh_heartbeats(self):
        for advancing in (False,True):
            with self.subTest(advancing=advancing):
                controller=self.module.SecondaryBroadcast();controller._generation=1
                clock=SimpleNamespace(now=0,cycles=0)
                engine=SimpleNamespace(process=SimpleNamespace(pid=206,poll=lambda:None),is_streaming=True,
                    telemetry={'frames_encoded':30,'out_time_us':1000000,'last_progress_epoch':0},
                    start_stream=lambda **_:True,stop_stream=lambda:{'status':'stopped'})
                class Heartbeats:
                    def is_set(self):return False
                    def wait(self,_):
                        clock.now+=1;clock.cycles+=1
                        engine.telemetry['last_progress_epoch']=clock.now
                        if advancing:
                            engine.telemetry['frames_encoded']+=30;engine.telemetry['out_time_us']+=1000000
                        return clock.cycles>20
                controller._stop=Heartbeats()
                @contextmanager
                def inert(*_):yield
                with patch.object(self.module,'_secondary_guard',inert),patch.object(self.module,'_owned_job',inert), \
                     patch.object(self.module,'_verify_window'),patch.object(self.module,'_load_targets',return_value=[]), \
                     patch.object(self.module,'_prepare_paths'),patch.object(self.module,'_new_engine',return_value=engine), \
                     patch.object(self.module,'_new_follow',side_effect=fake_follow), \
                     patch.object(self.module,'_process_start',return_value=1000.), \
                     patch.object(self.module.time,'monotonic',side_effect=lambda:clock.now), \
                     patch.object(self.module.time,'time',side_effect=lambda:clock.now):
                    controller._run(206,900,'Fortnite  ',('youtube',),1)
                self.assertEqual(controller._error,None if advancing else 'ENCODER_PROGRESS_STALLED')

    def test_kick_server_accepts_only_dashboard_rtmps_host_443_app(self):
        approved='rtmps://fa723fc1b171.global-contribute.live-video.net:443/app'
        self.assertEqual(self.module.kick_server(approved),approved)
        for server in [approved.replace('rtmps:','rtmp:'),approved.replace(':443',':1935'),
                       approved.replace('/app','/app/key'),
                       approved.replace('fa723fc1b171.',''),approved.replace('live-video.net','live-video.net.evil.invalid'),
                       approved.replace('fa723fc1b171','u@fa723fc1b171'),approved+'?token=secret',
                       approved+'#ignored','srt://127.0.0.1:9000',approved+'\n',None]:
            with self.subTest(server=server):
                with self.assertRaises(self.module.SecondaryError):self.module.kick_server(server)

    def test_kick_dashboard_root_normalizes_only_secure_same_host_to_documented_app(self):
        canonical='rtmps://fa723fc1b171.global-contribute.live-video.net:443/app'
        for url in ['rtmps://fa723fc1b171.global-contribute.live-video.net/',
                    'rtmps://fa723fc1b171.global-contribute.live-video.net',
                    'rtmps://fa723fc1b171.global-contribute.live-video.net:443/',
                    'rtmps://fa723fc1b171.global-contribute.live-video.net/app']:
            with self.subTest(url=url):self.assertEqual(self.module.kick_server(url),canonical)
        for url in ['rtmps://fa723fc1b171.global-contribute.live-video.net:444/',
                    'rtmps://fa723fc1b171.global-contribute.live-video.net/other',
                    'rtmps://fa723fc1b171.global-contribute.live-video.net.evil.invalid/',
                    'rtmp://fa723fc1b171.global-contribute.live-video.net/']:
            with self.subTest(url=url):
                with self.assertRaises(self.module.SecondaryError):self.module.kick_server(url)

    def test_kick_load_requires_protected_credential_and_rejects_bad_host_before_decrypt(self):
        destination={'enabled':True,'url':'rtmps://fa723fc1b171.global-contribute.live-video.net:443/app','key_dpapi':'ZmFrZQ=='}
        saved={'destinations':{'kick':destination,'facebook':{'key_dpapi':'never decrypt'}}}
        with patch.object(self.module,'_read_profile',return_value=saved),patch.object(self.module,'_unprotect',return_value='test_only_kick_key206') as decrypt:
            loaded=self.module._load_targets(('kick',))
            self.assertEqual(loaded[0]['name'],'kick');self.assertEqual(loaded[0]['url'],destination['url'])
            self.assertEqual(decrypt.call_args.args,('ZmFrZQ==',))
            destination['url']='rtmps://evil.invalid:443/app';decrypt.reset_mock()
            with self.assertRaises(self.module.SecondaryError):self.module._load_targets(('kick',))
            decrypt.assert_not_called()
        destination={'enabled':True,'url':'rtmps://fa723fc1b171.global-contribute.live-video.net:443/app','key':'plaintext_fixture_only'}
        with patch.object(self.module,'_read_profile',return_value={'destinations':{'kick':destination}}),patch.object(self.module,'_unprotect') as decrypt:
            with self.assertRaises(self.module.SecondaryError):self.module._load_targets(('kick',))
            decrypt.assert_not_called()

    def test_three_explicit_targets_and_cli_accept_kick_without_adding_capture_sources(self):
        endpoints=[{'name':name,'enabled':True,'key':'test_only_key206','url':url} for name,url in [
            ('youtube','rtmps://a.rtmps.youtube.com:443/live2'),
            ('twitch','rtmps://ingest.global-contribute.live-video.net:443/app'),
            ('kick','rtmps://fa723fc1b171.global-contribute.live-video.net:443/app')]]
        payload=self.module.secondary_payload(206,900,'Fortnite  ',endpoints)
        self.assertEqual(len(payload['sources']),1);self.assertEqual(len(payload['endpoints']),3)
        self.assertEqual(self.module._target_names(('youtube','twitch','kick')),('youtube','twitch','kick'))
        with self.assertRaises(self.module.SecondaryError):self.module._target_names(('kick','kick'))
        controller=Mock(_lease_acquired=False);controller.start.return_value={'status':'failed','error_code':'SECONDARY_ALREADY_RUNNING'}
        with patch.object(self.module,'SecondaryBroadcast',return_value=controller),patch.object(sys,'argv',[
                'sender','--hwnd','206','--pid','900','--title','Fortnite  ','--targets','youtube','twitch','kick']):
            self.assertEqual(self.module.main(),1)
        self.assertEqual(controller.start.call_args.kwargs['targets'],['youtube','twitch','kick'])

    def test_facebook_accepts_only_exact_approved_secure_ingest(self):
        approved='rtmps://live-api-s.facebook.com:443/rtmp/'
        self.assertEqual(self.module.facebook_server(approved),approved)
        for server in [approved.replace('rtmps:','rtmp:'),approved.replace(':443',':1935'),
                       approved.replace(':443',''),approved.replace('facebook.com','facebook.com.evil.invalid'),
                       approved.replace('live-api-s.','other.'),approved.replace('live-api-s.','u@live-api-s.'),
                       approved+'key',approved+'?key=secret',approved+'#ignored',None]:
            with self.subTest(server=server):
                with self.assertRaises(self.module.SecondaryError):self.module.facebook_server(server)

    def test_facebook_load_requires_dpapi_and_rejects_server_before_decrypt(self):
        target={'enabled':True,'url':'rtmps://live-api-s.facebook.com:443/rtmp/','key_dpapi':'ZmFrZQ=='}
        with patch.object(self.module,'_read_profile',return_value={'destinations':{'facebook':target}}),patch.object(self.module,'_unprotect',return_value='FB-fixture_only_key206') as decrypt:
            endpoints=self.module._load_targets(('facebook',))
            self.assertEqual(endpoints[0]['name'],'facebook');self.assertEqual(endpoints[0]['url'],target['url'])
            self.assertEqual(decrypt.call_args.args,('ZmFrZQ==',))
            target['url']='rtmps://unapproved.invalid:443/rtmp/';decrypt.reset_mock()
            with self.assertRaises(self.module.SecondaryError):self.module._load_targets(('facebook',))
            decrypt.assert_not_called()
        target={'enabled':True,'url':'rtmps://live-api-s.facebook.com:443/rtmp/','key':'plaintext_fixture_only'}
        with patch.object(self.module,'_read_profile',return_value={'destinations':{'facebook':target}}):
            with self.assertRaises(self.module.SecondaryError):self.module._load_targets(('facebook',))

    def test_four_explicit_targets_share_one_exact_window_and_cli_defaults_stay_unchanged(self):
        targets=('youtube','twitch','kick','facebook')
        endpoints=[{'name':name,'enabled':True,'key':'test_only_key206','url':url} for name,url in [
            ('youtube','rtmps://a.rtmps.youtube.com:443/live2'),
            ('twitch','rtmps://ingest.global-contribute.live-video.net:443/app'),
            ('kick','rtmps://fa723fc1b171.global-contribute.live-video.net:443/app'),
            ('facebook','rtmps://live-api-s.facebook.com:443/rtmp/')]]
        self.assertEqual(self.module._target_names(targets),targets)
        payload=self.module.secondary_payload(206,900,'Fortnite  ',endpoints)
        self.assertEqual(len(payload['sources']),1);self.assertEqual(len(payload['endpoints']),4)
        self.assertEqual(payload['encoder_choice'],'h264_nvenc')
        self.assertEqual(self.module.SecondaryBroadcast.start.__kwdefaults__['targets'],('youtube','twitch'))
        controller=Mock(_lease_acquired=False);controller.start.return_value={'status':'failed','error_code':'SECONDARY_ALREADY_RUNNING'}
        with patch.object(self.module,'SecondaryBroadcast',return_value=controller),patch.object(sys,'argv',[
                'sender','--hwnd','206','--pid','900','--title','Fortnite  ','--targets',*targets]):
            self.assertEqual(self.module.main(),1)
        self.assertEqual(controller.start.call_args.kwargs['targets'],list(targets))


if __name__=='__main__':unittest.main()
