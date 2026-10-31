"""AST-loaded broadcast behavior with injected process/filesystem stand-ins.

The daemon entrypoint, hardware probes, threads, cameras and network never run.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import types
import unittest
import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[2]/'backend/aibs_broadcast_daemon.py'


def load_daemon():
    parsed = ast.parse(SOURCE.read_text(encoding='utf-8'))
    selected = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in {'escape_tee_url', 'redact_broadcast_log', 'join_stream_destination'}:
            selected.append(node)
        if isinstance(node, ast.ClassDef) and node.name == 'BroadcastDaemon':
            node.body = [item for item in node.body if isinstance(item, ast.FunctionDef)
                         and item.name in {'start_stream', '_telemetry_reader', 'stop_stream'}]
            selected.append(node)
    process = Mock()
    process.poll.return_value = None
    process.wait.return_value = 0
    process.stdout = io.StringIO('')
    subprocess = types.SimpleNamespace(Popen=Mock(return_value=process), PIPE=-1, STDOUT=-2)
    log_file = Mock()
    opened = Mock()
    opened.__enter__ = Mock(return_value=log_file)
    opened.__exit__ = Mock(return_value=False)
    ns = {'List': List, 'Dict': Dict, 'Any': Any, 'Optional': Optional, 're': re,
          'subprocess': subprocess, 'time': types.SimpleNamespace(time=lambda: 1700000000, sleep=Mock()),
          'os': types.SimpleNamespace(path=types.SimpleNamespace(exists=lambda _: False), makedirs=Mock()),
          'logging': Mock(), 'threading': types.SimpleNamespace(Thread=Mock()),
          'build_encoder_flags': lambda *a, **k: [], 'detect_microphone': lambda: 'fixture microphone',
          'OBSOrchestrator': None, 'open': Mock(return_value=opened)}
    def capture_fixture(hwnd,pid,title,**kwargs):
        return types.SimpleNamespace(width=2,height=2,fps=kwargs.get('fps',30),
            start=Mock(return_value={'provider':'fixture_wgc','frame_available':True}),
            read_frame=Mock(return_value=b'\x01'*16),stop=Mock(return_value=True))
    ns['NativeWindowCapture']=Mock(side_effect=capture_fixture)
    ns['WindowCapturePipe']=Mock(side_effect=lambda *a,**k:types.SimpleNamespace(start=Mock(),stop=Mock(return_value=True)))
    exec(compile(ast.Module(selected, type_ignores=[]), str(SOURCE), 'exec'), ns)
    daemon = object.__new__(ns['BroadcastDaemon'])
    daemon.process = process
    daemon.is_streaming = False
    daemon.active_game = 'Desktop Screen 1'
    daemon.telemetry = {'endpoints': {}}
    return daemon, ns, process, log_file


class BroadcastDaemonIntegrityTests(unittest.TestCase):
    def test_unsafe_browser_origins_rejected_before_dispatch(self):
        parsed = ast.parse(SOURCE.read_text(encoding='utf-8'))
        guard = next((node for node in parsed.body if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == 'enforce_broadcast_origin'), None)
        self.assertIsNotNone(guard, 'Unsafe browser requests need an origin gate before dispatch')
        guard.decorator_list = []
        from starlette.responses import JSONResponse
        namespace = {'Request': object, 'JSONResponse': JSONResponse,
                     'BROADCAST_ALLOWED_ORIGINS': ('http://localhost:5173', 'https://ai-bs-dashboard.web.app')}
        exec(compile(ast.Module([guard], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        for origin in ['https://hostile.invalid', 'null', '', 'http://localhost:5173.hostile.invalid']:
            with self.subTest(origin=origin):
                called = []
                async def dispatch(request):
                    called.append(request)
                    return 'dispatched'
                request = types.SimpleNamespace(method='POST', headers={'origin': origin})
                response = asyncio.run(namespace['enforce_broadcast_origin'](request, dispatch))
                self.assertEqual(response.status_code, 403)
                self.assertFalse(called)

    def test_native_and_allowlisted_browser_requests_preserved(self):
        parsed = ast.parse(SOURCE.read_text(encoding='utf-8'))
        guard = next((node for node in parsed.body if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == 'enforce_broadcast_origin'), None)
        self.assertIsNotNone(guard)
        guard.decorator_list = []
        from starlette.responses import JSONResponse
        namespace = {'Request': object, 'JSONResponse': JSONResponse,
                     'BROADCAST_ALLOWED_ORIGINS': ('http://localhost:5173', 'https://ai-bs-dashboard.web.app')}
        exec(compile(ast.Module([guard], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        for headers in [{}, {'origin': 'http://localhost:5173'}, {'origin': 'https://ai-bs-dashboard.web.app'}]:
            async def dispatch(request):
                return 'dispatched'
            request = types.SimpleNamespace(method='POST', headers=headers)
            self.assertEqual(asyncio.run(namespace['enforce_broadcast_origin'](request, dispatch)), 'dispatched')

    def test_immediate_encoder_failure_never_acknowledged_as_running(self):
        daemon, ns, process, _ = load_daemon()
        process.poll.return_value = 1
        self.assertFalse(daemon.start_stream([], sources=[{'type': 'screen'}]))
        self.assertFalse(daemon.is_streaming)

    def test_endpoint_state_is_unverified_after_process_spawn(self):
        daemon, ns, process, _ = load_daemon()
        endpoints = [{'name': 'Fixture', 'url': 'rtmps://example.invalid/live/', 'key': '/fixture-stream-key'}]
        self.assertTrue(daemon.start_stream(endpoints, sources=[{'type': 'screen'}]))
        self.assertNotEqual(daemon.telemetry['endpoints']['Fixture'], 'STREAMING')
        self.assertFalse(daemon.telemetry.get('ingest_verified', True))

    def test_log_scrubs_raw_and_escaped_stream_urls_and_keys(self):
        daemon, ns, process, log = load_daemon()
        daemon.is_streaming = True
        daemon._stream_secrets = ('fixture-stream-key',)
        process.stdout = io.StringIO('Opening rtmps://example.invalid/live/fixture-stream-key\n'
                                    'Opening rtmps\\://example.invalid/live/fixture-stream-key\n'
                                    'Rejected key fixture-stream-key\n')
        daemon._telemetry_reader()
        written = ''.join(call.args[0] for call in log.write.call_args_list)
        self.assertNotIn('fixture-stream-key', written)
        self.assertNotIn('example.invalid', written)

    def test_stop_does_not_claim_archive_was_saved(self):
        daemon, ns, process, _ = load_daemon()
        daemon.is_streaming = True
        process.poll.return_value = 0
        result = daemon.stop_stream()
        self.assertEqual(result['status'], 'stopped')
        self.assertNotIn('archive saved', result['message'].lower())
        self.assertEqual(result.get('archive_verified'), False)

    def test_stop_failure_retains_handle_and_reports_failure(self):
        daemon, ns, process, _ = load_daemon()
        daemon.is_streaming = True
        process.wait.side_effect = TimeoutError('fixture timeout')
        process.kill.side_effect = OSError('fixture kill refused')
        result = daemon.stop_stream()
        self.assertEqual(result['status'], 'error')
        self.assertIs(daemon.process, process)

    def test_tee_destination_does_not_insert_duplicate_slash(self):
        daemon, ns, process, _ = load_daemon()
        endpoints = [{'name': 'Fixture', 'url': 'rtmps://example.invalid/live/', 'key': '/fixture-key'}]
        daemon.start_stream(endpoints, sources=[{'type': 'screen'}])
        command = ns['subprocess'].Popen.call_args.args[0]
        self.assertNotIn('live//fixture-key', command[-1])


if __name__ == '__main__':
    unittest.main()
