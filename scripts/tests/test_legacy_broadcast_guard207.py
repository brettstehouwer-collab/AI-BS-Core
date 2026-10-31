"""Injected mutex/daemon fixtures only; never touches a live lease or stream."""
from __future__ import annotations
import ast
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

SOURCE=Path(__file__).resolve().parents[2]/'backend/aibs_broadcast_daemon.py'


class LegacyBroadcastGuardTests(unittest.TestCase):
    def guard(self,event,api):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='legacy_coordinator_guard'),None)
        self.assertIsNotNone(node,'Legacy dispatch must check the coordinator before effects')
        env={};exec(compile(ast.Module([node],type_ignores=[]),str(SOURCE),'exec'),env)
        with patch.dict(sys.modules,{'win32event':event,'win32api':api}):return env['legacy_coordinator_guard']()

    def test_active_or_unknown_owner_holds_before_credentials_capture_or_files(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        class PrivateEndpoints:
            def __iter__(self):raise AssertionError('Credentials accessed before guard')
        for code in ('COORDINATOR_ACTIVE','OWNER_UNVERIFIED'):
            with self.subTest(code=code):
                daemon,ns,_,_=load_daemon();ns['legacy_coordinator_guard']=Mock(return_value=code)
                self.assertFalse(daemon.start_stream(PrivateEndpoints(),sources=[{'type':'screen','enabled':True}]))
                self.assertEqual(daemon.telemetry['capture_error_code'],code)
                ns['subprocess'].Popen.assert_not_called();ns['os'].makedirs.assert_not_called()
                ns['NativeWindowCapture'].assert_not_called();ns['threading'].Thread.assert_not_called()

    def test_modern_owner_bypasses_legacy_probe(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,ns,_,_=load_daemon();daemon._secondary_outputs=True;ns['os'].environ={}
        ns['legacy_coordinator_guard']=Mock(side_effect=AssertionError('Modern owner must not probe its own lease'))
        provider=SimpleNamespace(width=2,height=2,fps=30,start=Mock(),read_frame=Mock(return_value=b'\0'*16),stop=Mock(return_value=True))
        daemon._capture_provider_override=provider
        self.assertTrue(daemon.start_stream([],fps=30,resolution='2x2',sources=[{'type':'game','enabled':True,'capture_policy':'verified_game_follow'}]))
        ns['legacy_coordinator_guard'].assert_not_called()

    def test_busy_probe_never_releases_another_owner_and_free_probe_releases_own(self):
        for wait,expected,release in [(258,'COORDINATOR_ACTIVE',False),(0,None,True),(128,'OWNER_UNVERIFIED',True),(42,'OWNER_UNVERIFIED',False)]:
            with self.subTest(wait=wait):
                event=SimpleNamespace(OpenMutex=Mock(return_value=207),WaitForSingleObject=Mock(return_value=wait),ReleaseMutex=Mock())
                api=SimpleNamespace(CloseHandle=Mock())
                self.assertEqual(self.guard(event,api),expected)
                event.WaitForSingleObject.assert_called_once_with(207,0)
                self.assertEqual(event.ReleaseMutex.called,release);api.CloseHandle.assert_called_once_with(207)

    def test_missing_mutex_preserves_legacy_default_but_access_or_cleanup_errors_hold(self):
        for winerror,expected in [(2,None),(5,'OWNER_UNVERIFIED')]:
            with self.subTest(winerror=winerror):
                error=OSError('fixture');error.winerror=winerror
                event=SimpleNamespace(OpenMutex=Mock(side_effect=error),WaitForSingleObject=Mock(),ReleaseMutex=Mock())
                api=SimpleNamespace(CloseHandle=Mock())
                self.assertEqual(self.guard(event,api),expected);event.WaitForSingleObject.assert_not_called()
        event=SimpleNamespace(OpenMutex=Mock(return_value=207),WaitForSingleObject=Mock(return_value=0),ReleaseMutex=Mock(side_effect=OSError('fixture')))
        self.assertEqual(self.guard(event,SimpleNamespace(CloseHandle=Mock())),'OWNER_UNVERIFIED')

    def test_legacy_http_ack_reports_guard_hold_with_fixed_code(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start_stream_endpoint')
        node.decorator_list=[]
        request=SimpleNamespace(endpoints=[],game_name='Fixture',fps=30,resolution='1280x720',video_bitrate='4500k',
                                audio_bitrate='128k',encoder='h264_nvenc',preset='p4',format='hybrid_mp4',sources=[])
        for code in ('COORDINATOR_ACTIVE','OWNER_UNVERIFIED'):
            daemon=SimpleNamespace(start_stream=Mock(return_value=False),telemetry={'capture_error_code':code})
            env={'StreamStartRequest':object,'daemon':daemon}
            exec(compile(ast.Module([node],type_ignores=[]),str(SOURCE),'exec'),env)
            result=asyncio.run(env['start_stream_endpoint'](request))
            self.assertEqual(result['status'],'held');self.assertEqual(result['error_code'],code)
            self.assertFalse(result['process_running'])


if __name__=='__main__':unittest.main()
