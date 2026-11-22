"""One real owned-child/HTTP/Qt workflow, synthetic stores and auth channel only.

No production listener, credential lookup, provider or original document. The
fixed test child remaps its client origin to this ephemeral HTTP server. Listed
candidate pins are deliberately not a whole Python/DLL dependency attestation.
"""
import ast
from contextvars import ContextVar
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = Path(r'C:\Users\Administrator\Documents\Codex\2026-11-10\c-ai-bs')
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]

import httpx
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt
from scripts.tests import test_chat_pdf_workflow as pdf_fixture
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_adapter import NativeCreativeAdapter
from security.native_creative_controller import BOOTSTRAP_CONTRACT, NativeCreativeController, NativeControllerError, ReviewedCandidate, ReviewedFile
from security.native_creative_handoff import CreativeHandoffs, HandoffDenied
from security.native_creative_peer import NativePeerResolver
from security.screenwriting_access import require_screenwriting_access

PROJECT = 'Native Owned PDF Fixture'
OWNER = pdf_fixture.OWNER
MARKER = 'NATIVE OWNED FIXTURE EDIT'
SOURCE_FILES = ('original.pdf', 'source_packet.json', 'source_exports/layout.fdx', 'source_exports/layout.pdf')
HTTP_PATHS = frozenset({'/api/screenwriting/native/redeem', '/api/screenwriting/read',
    '/api/screenwriting/write', '/api/screenwriting/export/fdx', '/api/screenwriting/export/pdf'})
CHILD_STEPS = frozenset({'arguments', 'pipe_bootstrap_redeem', 'qt_initialization', 'initial_bound_read',
    'edit_and_save', 'fresh_process_reopen', 'explicit_reflow_export_fdx', 'explicit_reflow_export_pdf',
    'gui_close_and_drain'})


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(os.name == 'nt', 'Owned Windows process/pipe and Qt fixture')
class OwnedWorkflow(unittest.TestCase):
    def setUp(self):
        self.evidence = WORKSPACE / 'work' / ('native-owned-workflow-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        self.evidence.mkdir()
        self.results = []; self.records = []; self.connections = []
        self.auth_guards = []
        self.diagnostics = os.environ.get('AI_BS_NATIVE_WORKFLOW_DIAGNOSTICS') == '1'
        self.http_observations = []; self.denial_observations = []; self.diagnostic_errors = []
        self.adapter_observers = []; self.cleanup_outcomes = []
        self.http_observer_app = None; self.http_observer_type = None
        self.active_traces = 0; self.trace_restore_failed = False
        self.observation_lock = threading.Lock()
        self.request_context = ContextVar('owned_workflow_diagnostic_request', default=None)
        self.request_sequence = 0
        self.fixture = None; self.server = None; self.thread = None
        self.fixture_ready = False
        self.stage = 'setup'; self.failure = None
        self.addCleanup(self.cleanup)
        fixture = self.fixture = pdf_fixture.PdfWorkflowFixture()
        fixture._setupAsyncioRunner()
        # Preserve the fixture's existing short ROOT/t path. Long evidence-root
        # paths exceed Windows NamedTemporaryFile limits once cache hashes nest.
        fixture._callSetUp()
        self.fixture_ready = True
        self.assertEqual(fixture.root.resolve().parent, (ROOT / 't').resolve())
        self.assertTrue(fixture.root.name.startswith('pdf-workflow-'))
        self.source = fixture.stage()
        fixture.import_source(self.source, name=PROJECT)
        self.project = fixture.projects / PROJECT
        self.source_before = {name: digest(self.project / name) for name in SOURCE_FILES}
        self.namespace = fixture.router_scope()
        source = ROOT / 'backend/routers/screenwriting_router.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        ns = self.namespace
        ns.update(BaseModel=BaseModel, StrictInt=StrictInt, JSONResponse=JSONResponse)
        models = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'WriteScreenplayPayload']
        exec(compile(ast.Module(body=models, type_ignores=[]), '<actual write model>', 'exec'), ns)
        names = {'_native_creative_owner', '_screenwriting_owner_scope', 'redeem_native_creative',
                 '_issue_native_creative_grant', 'read_screenplay', 'write_screenplay', 'export_fdx', 'export_pdf'}
        definitions = [node for node in tree.body if getattr(node, 'name', '') in names]
        self.assertEqual(len(definitions), len(names))
        for node in definitions: node.decorator_list = []
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<actual owned workflow routes>', 'exec'), ns)
        router = APIRouter(dependencies=[Depends(require_screenwriting_access), Depends(ns['_screenwriting_owner_scope'])])
        for method, path, name in (
            ('POST', '/api/screenwriting/native/redeem', 'redeem_native_creative'),
            ('GET', '/api/screenwriting/read', 'read_screenplay'),
            ('POST', '/api/screenwriting/write', 'write_screenplay'),
            ('GET', '/api/screenwriting/export/fdx', 'export_fdx'),
            ('GET', '/api/screenwriting/export/pdf', 'export_pdf')):
            router.add_api_route(path, ns[name], methods=[method])
        app = FastAPI(); app.include_router(router)
        if self.diagnostics:
            self.install_http_observer(app)
        for guard in (
            patch('security.screenwriting_access.verify_admin_credentials',
                  side_effect=lambda key, bearer: key == 'synthetic-owned-workflow' and not bearer),
            patch('security.firebase_auth.get_admin_principal', return_value='local_admin')):
            guard.start(); self.auth_guards.append(guard)
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0)); self.listener.listen()
        self.port = self.listener.getsockname()[1]
        self.assertNotEqual(self.port, 8080)
        self.server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False,
            lifespan='off', proxy_headers=False, log_config=None))
        self.thread = threading.Thread(target=self.server.run, kwargs={'sockets': [self.listener]}, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 5
        while not self.server.started and self.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.server.started)
        self.grants = CreativeHandoffs()
        self.source_pins = {str(path.relative_to(ROOT)): digest(path) for path in self.pin_paths()}

    def observe(self, destination, value, limit=128):
        with self.observation_lock:
            if len(destination) < limit: destination.append(value)

    def install_http_observer(self, app):
        owner = self
        class DiagnosticHTTP:
            def __init__(self, app): self.app = app
            async def __call__(self, scope, receive, send):
                if scope['type'] != 'http':
                    return await self.app(scope, receive, send)
                with owner.observation_lock:
                    owner.request_sequence += 1
                    ordinal = owner.request_sequence
                observation = dict(phase=owner.stage, request=ordinal,
                    method=scope.get('method') if scope.get('method') in {'GET', 'POST'} else 'OTHER',
                    path=scope.get('path') if scope.get('path') in HTTP_PATHS else 'OTHER',
                    status=None, exception_class=None)
                token = owner.request_context.set((observation['phase'], ordinal))
                async def observed_send(message):
                    if message['type'] == 'http.response.start': observation['status'] = message['status']
                    await send(message)
                try:
                    return await self.app(scope, receive, observed_send)
                except BaseException as error:
                    observation['exception_class'] = type(error).__name__[:80]
                    raise
                finally:
                    owner.observe(owner.http_observations, observation, 64)
                    owner.request_context.reset(token)
        app.add_middleware(DiagnosticHTTP)
        self.http_observer_app, self.http_observer_type = app, DiagnosticHTTP

    def install_denial_observer(self, adapter, phase, method="redeem"):
        # Only the fixture's real redeem invocation installs a thread-local trace.
        # No global threading trace or replacement OS table reader is installed.
        import psutil
        targets = {
            NativePeerResolver._owner.__code__: 'peer._owner',
            NativePeerResolver.resolve.__code__: 'peer.resolve',
            CreativeHandoffs.redeem_with_details.__code__: 'handoff.redeem_with_details',
            NativeCreativeController.acknowledge_redeemed.__code__: 'controller.acknowledge_redeemed',
            NativeCreativeAdapter._peer_locked.__code__: 'adapter._peer_locked',
            NativeCreativeAdapter.redeem.__code__: 'adapter.redeem',
        }
        original = getattr(adapter, method)
        original_reader = psutil.net_connections
        owner_calls = {}; sample_sequence = [0]

        def trace(frame, event, argument):
            function = targets.get(frame.f_code)
            if function is None: return None
            try:
                if function == 'peer._owner' and event == 'call':
                    sample_sequence[0] += 1
                    owner_calls[id(frame)] = (sample_sequence[0], psutil.net_connections is original_reader)
                elif event == 'exception' and (argument[0] is HandoffDenied
                        or function == 'controller.acknowledge_redeemed' and argument[0] is NativeControllerError):
                    values = frame.f_locals
                    context = self.request_context.get()
                    item = dict(phase=phase, request=context[1] if context else None,
                        function=function, line=frame.f_lineno, exception_class=argument[0].__name__)
                    if argument[1].__context__ is not None:
                        item['context_exception_class'] = type(argument[1].__context__).__name__[:80]
                    # Explicit scalar allowlist only; never dump locals, rows or capabilities.
                    if function == 'peer._owner':
                        sample, reader_original = owner_calls.get(id(frame), (None, None))
                        item.update(sample=sample, reader_was_original_at_call=reader_original)
                        owned_pids = {record.pid for _, record in self.records}
                        ancestor = frame.f_back
                        if ancestor is not None and ancestor.f_code is NativePeerResolver.resolve.__code__:
                            owned_pids.update(invocation._pid for invocation in ancestor.f_locals.get('invocations', ()))
                        for key in ('clients', 'servers'):
                            observed = values.get(key)
                            if type(observed) is set:
                                item[key + '_count'] = len(observed)
                                item[key + '_owned_pids'] = sorted(pid for pid in observed if type(pid) is int and pid in owned_pids)
                                item[key + '_backend_present'] = os.getpid() in observed
                        rows = values.get('rows')
                        item['row_count'] = len(rows) if type(rows) in (list, tuple) else None
                        peer, endpoint = values.get('peer'), values['self'].endpoint
                        item['matching_endpoint_states'] = [dict(direction='client' if tuple(row.laddr)==peer else 'server', state=str(row.status)[:32], owned_pid=row.pid in owned_pids, backend_pid=row.pid==os.getpid()) for row in (rows or []) if (tuple(row.laddr)==peer and tuple(row.raddr)==endpoint) or (tuple(row.laddr)==endpoint and tuple(row.raddr)==peer)][:16]
                    elif function == 'peer.resolve':
                        invocations = values.get('invocations')
                        item['invocation_count'] = len(invocations) if type(invocations) in (list, tuple) else None
                        matches = values.get('matches')
                        item['match_count'] = len(matches) if type(matches) is list else None
                    elif function == 'handoff.redeem_with_details':
                        record = values.get('record')
                        item.update(record_found=record is not None,
                            invocation_matches=record is not None and record.invocation is values.get('invocation'),
                            grant_count=len(values['self']._grants), lease_count=len(values['self']._leases))
                    elif function == 'controller.acknowledge_redeemed':
                        record = values.get('record')
                        item['record_found'] = record is not None
                        if record is not None:
                            item.update(delivery_done=record._delivery.is_set(), delivery_ok=record._delivery_ok,
                                failed=record._failed, already_closed=record._result is not None,
                                acked=record._acked.is_set(), lifetime_acknowledged=record._lifetime.acknowledged,
                                drain_done=[drain.done.is_set() for drain in record._drains],
                                drain_failed=[drain.failed for drain in record._drains])
                    else:
                        item['registry_count'] = len(values['self']._invocations)
                        item['invocation_available'] = values.get('invocation') is not None
                        item['candidate_available'] = values.get('candidate') is not None
                    self.observe(self.denial_observations, item)
                elif event == 'return': owner_calls.pop(id(frame), None)
            except BaseException as error:
                # Observation failures must not alter the real authorization result.
                self.observe(self.diagnostic_errors, dict(function=function, exception_class=type(error).__name__), 16)
            return trace

        def observed_redeem(*args, **kwargs):
            previous = sys.gettrace()
            if previous is not None:
                self.observe(self.diagnostic_errors, dict(function='observer', exception_class='ExistingTraceNotReplaced'), 16)
                return original(*args, **kwargs)
            try: sys.settrace(trace)
            except BaseException as error:
                self.observe(self.diagnostic_errors, dict(function='observer.install', exception_class=type(error).__name__), 16)
                return original(*args, **kwargs)
            with self.observation_lock: self.active_traces += 1
            try: return original(*args, **kwargs)
            finally:
                try: sys.settrace(previous)
                except BaseException as error:
                    self.trace_restore_failed = True
                    self.observe(self.diagnostic_errors, dict(function='observer.restore', exception_class=type(error).__name__), 16)
                finally:
                    with self.observation_lock: self.active_traces -= 1
        setattr(adapter, method, observed_redeem)
        self.adapter_observers.append((adapter, method, original))

    def read_child_failure(self, directory, phase):
        """Read only a bounded regular metadata file in this exact owned tree."""
        import re
        path = directory / 'failure.json'
        try:
            if phase not in {'edit-save', 'reopen-export'} or directory != self.evidence / phase:
                raise ValueError()
            # Check every existing ancestor without following a junction/symlink.
            for parent in (path, *path.parents):
                info = parent.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ValueError()
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 8192: raise ValueError()
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                if ((opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                        or not 0 < opened.st_size <= 8192): raise ValueError()
                raw = stream.read(8193)
            if not 0 < len(raw) <= 8192: raise ValueError()
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result: raise ValueError()
                    result[key] = value
                return result
            value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
            required = {'kind', 'phase', 'step', 'exception_class', 'location'}
            if (type(value) is not dict or not required <= set(value) <= required | {'http_events'}
                    or value['kind'] != 'failure' or value['phase'] != phase or value['step'] not in CHILD_STEPS
                    or not isinstance(value['exception_class'], str)
                    or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}', value['exception_class'])): raise ValueError()
            location = value['location']
            if location is not None and (type(location) is not dict or set(location) != {'file', 'line'}
                    or not isinstance(location['file'], str) or not re.fullmatch(r'[A-Za-z_0-9.-]{1,128}', location['file'])
                    or type(location['line']) is not int or not 0 < location['line'] <= 1000000): raise ValueError()
            events = value.get('http_events', [])
            if type(events) is not list or len(events) > 64: raise ValueError()
            for event in events:
                if (type(event) is not dict or set(event) != {'path', 'status', 'exception_class'}
                        or event['path'] not in HTTP_PATHS | {'OTHER'}
                        or event['status'] is not None and (type(event['status']) is not int or not 100 <= event['status'] <= 599)
                        or event['exception_class'] is not None and (not isinstance(event['exception_class'], str)
                            or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}', event['exception_class']))): raise ValueError()
            return value
        except (OSError, ValueError, TypeError, UnicodeError):
            return dict(kind='failure', phase=phase, classification='child_failure_metadata_unavailable_or_invalid')

    def pin_paths(self):
        return [ROOT / name for name in (
            'scripts/tests/fixtures/native_creative_owned_child.py',
            'native_studio/creative_session.py', 'native_studio/native_creative_entry.py',
            'native_studio/screenwriting_view.py', 'native_studio/screenplay_client.py',
            'native_studio/rich_screenplay_draft.py', 'native_studio/local_connection.py',
            'native_studio/engine.py', 'native_studio/theme.py',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/__init__.py',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/QtCore.pyd',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/QtGui.pyd',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/QtWidgets.pyd',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin/Qt6Core.dll',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin/Qt6Gui.dll',
            'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin/Qt6Widgets.dll')]

    def receive(self, connection, record, seconds=35):
        connection.settimeout(.1); raw = bytearray(); deadline = time.monotonic() + seconds
        while b'\n' not in raw:
            if time.monotonic() >= deadline: raise TimeoutError('Synthetic phase deadline')
            try: block = connection.recv(8192 - len(raw))
            except socket.timeout:
                if record._lifetime.process.poll() is not None: raise AssertionError('Owned child exited before metadata')
                continue
            if not block or len(raw) + len(block) >= 8192: raise AssertionError('Invalid coordination frame')
            raw.extend(block)
        return json.loads(bytes(raw).split(b'\n', 1)[0])

    def run_phase(self, phase):
        self.stage = phase
        directory = self.evidence / phase; directory.mkdir()
        coordination = socket.socket(); coordination.bind(('127.0.0.1', 0)); coordination.listen(); coordination.settimeout(.1)
        self.addCleanup(coordination.close)
        candidate = ReviewedCandidate(ReviewedFile(str(Path(sys._base_executable)), digest(sys._base_executable)),
            ('-I', '-B', str(ROOT / 'scripts/tests/fixtures/native_creative_owned_child.py'), phase,
             str(self.port), str(coordination.getsockname()[1]), str(directory))
            + (('--diagnostics',) if self.diagnostics else ()),
            str(directory), (('SYSTEMROOT', os.environ['SYSTEMROOT']), ('TEMP', str(directory)),
                             ('TMP', str(directory)), ('PYTHONDONTWRITEBYTECODE', '1'),
                             ('PATH', str(ROOT / 'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin')
                              + os.pathsep + str(Path(os.environ['SYSTEMROOT']) / 'System32'))),
            tuple(ReviewedFile(str(path), digest(path)) for path in self.pin_paths()), BOOTSTRAP_CONTRACT)
        controller = NativeCreativeController.create(candidate, self.grants,
            self.namespace['_issue_native_creative_grant'], peer_resolver=NativePeerResolver(endpoint=('127.0.0.1', self.port)))
        if self.diagnostics:
            self.install_denial_observer(controller.adapter, phase)
            self.install_denial_observer(controller.adapter, phase, "resolve")
        self.namespace['_NATIVE_CREATIVE_ADAPTER'] = controller.adapter
        revision = self.namespace['_screenplay_snapshot'](self.project)['revision']
        # This waits once for the known issuance bound, never retries a launch.
        ready_at = self.grants._issued.get(OWNER, 0) + 1
        if ready_at > time.monotonic(): threading.Event().wait(min(1, ready_at - time.monotonic()))
        record = controller.launch(VerifiedFirebaseContext(OWNER, time.monotonic() + 240),
            project=PROJECT, revision=revision, source_sha256=self.source['source_sha256'])
        self.records.append((controller, record))
        deadline = time.monotonic() + 20
        while True:
            try: connection, _ = coordination.accept(); break
            except socket.timeout:
                code = record._lifetime.process.poll()
                if code is not None:
                    self.failure = self.read_child_failure(directory, phase)
                    self.failure.update(owned_exit_code=code, acknowledged=record.acknowledged)
                    raise AssertionError('Owned child did not reach acknowledged coordination')
                if time.monotonic() >= deadline:
                    self.failure = dict(kind='failure', phase=phase, classification='precoord_deadline',
                                        owned_exit_code=None, acknowledged=record.acknowledged)
                    raise AssertionError('Owned child did not reach acknowledged coordination')
        self.connections.append(connection)
        ready = self.receive(connection, record)
        self.assertEqual(ready.get('kind'), 'ready')
        self.assertEqual(ready.get('pid'), record.pid)
        self.assertTrue(ready['bootstrap_before_qt'])
        self.assertTrue(record.acknowledged)
        self.assertTrue(record._acked.is_set())
        self.assertFalse(record._lifetime._query_limits().BasicLimitInformation.LimitFlags & 0x2000)
        self.assertTrue(all(drain.done.is_set() and drain.bytes_discarded == 0 for drain in record._drains))
        connection.sendall(b'R')
        result = self.receive(connection, record)
        if result.get('kind') != 'complete':
            self.failure = result
            raise AssertionError('Owned child failed: ' + result.get('step', 'unknown') + '/' + result.get('exception_class', 'unknown'))
        self.assertEqual(result['pid'], record.pid)
        self.assertTrue(result['actual_rich_writer'] and result['only_writing_page'])
        self.assertTrue(result['gui_worker_drained'] and result['session_cleared_after_close'])
        self.assertEqual(result['forbidden_modules_loaded'], [])
        self.assertTrue(all(path in {'/api/screenwriting/native/redeem', '/api/screenwriting/read',
            '/api/screenwriting/write', '/api/screenwriting/export/fdx', '/api/screenwriting/export/pdf'} for path in result['request_paths']))
        self.assertEqual({name: digest(self.project / name) for name in SOURCE_FILES}, self.source_before)
        connection.sendall(b'X')
        deadline = time.monotonic() + 10
        while record._lifetime.process.poll() is None and time.monotonic() < deadline: time.sleep(.01)
        code = record._lifetime.process.poll(); self.assertEqual(code, 0)
        closed = controller.close(record)
        self.assertTrue(closed.acknowledged); self.assertFalse(closed.termination_requested)
        self.assertIsNone(closed.job_drained)  # Released editor is not mislabeled a worker-drain proof.
        self.assertIsNone(record._lifetime.process.hp); self.assertIsNone(record._lifetime.process.job)
        self.assertEqual(record._pins.handles, [])
        self.assertFalse(controller.cleanup_failed)
        result.update(exit_code=code, acknowledged_before_gui=True, controller_released_without_termination=True,
                      listed_candidate_sha256=candidate.sha256, listed_files_only=True)
        self.results.append(result)
        return result

    def test_real_owned_pdf_writer_save_fresh_reopen_and_reflow_exports(self):
        try:
            with httpx.Client(trust_env=False, timeout=3) as client:
                response = client.get(f'http://127.0.0.1:{self.port}/api/screenwriting/read', params={'project_name': PROJECT})
                self.assertEqual(response.status_code, 403)
            first = self.run_phase('edit-save')
            self.assertTrue(first['saved_edit_present'])
            self.assertIn(MARKER, (self.project / 'screenplay.fountain').read_text(encoding='utf-8'))
            second = self.run_phase('reopen-export')
            self.assertNotEqual(first['pid'], second['pid'])
            self.assertTrue(second['reopened_edit_present'])
            self.assertEqual(set(second['exports']), {'fdx', 'pdf'})
            self.assertTrue(all(value['edit_present'] for value in second['exports'].values()))
            self.assertEqual({name: digest(self.project / name) for name in SOURCE_FILES}, self.source_before)
            self.assertTrue(all(digest(ROOT / name) == value for name, value in self.source_pins.items()))
            self.stage = 'complete'
        except BaseException:
            if self.failure is None: self.failure = dict(stage=self.stage, classification='parent_fixture_failure')
            raise

    def cleanup(self):
        cleanup_errors = []
        for connection in self.connections:
            try: connection.sendall(b'X'); connection.close()
            except OSError: pass
        for controller, record in self.records:
            outcome = dict(owned_pid=record.pid, acknowledged=record.acknowledged,
                pre_close_poll_available=False, pre_close_exit_code=None,
                termination_requested=None, job_drained=None, exception_class=None)
            try:
                process = record._lifetime.process
                outcome['pre_close_poll_available'] = process.hp is not None
                outcome['pre_close_exit_code'] = process.poll() if process.hp is not None else None
                if record._result is None and record.acknowledged and outcome['pre_close_exit_code'] is None:
                    # Exact synthetic fixture handle only, never a PID/broad kill.
                    import _winapi
                    _winapi.TerminateProcess(process.hp, 99)
                    _winapi.WaitForSingleObject(process.hp, 5000)
                closed = controller.close(record)
                outcome.update(termination_requested=closed.termination_requested, job_drained=closed.job_drained)
            except BaseException as error:
                outcome['exception_class'] = type(error).__name__
                cleanup_errors.append(type(error).__name__)
            finally:
                outcome.update(process_handle_empty=record._lifetime.process.hp is None,
                    job_handle_empty=record._lifetime.process.job is None,
                    pin_handles_empty=record._pins.handles == [], controller_cleanup_failed=controller.cleanup_failed)
                self.cleanup_outcomes.append(outcome)
        if self.server is not None: self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)
            if self.thread.is_alive(): cleanup_errors.append('ServerThreadNotJoined')
        if hasattr(self, 'listener'):
            try: self.listener.close()
            except OSError: pass
        for adapter, method, original in reversed(self.adapter_observers): setattr(adapter, method, original)
        if self.http_observer_app is not None:
            self.http_observer_app.user_middleware = [entry for entry in self.http_observer_app.user_middleware
                if entry.cls is not self.http_observer_type]
            self.http_observer_app.middleware_stack = None
        for guard in reversed(self.auth_guards): guard.stop()
        if self.fixture is not None:
            try:
                if self.fixture_ready: self.fixture._callTearDown()
                self.fixture.doCleanups()
            except BaseException as error: cleanup_errors.append(type(error).__name__)
            finally: self.fixture._tearDownAsyncioRunner()
        receipt = dict(schema='aibs.native-owned-workflow.v1', stage=self.stage,
            status='PASS_SYNTHETIC_OWNED_HTTP_QT' if self.stage == 'complete' and not cleanup_errors else 'FAILED_RETAINED',
            phases=self.results, failure=self.failure, cleanup_errors=cleanup_errors,
            owned_cleanup_outcomes=self.cleanup_outcomes,
            four_original_source_artifact_pins=getattr(self, 'source_before', {}),
            listed_source_pins=getattr(self, 'source_pins', {}),
            test_harness_sha256=digest(__file__), synthetic_auth_not_production=True,
            whole_dependency_closure_qualified=False, production_8080_connections=False,
            production_services_or_originals_or_models_touched=False)
        if self.diagnostics:
            receipt['diagnostics'] = dict(enabled=True, http=self.http_observations,
                denials=self.denial_observations, observer_errors=self.diagnostic_errors,
                observer_restored=(self.active_traces == 0 and not self.trace_restore_failed
                    and all(getattr(adapter, method) == original for adapter, method, original in self.adapter_observers)
                    and (self.http_observer_app is None or not any(entry.cls is self.http_observer_type
                        for entry in self.http_observer_app.user_middleware))),
                extra_os_table_samples=0,
                limits='Fixed paths/status/classes and approved-frame scalar fields only; tracing perturbs timing; no bodies/headers/capabilities')
        with (self.evidence / 'result.json').open('x', encoding='utf-8') as stream: json.dump(receipt, stream, indent=2)
        print('Owned workflow evidence: ' + str(self.evidence / 'result.json'), flush=True)
        self.assertEqual(cleanup_errors, [])


if __name__ == '__main__': unittest.main(verbosity=2)
