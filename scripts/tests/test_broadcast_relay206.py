"""Offline relay fixtures. All keys/endpoints here are synthetic; no live dispatch."""
from __future__ import annotations
from contextlib import nullcontext
import importlib
import io
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class BroadcastRelayContractTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('backend.core.broadcast_relay')
        self.folder=tempfile.TemporaryDirectory(prefix='relay206_fixture_')
        self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self.source=self.root/'stream_1234567890.mp4'
        self.source.write_bytes(b'\x00\x00\x00\x18ftypisom'+b'\x00'*12)
        p=patch.object(self.module,'RECORDING_ROOT',self.root);p.start();self.addCleanup(p.stop)

    def test_youtube_known_cleartext_server_is_upgraded_to_fixed_secure_ingest(self):
        self.assertEqual(self.module.youtube_server('rtmp://a.rtmp.youtube.com/live2'),
                         'rtmps://a.rtmps.youtube.com:443/live2')
        self.assertEqual(self.module.youtube_server('rtmps://a.rtmps.youtube.com/live2/'),
                         'rtmps://a.rtmps.youtube.com:443/live2')

    def test_arbitrary_hosts_ports_credentials_query_and_paths_are_rejected(self):
        for url in ('rtmps://localhost/live2','rtmps://a.rtmps.youtube.com.hostile.invalid/live2',
                    'rtmps://a.rtmps.youtube.com:444/live2','rtmps://u:p@a.rtmps.youtube.com/live2',
                    'rtmps://a.rtmps.youtube.com/live2?key=fixture','rtmps://a.rtmps.youtube.com/other'):
            with self.subTest(url=url):
                with self.assertRaises(self.module.RelayError):self.module.youtube_server(url)

    def test_only_direct_expected_mp4_archive_is_accepted(self):
        self.assertEqual(self.module.validate_source(self.source),self.source.resolve())
        for path in (self.root/'other.mp4',self.root/'nested/stream_1234567890.mp4',Path('C:/AI-BS/.env')):
            with self.subTest(path=path):
                with self.assertRaises(self.module.RelayError):self.module.validate_source(path)

    def test_copy_command_seeks_after_input_and_never_encodes(self):
        command=self.module._relay_command(self.source,'rtmps://a.rtmps.youtube.com:443/live2','fixture-key-only',26.0)
        self.assertEqual(command[command.index('-follow')+1],'1')
        self.assertGreater(command.index('-ss'),command.index('-i'))
        self.assertEqual(command[command.index('-c')+1],'copy')
        self.assertEqual(command[command.index('-tls_verify')+1],'1')
        self.assertIn('-nostdin',command)
        self.assertNotIn('libx264',command);self.assertNotIn('h264_nvenc',command)
        self.assertEqual(command[-1],'rtmps://a.rtmps.youtube.com:443/live2/fixture-key-only')

    def test_stream_key_cannot_inject_another_url_or_protocol(self):
        for key in ('','a/b','a?b','a\nb','rtmps://other','x'*300):
            with self.subTest(key=key):
                with self.assertRaises(self.module.RelayError):self.module.validate_key(key)

    def test_unnamed_windows_job_uses_supported_empty_string(self):
        import win32api,win32job
        def create(security,name):
            if name is None:raise TypeError('None is not a valid string in this context')
            return 206
        with patch.object(win32job,'CreateJobObject',side_effect=create) as create_job, \
             patch.object(win32job,'QueryInformationJobObject',return_value={'BasicLimitInformation':{'LimitFlags':0}}), \
             patch.object(win32job,'SetInformationJobObject'),patch.object(win32job,'AssignProcessToJobObject'), \
             patch.object(win32api,'CloseHandle'):
            with self.module._owned_job(SimpleNamespace(_handle=123)):pass
        create_job.assert_called_once_with(None,'')


class BroadcastRelayLifecycleTests(unittest.TestCase):
    def setUp(self):
        BroadcastRelayContractTests.setUp(self)
        self.process=None
        owner=self
        class Process:
            pid=20601
            def __init__(self):
                self.code=None;self.stdout=io.BytesIO(b'frame=1\nout_time_us=1000000\nspeed=1.0x\nprogress=continue\n')
            def poll(self):return self.code
            def terminate(self):self.code=0
            def kill(self):self.code=-9
            def wait(self,timeout=None):return self.code
        def spawn(*args):owner.process=Process();return owner.process
        self.patchers=[patch.object(self.module,'probe_source',return_value={'duration':30.0,'video_codec':'h264','audio_codec':'aac'}),
                       patch.object(self.module,'_spawn_relay',side_effect=spawn),
                       patch.object(self.module,'_target_guard',return_value=nullcontext()),
                       patch.object(self.module,'_owned_job',return_value=nullcontext())]
        for item in self.patchers:item.start();self.addCleanup(item.stop)
        self.manager=self.module.BroadcastRelay();self.addCleanup(self.manager.stop)

    def start(self,**kwargs):
        return self.manager.start(self.source,'rtmps://a.rtmps.youtube.com/live2','fixture-key-only',timeout=1,**kwargs)

    def test_progress_proves_packetcopy_only_not_platform_ingest(self):
        result=self.start()
        self.assertEqual(result['status'],'relaying_unverified')
        self.assertEqual(result['pid'],20601)
        self.assertGreater(result['frames'],0)
        self.assertFalse(result['platform_ingest_verified'])
        self.assertFalse(result['primary_modified'])

    def test_second_start_does_not_spawn_duplicate_target(self):
        self.start();first=self.process
        result=self.start()
        self.assertEqual(result['pid'],first.pid)
        self.assertIs(self.process,first)

    def test_stop_terminates_only_its_captured_relay(self):
        self.start();self.assertTrue(self.manager.stop(timeout=1))
        self.assertIsNotNone(self.process.poll())
        self.assertIn(self.manager.status()['status'],('stopped','error'))

    def test_source_replacement_stops_owned_relay(self):
        self.start();self.source.unlink();self.source.write_bytes(b'\x00\x00\x00\x18ftypisom'+b'\x01'*12)
        deadline=time.monotonic()+1
        while self.manager.status()['status']!='error' and time.monotonic()<deadline:time.sleep(.02)
        self.assertEqual(self.manager.status()['error_code'],'SOURCE_CHANGED')
        self.assertIsNotNone(self.process.poll())

    def test_unhealthy_codec_or_missing_source_never_spawns(self):
        with patch.object(self.module,'probe_source',return_value={'duration':30.0,'video_codec':'hevc','audio_codec':'aac'}):
            result=self.start()
        self.assertEqual(result['status'],'error');self.assertIsNone(self.process)

    def test_secret_and_full_output_url_are_never_in_status_or_errors(self):
        self.start();text=repr(self.manager.status())
        self.assertNotIn('fixture-key-only',text);self.assertNotIn('rtmps://',text)

    def test_old_session_progress_and_reader_error_cannot_mutate_new_session(self):
        old=SimpleNamespace(stdout=io.BytesIO(b'frame=999\n'))
        current=SimpleNamespace(pid=77,poll=lambda:None)
        manager=self.manager;manager._process=current;manager._session=2;manager._state='starting'
        manager._read_progress(old,1)
        self.assertEqual(manager.status()['status'],'starting');self.assertEqual(manager.status()['frames'],0)
        old.stdout=SimpleNamespace(readline=lambda n:(_ for _ in ()).throw(OSError('stale fixture')))
        manager._read_progress(old,1)
        self.assertIsNone(manager.status()['error_code'])

    def test_progress_cannot_promote_known_error_or_stopping_session(self):
        manager=self.manager;manager._session=1
        process=SimpleNamespace(pid=77,stdout=io.BytesIO(b'frame=999\n'),poll=lambda:None)
        manager._process=process;manager._state='error';manager._error='CLEANUP_UNCONFIRMED'
        manager._read_progress(process,1)
        self.assertEqual(manager.status()['status'],'error');self.assertEqual(manager.status()['frames'],0)
        manager._state='stopped';manager._error=None;manager._stop.set()
        process.stdout=io.BytesIO(b'frame=1000\n');manager._read_progress(process,1)
        self.assertEqual(manager.status()['status'],'stopped');self.assertEqual(manager.status()['frames'],0)

    def test_invalid_new_request_does_not_poison_existing_target(self):
        self.start();before=self.manager.status()
        result=self.manager.start(self.source,'rtmps://hostile.invalid/live2','fixture-key-only')
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(self.manager.status()['status'],before['status'])
        self.assertIsNone(self.manager.status()['error_code'])


if __name__=='__main__':unittest.main()
