"""Synthetic source-only Windows candidates; no HTTP, SDK verification or originals.

The fixed fixture invokes the real bootstrap reader/output-silencing helper. Its
loopback socket is test coordination, not the production peer resolver or routes.
All contexts/grants are synthetic and remain in memory; no provider calls occur.
"""
import ctypes
import concurrent.futures
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys
import sysconfig
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_adapter import NativeCreativeAdapter
from security.native_creative_controller import (BOOTSTRAP_CONTRACT, NativeControllerError,
    NativeCreativeController, ReviewedCandidate, ReviewedFile)
from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied
from security.native_creative_peer import NativePeerResolver

if os.name == 'nt':
    import _winapi


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(os.name == 'nt', 'Windows file shares and owned jobs')
class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aibs-native-controller-')
        self.directory = Path(self.temp.name).resolve()
        # Explicitly constrain the later recursive TemporaryDirectory cleanup.
        self.assertEqual(self.directory.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.directory.name.startswith('aibs-native-controller-'))
        self.addCleanup(self.temp.cleanup)
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0)); self.listener.listen(); self.listener.settimeout(5)
        self.addCleanup(self.listener.close)
        self.records = []; self.connections = []; self.controllers = []
        self.fixture_handles = {}
        self.addCleanup(self.cleanup_owned)
        self.grants = CreativeHandoffs()
        def acknowledged(invocation, lease):
            owners = [controller for controller in self.controllers if invocation in controller._records]
            self.assertEqual(len(owners), 1)
            return owners[0].acknowledge_redeemed(invocation, lease)
        self.adapter = NativeCreativeAdapter(self.grants, on_redeemed=acknowledged)
        self.sequence = 0
        self.preflight_calls = []
        self.script = self.directory/'reviewed_fixture.py'
        self.script.write_text('''
import json,os,socket,struct,sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from native_studio.creative_session import read_bootstrap_pipe,silence_native_bootstrap_output
if sys.argv[4]=='flood':
    for _ in range(8):os.write(1,b'O'*16384);os.write(2,b'E'*16384)
if sys.argv[4]!='unsilenced':silence_native_bootstrap_output()
packet=read_bootstrap_pipe(sys.stdin.buffer)
value=dict(grant=packet.grant,project=packet.project,revision=packet.revision,source_sha256=packet.source_sha256,candidate_sha256=packet.candidate_sha256)
s=socket.create_connection(('127.0.0.1',int(sys.argv[3])));s.settimeout(20)
raw=json.dumps(value).encode();s.sendall(struct.pack('<I',len(raw))+raw)
s.recv(1);s.close()
''', encoding='utf-8')

    def cleanup_owned(self):
        for connection in self.connections:
            connection.close()  # Exact acknowledged fixtures exit on EOF.
        for controller in self.controllers:
            for record in tuple(controller._records.values()):
                result = controller.close(record)
                if result.job_drained is not None:
                    self.assertTrue(result.job_drained)
        for record in self.records:
            handle = self.fixture_handles.get(record)
            if handle is not None:
                try:
                    completed = _winapi.WaitForSingleObject(handle, 3000) == 0
                    if not completed:
                        # Only the exact retained synthetic fixture process.
                        _winapi.TerminateProcess(handle, 98)
                        _winapi.WaitForSingleObject(handle, 3000)
                    self.assertTrue(completed, 'Surviving fixture did not exit on EOF')
                finally:
                    _winapi.CloseHandle(handle)
            self.assertFalse(record.invocation.alive())
            self.assertTrue(record._lifetime.closed)
            for worker in (record._writer, *(d.thread for d in record._drains)):
                if worker is not None:
                    self.assertFalse(worker.is_alive(), 'Owned fixture IO thread remains')

    def candidate(self, mode='normal'):
        return ReviewedCandidate(
            ReviewedFile(str(Path(sys._base_executable)), digest(sys._base_executable)),
            ('-I', str(self.script), str(ROOT), sysconfig.get_path('purelib'),
             str(self.listener.getsockname()[1]), mode),
            str(self.directory), (('SYSTEMROOT', os.environ['SYSTEMROOT']),
                ('TEMP', str(self.directory)), ('TMP', str(self.directory))),
            (ReviewedFile(str(self.script), digest(self.script)),
             ReviewedFile(str(ROOT/'native_studio/creative_session.py'), digest(ROOT/'native_studio/creative_session.py'))),
            BOOTSTRAP_CONTRACT)

    def preflight(self, context, invocation, candidate, *, project_name,
                  expected_revision, expected_source_sha256, grants):
        self.assertIs(grants, self.grants)
        self.assertIn(invocation, self.adapter._invocations)
        self.assertTrue(invocation.alive())
        self.preflight_calls.append(invocation)
        return grants.issue_verified(CreativeScope(context.principal, project_name,
            expected_revision, expected_source_sha256, candidate), invocation, context)

    def controller(self, candidate=None, preflight=None, **kwargs):
        controller = NativeCreativeController(candidate or self.candidate(), self.grants,
            self.adapter, preflight or self.preflight, **kwargs)
        self.controllers.append(controller)
        return controller

    def context(self):
        self.sequence += 1
        return VerifiedFirebaseContext('firebase:fixture:synthetic-'+str(self.sequence), time.monotonic()+60)

    def launch(self, controller):
        record = controller.launch(self.context(), project='synthetic-project',
            revision='synthetic-revision', source_sha256='b'*64)
        self.records.append(record)
        current = _winapi.GetCurrentProcess()
        self.fixture_handles[record] = _winapi.DuplicateHandle(current,
            record._lifetime.process.hp, current, 0, False, _winapi.DUPLICATE_SAME_ACCESS)
        return record

    def packet(self):
        connection, address = self.listener.accept(); connection.settimeout(5)
        self.last_address = address
        self.connections.append(connection)
        def read_exact(count):
            raw = bytearray()
            while len(raw) < count:
                part = connection.recv(count-len(raw))
                self.assertTrue(part)
                raw.extend(part)
            return bytes(raw)
        count = struct.unpack('<I', read_exact(4))[0]
        self.assertLessEqual(count, 4096)
        return json.loads(read_exact(count)), connection

    def retain(self, record):
        current = _winapi.GetCurrentProcess()
        handle = _winapi.DuplicateHandle(current, record._lifetime.process.hp,
            current, 0, False, _winapi.DUPLICATE_SAME_ACCESS)
        self.addCleanup(_winapi.CloseHandle, handle)
        return handle

    def test_real_pipe_packet_registered_before_issue_and_secret_not_in_argv(self):
        controller = self.controller()
        lengths = []
        deliver = controller._deliver
        def observed(record, packet):
            lengths.append(len(packet)); return deliver(record, packet)
        with patch.object(controller, '_deliver', side_effect=observed):
            record = self.launch(controller)
        packet, connection = self.packet()
        self.assertEqual(self.preflight_calls, [record.invocation])
        self.assertEqual(packet['project'], 'synthetic-project')
        self.assertEqual(packet['candidate_sha256'], controller.candidate.sha256)
        self.assertTrue(0 < lengths[0] <= 4096)
        self.assertTrue(record._lifetime.process.stdin.closed)
        import psutil
        self.assertNotIn(packet['grant'], ' '.join(psutil.Process(record.pid).cmdline()))
        self.assertNotIn(packet['grant'], repr(controller.candidate.environment))
        self.assertNotIn(packet['grant'], repr(record))

    def test_redeemed_exact_scope_ack_releases_surviving_child(self):
        controller = self.controller()
        record = self.launch(controller); handle = self.retain(record)
        packet, connection = self.packet()
        lease = self.grants.redeem(packet['grant'], record.invocation)
        controller.acknowledge_redeemed(record.invocation, lease)
        self.assertTrue(record.acknowledged)
        result = controller.close(record)
        self.assertTrue(result.acknowledged); self.assertFalse(result.termination_requested)
        self.assertIsNone(result.job_drained)
        self.assertEqual(_winapi.WaitForSingleObject(handle, 0), 258)
        self.assertNotIn(record.invocation, self.adapter._invocations)
        with self.assertRaises(HandoffDenied):
            self.grants.authorize(lease, record.invocation, project='synthetic-project', operation='read')
        connection.sendall(b'X')
        self.assertEqual(_winapi.WaitForSingleObject(handle, 3000), 0)
        self.assertEqual(_winapi.GetExitCodeProcess(handle), 0)
        self.assertIs(controller.close(record), result)

    def test_factory_actual_owned_tcp_registry_hook_acknowledges_before_response(self):
        resolver = NativePeerResolver(endpoint=self.listener.getsockname())
        controller = NativeCreativeController.create(self.candidate(), self.grants,
            self.preflight, peer_resolver=resolver)
        self.controllers.append(controller); self.adapter = controller.adapter
        record = self.launch(controller); packet, connection = self.packet()
        scope = dict(type='http', client=self.last_address,
            server=self.listener.getsockname(), headers=[])
        # Actual Windows client/reverse-server TCP ownership; synthetic ASGI
        # scope only. This is not a mounted HTTP route/candidate GUI proof.
        import psutil
        observe = psutil.net_connections
        observations = []
        def observed(**kwargs):
            try:
                rows = observe(**kwargs)
                observations.append({'rows':[
                    dict(pid=row.pid, local=list(row.laddr), remote=list(row.raddr), status=row.status)
                    for row in rows if tuple(row.laddr) in (scope['client'], scope['server'])
                    or tuple(row.raddr) in (scope['client'], scope['server'])]})
                return rows
            except (OSError, psutil.Error) as error:
                observations.append(dict(error=type(error).__name__, winerror=getattr(error, 'winerror', None)))
                raise
        with patch('security.native_creative_peer.psutil.net_connections', side_effect=observed):
            try:
                result = self.adapter.redeem(scope, packet['grant'])
            except HandoffDenied:
                self.fail('Actual TCP ownership refused; exact endpoint metadata: '+json.dumps(observations))
        self.assertTrue(record.acknowledged)
        self.assertEqual(result['project'], 'synthetic-project')
        authorized = self.adapter.resolve(scope, result['lease'],
            project='synthetic-project', operation='read')
        self.assertEqual(authorized, record._expected)
        with self.assertRaises(HandoffDenied):
            self.adapter.redeem(scope, packet['grant'])

    def test_ack_requires_redeemed_lease_and_exact_owned_invocation(self):
        controller = self.controller(); record = self.launch(controller)
        packet, connection = self.packet()
        with self.assertRaises(NativeControllerError):
            controller.acknowledge_redeemed(record.invocation, packet['grant'])
        lease = self.grants.redeem(packet['grant'], record.invocation)
        with self.assertRaises(NativeControllerError):
            controller.acknowledge_redeemed(object(), lease)
        self.assertFalse(record.acknowledged)
        controller.acknowledge_redeemed(record.invocation, lease)

    def test_wrong_scope_lease_cannot_acknowledge(self):
        controller = self.controller()
        def other_scope(context, invocation, candidate, **kwargs):
            self.assertIn(invocation, self.adapter._invocations)
            return self.grants.issue_verified(CreativeScope(context.principal, 'different-project',
                kwargs['expected_revision'], kwargs['expected_source_sha256'], candidate), invocation, context)
        controller._preflight = other_scope
        record = self.launch(controller); packet, connection = self.packet()
        lease = self.grants.redeem(packet['grant'], record.invocation)
        with self.assertRaises(NativeControllerError):
            controller.acknowledge_redeemed(record.invocation, lease)
        self.assertFalse(record.acknowledged)

    def test_inherited_output_must_be_closed_before_ack(self):
        controller = self.controller(self.candidate('unsilenced'))
        record = self.launch(controller); packet, connection = self.packet()
        lease = self.grants.redeem(packet['grant'], record.invocation)
        with patch('security.native_creative_controller.DELIVERY_SECONDS', .1):
            with self.assertRaises(NativeControllerError):
                controller.acknowledge_redeemed(record.invocation, lease)
        self.assertFalse(record.acknowledged)
        self.assertTrue(controller.close(record).job_drained)

    def test_output_flood_is_discarded_and_actual_child_sinks_reach_eof(self):
        controller = self.controller(self.candidate('flood'))
        record = self.launch(controller); packet, connection = self.packet()
        lease = self.grants.redeem(packet['grant'], record.invocation)
        controller.acknowledge_redeemed(record.invocation, lease)
        for drain in record._drains:
            self.assertTrue(drain.done.is_set()); self.assertFalse(drain.failed)
            self.assertEqual(drain.bytes_discarded, 131072)
            self.assertNotIn('blocks', drain.__dict__)

    def test_listed_files_and_parent_path_stay_no_write_no_delete_pinned(self):
        controller = self.controller(); record = self.launch(controller)
        self.packet()
        with self.assertRaises(OSError):
            self.script.write_text('replacement', encoding='utf-8')
        with self.assertRaises(OSError):
            self.script.unlink()
        with self.assertRaises(OSError):
            self.directory.rename(self.directory.with_name(self.directory.name+'-moved'))
        controller.close(record)
        self.script.write_text('replacement after release', encoding='utf-8')

    def test_hash_mismatch_and_existing_writer_refuse_before_launch(self):
        candidate = self.candidate()
        bad = dataclasses.replace(candidate, executable=ReviewedFile(candidate.executable.path, 'f'*64))
        for spec in (bad, candidate):
            controller = self.controller(spec)
            writer = self.script.open('r+b') if spec is candidate else None
            try:
                with patch('security.native_creative_controller.NativeCreativeLifetime') as launch:
                    with self.assertRaises(NativeControllerError):
                        self.launch(controller)
                    launch.assert_not_called()
            finally:
                if writer: writer.close()
            self.assertEqual(controller._pending, 0)
            self.assertEqual(controller._records, {})
        # Failed pin attempts have released their own read/ancestor handles.
        self.script.write_text('released after failed pins', encoding='utf-8')

    def test_preflight_error_aborts_owned_launch_and_is_sanitized(self):
        handles = []
        def fail(context, invocation, candidate, **kwargs):
            current = _winapi.GetCurrentProcess()
            handle = _winapi.DuplicateHandle(current, invocation._process.hp, current,
                0, False, _winapi.DUPLICATE_SAME_ACCESS)
            handles.append(handle); self.addCleanup(_winapi.CloseHandle, handle)
            raise RuntimeError('synthetic-private-marker-that-must-not-escape')
        controller = self.controller(preflight=fail)
        with self.assertRaises(NativeControllerError) as error:
            self.launch(controller)
        self.assertNotIn('synthetic-private-marker', str(error.exception))
        self.assertEqual(_winapi.WaitForSingleObject(handles[0], 0), 0)
        self.assertEqual(controller._records, {})
        self.assertEqual(self.adapter._invocations, {})
        self.script.write_text('pins released', encoding='utf-8')

    def test_unpublished_cleanup_attempts_both_resources_and_keeps_failures_bounded(self):
        controller = self.controller()
        pins = MagicMock(); life = MagicMock()
        life.close.side_effect = RuntimeError('synthetic-private-cleanup-marker')
        with patch('security.native_creative_controller._PinnedFiles', return_value=pins), \
             patch('security.native_creative_controller.NativeCreativeLifetime', return_value=life), \
             patch('security.native_creative_controller._Drain', side_effect=RuntimeError('Synthetic thread start failure')):
            with self.assertRaises(NativeControllerError) as error:
                self.launch(controller)
        self.assertNotIn('synthetic-private', str(error.exception))
        life.close.assert_called_once(); pins.close.assert_called_once()
        self.assertTrue(controller.cleanup_failed)
        self.assertEqual(len(controller._retained_cleanup), 1)
        self.assertEqual(controller._pending, 0)
        life.close.side_effect = None
        controller.prune()
        self.assertEqual(controller._retained_cleanup, {})
        self.assertTrue(controller.cleanup_failed)  # Historical failure stays true.

    def test_concurrent_close_before_preflight_issue_revokes_late_grant(self):
        entered = threading.Event(); proceed = threading.Event(); observed = []
        def blocked(context, invocation, candidate, **kwargs):
            record = controller._records[invocation]
            self.records.append(record)
            current = _winapi.GetCurrentProcess()
            self.fixture_handles[record] = _winapi.DuplicateHandle(current,
                record._lifetime.process.hp, current, 0, False, _winapi.DUPLICATE_SAME_ACCESS)
            observed.append(record); entered.set()
            if not proceed.wait(5): raise RuntimeError('Synthetic preflight wait expired')
            return self.preflight_late(context, invocation, candidate, **kwargs)
        controller = self.controller(preflight=blocked)
        errors = []
        def start():
            try: self.launch(controller)
            except NativeControllerError: errors.append(True)
        thread = threading.Thread(target=start, name='synthetic-blocked-preflight')
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertTrue(controller.close(observed[0]).job_drained)
        finally:
            proceed.set(); thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [True])
        self.assertEqual(self.grants._grants, {})
        self.assertEqual(controller._records, {})
        self.assertEqual(controller._pending, 0)

    def test_concurrent_unpublished_retry_serializes_resource_close(self):
        controller = self.controller()
        life = MagicMock(); pins = MagicMock()
        life.close.return_value.job_drained = True
        controller._retained_cleanup[(id(life), id(pins))] = (life, pins)
        barrier = threading.Barrier(2)
        counter_lock = threading.Lock(); counts = dict(active=0, maximum=0)
        def pin_close():
            with counter_lock:
                counts['active'] += 1
                counts['maximum'] = max(counts['maximum'], counts['active'])
            time.sleep(.02)
            with counter_lock:
                counts['active'] -= 1
        pins.close.side_effect = pin_close
        retry = controller._close_unpublished
        def synchronized_snapshot(lifetime, resources):
            barrier.wait(timeout=3)  # Both prune calls already took snapshots.
            return retry(lifetime, resources)
        with patch.object(controller, '_close_unpublished', side_effect=synchronized_snapshot):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = [pool.submit(controller.prune) for _ in range(2)]
                for result in results:
                    result.result(timeout=5)
        self.assertEqual(counts['maximum'], 1)
        self.assertEqual(controller._retained_cleanup, {})

    def preflight_late(self, context, invocation, candidate, **kwargs):
        # Store issue is intentionally allowed after the exact invocation was
        # closed, to exercise the controller's post-preflight cleanup race.
        return self.grants.issue_verified(CreativeScope(context.principal, kwargs['project_name'],
            kwargs['expected_revision'], kwargs['expected_source_sha256'], candidate), invocation, context)

    def test_failed_delivery_aborts_exact_job_and_revokes_pending_grant(self):
        controller = self.controller()
        def fail_delivery(record, packet):
            self.records.append(record)
            record._delivery_ok = False; record._delivery.set()
        with patch.object(controller, '_deliver', side_effect=fail_delivery):
            with self.assertRaises(NativeControllerError):
                self.launch(controller)
        self.assertEqual(self.adapter._invocations, {})
        self.assertEqual(self.grants._grants, {})
        self.assertTrue(self.records[0]._result.job_drained)

    def test_expired_context_and_capacity_do_not_start_another_process(self):
        controller = self.controller(capacity=1)
        expired = VerifiedFirebaseContext('firebase:fixture:expired', time.monotonic()-1)
        with patch('security.native_creative_controller.NativeCreativeLifetime') as launch:
            with self.assertRaises(NativeControllerError):
                controller.launch(expired, project='p', revision='r', source_sha256='b'*64)
            launch.assert_not_called()
        self.launch(controller); self.packet()
        with patch('security.native_creative_controller.NativeCreativeLifetime') as launch:
            with self.assertRaises(NativeControllerError):
                self.launch(controller)
            launch.assert_not_called()

    def test_unacknowledged_deadline_drains_without_user_interaction(self):
        controller = self.controller()
        with patch('security.native_creative_controller.ACK_SECONDS', .1):
            record = self.launch(controller)
            # This deliberately short test deadline may precede fixture imports
            # and TCP coordination. The owned job's close is the actual gate.
            self.assertTrue(record._acked.wait(3))
        self.assertFalse(record.acknowledged)
        self.assertTrue(record._result.job_drained)

    def test_fixed_spec_is_immutable_and_rejects_credentials_or_unknown_contract(self):
        candidate = self.candidate()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            candidate.arguments = ('caller-override',)
        for changes in ({'environment':(('AI_BS_ADMIN_KEY', 'synthetic-not-a-secret'),)},
                        {'contract':'unreviewed'}, {'arguments':['mutable']},
                        {'dependencies':(candidate.executable,)}):
            with self.assertRaises(ValueError):
                dataclasses.replace(candidate, **changes)
        self.assertNotEqual(candidate.sha256,
            dataclasses.replace(candidate, arguments=candidate.arguments+('--fixed-change',)).sha256)
        with self.assertRaises(ValueError):
            NativeCreativeController(candidate, self.grants, NativeCreativeAdapter(self.grants), self.preflight)


if __name__ == '__main__':
    unittest.main()
