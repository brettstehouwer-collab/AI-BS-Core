"""Offline FFmpeg command construction: no daemon import or external process."""
from __future__ import annotations
import ast
import asyncio
from pathlib import Path
import subprocess
import types
import unittest
from unittest.mock import Mock
from typing import Any, Dict, List, Optional
from scripts.tests.test_broadcast_daemon_integrity import load_daemon

SOURCE=Path(__file__).resolve().parents[2]/'backend/aibs_broadcast_daemon.py'


def microphone_probe(stderr='', exception=None):
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='detect_microphone')
    run=Mock(return_value=types.SimpleNamespace(stderr=stderr),side_effect=exception)
    namespace={'Optional':Optional,'subprocess':types.SimpleNamespace(run=run,PIPE=-1,TimeoutExpired=subprocess.TimeoutExpired),
               'logging':Mock(),'re':__import__('re')}
    exec(compile(ast.Module([function],type_ignores=[]),str(SOURCE),'exec'),namespace)
    return namespace['detect_microphone'],run


class MicrophoneProbeTests(unittest.TestCase):
    def test_no_device_does_not_invent_realtek(self):
        probe,run=microphone_probe('No audio capture devices found.');self.assertIsNone(probe())
        self.assertLessEqual(run.call_args.kwargs['timeout'],5)

    def test_probe_timeout_becomes_unavailable(self):
        probe,run=microphone_probe(exception=subprocess.TimeoutExpired('fixture ffmpeg',3));self.assertIsNone(probe())

    def test_non_keyword_device_name_uses_actual_enumerated_device(self):
        probe,run=microphone_probe('[dshow] "Stereo Mix" (audio)\n[dshow] Alternative name "fixture"')
        self.assertEqual(probe(),'Stereo Mix')


class CaptureInputTests(unittest.TestCase):
    def start(self,sources,game_name='General',**context):
        daemon,namespace,process,_=load_daemon()
        namespace.update(context)
        namespace['detect_microphone']=context.get('detect_microphone',Mock(return_value='fixture microphone'))
        result=daemon.start_stream([],sources=sources,game_name=game_name)
        command=namespace['subprocess'].Popen.call_args.args[0] if namespace['subprocess'].Popen.called else []
        return daemon,namespace,result,command

    def test_explicit_video_only_does_not_open_unrequested_microphone(self):
        daemon,ns,result,command=self.start([{'type':'screen','enabled':True}])
        self.assertTrue(result);self.assertFalse(ns['detect_microphone'].called)
        self.assertIn('anullsrc=channel_layout=stereo:sample_rate=48000',command)
        self.assertFalse(any(str(x).startswith('audio=') for x in command))

    def test_missing_requested_microphone_uses_valid_silent_audio_input(self):
        daemon,ns,result,command=self.start([{'type':'screen'},{'type':'mic','deviceId':'default'}],detect_microphone=Mock(return_value=None))
        self.assertTrue(result);self.assertIn('anullsrc=channel_layout=stereo:sample_rate=48000',command)
        self.assertNotIn('audio=None',command)

    def test_explicit_microphone_device_remains_selected(self):
        daemon,ns,result,command=self.start([{'type':'screen'},{'type':'mic','deviceId':'Fixture USB'}])
        self.assertTrue(result);self.assertIn('audio=Fixture USB',command);self.assertFalse(ns['detect_microphone'].called)

    def test_all_video_disabled_holds_without_desktop_fallback(self):
        daemon,ns,result,command=self.start([{'type':'game','enabled':False},{'type':'mic','deviceId':'Fixture USB'}])
        self.assertFalse(result);self.assertFalse(command);self.assertFalse(daemon.is_streaming)

    def test_camera_only_uses_camera_as_primary_without_desktop(self):
        daemon,ns,result,command=self.start([{'type':'cam','deviceId':'Fixture camera','enabled':True}])
        self.assertTrue(result);self.assertIn('video=Fixture camera',command);self.assertNotIn('desktop',command)
        self.assertNotIn('gdigrab',command)

    def test_selected_window_handle_binds_surface_without_desktop_crop(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:h==205,IsWindowVisible=lambda h:True,
                                  IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window',
                                  GetWindowRect=Mock(side_effect=AssertionError('No desktop crop')))
        obs=Mock()
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'title':'Fixture window','enabled':True}],win32gui=gui,OBSOrchestrator=obs)
        self.assertTrue(result);self.assertFalse(obs.called)
        self.assertIn('rawvideo',command);self.assertIn('pipe:0',command);self.assertNotIn('gdigrab',command);self.assertNotIn('desktop',command)
        self.assertEqual(ns['NativeWindowCapture'].call_args.args[0],205)
        self.assertFalse(gui.GetWindowRect.called)

    def test_closed_selected_window_holds_without_obs_or_full_desktop(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:False)
        obs=Mock()
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window','enabled':True}],win32gui=gui,OBSOrchestrator=obs)
        self.assertFalse(result);self.assertFalse(command);self.assertFalse(obs.called)

    def test_minimized_selected_window_holds_without_full_desktop(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:True)
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window','enabled':True}],win32gui=gui)
        self.assertFalse(result);self.assertFalse(command)

    def test_legacy_omitted_selection_holds_without_capture_or_microphone(self):
        daemon,ns,result,command=self.start(None,detect_microphone=Mock(return_value=None))
        self.assertFalse(result);self.assertFalse(ns['detect_microphone'].called);self.assertFalse(command)
        self.assertEqual(daemon.telemetry.get('capture_error_code'),'capture_selection_required')

    def test_explicit_desktop_is_not_rerouted_to_obs_by_game_metadata(self):
        obs=Mock()
        daemon,ns,result,command=self.start([{'type':'screen','name':'Full desktop'}],game_name='Fixture browser window',OBSOrchestrator=obs)
        self.assertTrue(result);self.assertFalse(obs.called);self.assertIn('gdigrab',command)

    def test_generated_silence_does_not_add_a_second_throttled_input_clock(self):
        daemon,ns,result,command=self.start([{'type':'screen'}])
        self.assertTrue(result)
        silence=command.index('anullsrc=channel_layout=stereo:sample_rate=48000')
        self.assertNotIn('-re',command[max(0,silence-8):silence])

    def test_explicit_empty_sources_holds_without_encoder(self):
        daemon,ns,result,command=self.start([])
        self.assertFalse(result);self.assertFalse(command)

    def test_daw_without_device_cannot_fall_back_to_microphone(self):
        daemon,ns,result,command=self.start([{'type':'screen'},{'type':'daw','enabled':True}])
        self.assertTrue(result);self.assertFalse(ns['detect_microphone'].called)
        self.assertIn('anullsrc=channel_layout=stereo:sample_rate=48000',command)

    def test_api_preserves_omitted_and_explicit_empty_source_intent(self):
        from pydantic import BaseModel
        tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
        model=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='StreamStartRequest')
        endpoint=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start_stream_endpoint');endpoint.decorator_list=[]
        dispatch=Mock(return_value=False)
        ns={'BaseModel':BaseModel,'Optional':Optional,'List':List,'Dict':Dict,'Any':Any,'daemon':types.SimpleNamespace(start_stream=dispatch),'__name__':'offline_fixture'}
        exec(compile(ast.Module([model,endpoint],type_ignores=[]),str(SOURCE),'exec'),ns)
        ns['StreamStartRequest'].model_rebuild(_types_namespace=ns)
        for body,expected in [({},None),({'sources':[]},[]),({'sources':[{'type':'screen'}]},[{'type':'screen'}])]:
            asyncio.run(ns['start_stream_endpoint'](ns['StreamStartRequest'](**body)))
            self.assertEqual(dispatch.call_args.kwargs['sources'],expected)

    def test_selected_window_title_mismatch_holds_without_fallback(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Different window',GetWindowRect=lambda h:(0,0,1280,720))
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'title':'Fixture window'}],win32gui=gui)
        self.assertFalse(result);self.assertFalse(command)

    def test_window_without_handle_cannot_expand_to_whole_desktop(self):
        daemon,ns,result,command=self.start([{'type':'window','name':'Fixture window'}])
        self.assertFalse(result);self.assertFalse(command)

    def test_unknown_game_target_cannot_expand_to_desktop_without_obs(self):
        daemon,ns,result,command=self.start([{'type':'game','name':'Fixture unknown target'}])
        self.assertFalse(result);self.assertFalse(command)

    def test_optional_process_identity_mismatch_holds(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window',GetWindowRect=lambda h:(0,0,1280,720))
        processes=types.SimpleNamespace(GetWindowThreadProcessId=lambda h:(1,900))
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'title':'Fixture window','pid':901}],win32gui=gui,win32process=processes)
        self.assertFalse(result);self.assertFalse(command)

    def test_actual_native_name_only_window_shape_binds_surface(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window','enabled':True}],win32gui=gui)
        self.assertTrue(result);self.assertIn('pipe:0',command);self.assertNotIn('desktop',command)
        self.assertEqual(ns['NativeWindowCapture'].call_args.args[0],205)

    def test_window_capture_holds_without_verified_window_surface_provider(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window'}],win32gui=gui,NativeWindowCapture=None)
        self.assertFalse(result);self.assertFalse(command)
        self.assertEqual(daemon.telemetry.get('capture_error_code'),'window_capture_unavailable')

    def test_native_name_fallback_still_requires_actual_window_identity(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Different window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window'}],win32gui=gui)
        self.assertFalse(result);self.assertFalse(command)

    def test_explicit_title_remains_authoritative_over_display_name(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'title':'Fixture window','name':'Display label'}],win32gui=gui)
        self.assertTrue(result);self.assertIn('pipe:0',command);self.assertNotIn('gdigrab',command)

    def test_explicit_empty_title_cannot_fall_back_to_native_name(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'title':'','name':'Fixture window'}],win32gui=gui)
        self.assertFalse(result);self.assertFalse(command)

    def test_rawvideo_without_attached_pipe_never_sends_q_as_pixels(self):
        daemon,ns,process,_=load_daemon();daemon._rawvideo_input=True;daemon._window_pipe=None
        process.terminate.side_effect=lambda:process.poll.configure_mock(return_value=0)
        daemon.stop_stream();process.stdin.write.assert_not_called();process.terminate.assert_called_once()

    def test_pipe_attachment_failure_requests_encoder_termination(self):
        gui=types.SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,IsIconic=lambda h:False,GetWindowText=lambda h:'Fixture window')
        daemon,ns,result,command=self.start([{'type':'window','hwnd':205,'name':'Fixture window'}],win32gui=gui,
            WindowCapturePipe=Mock(side_effect=ValueError('fixture invalid pipe')))
        self.assertFalse(result);ns['subprocess'].Popen.return_value.terminate.assert_called()

    def test_binary_ffmpeg_diagnostics_are_decoded_then_redacted(self):
        import io
        daemon,ns,process,log=load_daemon();daemon.is_streaming=True;daemon._stream_secrets=('fixture-secret',)
        process.stdout=io.BytesIO(b'frame=1 fps=30.0 bitrate=6000.0kbits/s\nOpening rtmps://example.invalid/fixture-secret\n')
        daemon._telemetry_reader();written=''.join(c.args[0] for c in log.write.call_args_list)
        self.assertEqual(daemon.telemetry['fps'],'30.0');self.assertNotIn('fixture-secret',written)

    def test_tee_outputs_require_explicit_global_codec_headers(self):
        daemon,ns,result,command=self.start([{'type':'screen'}])
        self.assertTrue(result);self.assertEqual(command[command.index('-flags')+1],'+global_header')

    def test_newline_progress_is_enabled_without_carriage_return_stats(self):
        daemon,ns,result,command=self.start([{'type':'screen'}])
        self.assertTrue(result);self.assertIn('-nostats',command)
        self.assertEqual(command[command.index('-progress')+1],'pipe:2')
        self.assertEqual(command[command.index('-stats_period')+1],'1')

    def test_newline_progress_commits_current_session_and_safe_marker(self):
        import io
        daemon,ns,process,log=load_daemon();daemon.is_streaming=True;session=(77,1234.5)
        daemon._stream_session=session
        process.stdout=io.BytesIO(b'frame=30\nfps=30.00\nbitrate=1000.0kbits/s\nspeed=1.00x\ndrop_frames=2\nout_time_us=1000000\nprogress=continue\n')
        daemon._telemetry_reader(process,session,())
        self.assertEqual(daemon.telemetry['frames_encoded'],30);self.assertEqual(daemon.telemetry['fps'],'30.00')
        self.assertEqual(daemon.telemetry['dropped'],'2');self.assertEqual(daemon.telemetry['out_time_us'],1000000)
        self.assertEqual(log.write.call_args_list[0].args[0],'[SESSION pid=77 epoch=1234.5]\n')

    def test_stale_session_reader_cannot_log_or_overwrite_current_metrics(self):
        import io
        daemon,ns,old,log=load_daemon();daemon.is_streaming=True;daemon._stream_session=(88,9999.0)
        daemon.process=Mock();daemon.telemetry['fps']='new'
        old.stdout=io.BytesIO(b'frame=1000\nfps=1000\nprogress=continue\n')
        daemon._telemetry_reader(old,(77,1234.5),())
        self.assertEqual(daemon.telemetry['fps'],'new');ns['open'].assert_not_called();self.assertTrue(daemon.is_streaming)

    def test_reader_thread_receives_owned_process_and_session_at_spawn(self):
        daemon,ns,result,command=self.start([{'type':'screen'}])
        kwargs=ns['threading'].Thread.call_args.kwargs
        self.assertIs(kwargs['args'][0],daemon.process);self.assertEqual(kwargs['args'][1],daemon._stream_session)


if __name__=='__main__':unittest.main()
