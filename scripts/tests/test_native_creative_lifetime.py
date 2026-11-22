"""Real Windows synthetic lifetimes only; no editor, document, provider or keys."""
import concurrent.futures
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import sysconfig
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.native_creative_lifetime import NativeCreativeLifetime, NativeLifetimeError
from security.native_creative_handoff import CreativeHandoffs, CreativeScope, HandoffDenied

if os.name == 'nt':
    import _winapi


def receive_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        block = connection.recv(size - len(data))
        if not block:
            raise AssertionError('Owned fixture connection ended early')
        data.extend(block)
    return bytes(data)


@unittest.skipUnless(os.name == 'nt', 'Windows owned jobs/handles required')
class LifetimeTests(unittest.TestCase):
    def retain(self, handle):
        current = _winapi.GetCurrentProcess()
        return _winapi.DuplicateHandle(current, handle, current, 0, False, _winapi.DUPLICATE_SAME_ACCESS)

    def alive(self, handle):
        return _winapi.WaitForSingleObject(handle, 0) == 258

    def spawn(self, revoker=None, *, descendant=False):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0)); listener.listen(); listener.settimeout(5)
        descendant_code = ('import subprocess,sys; p=subprocess.Popen([sys.executable,"-I","-c",'
            '"import time;time.sleep(20)"]); s.sendall(p.pid.to_bytes(4,"little"));') if descendant else ''
        code = ('import socket,sys; s=socket.create_connection(("127.0.0.1",int(sys.argv[1])));'
            's.settimeout(20);s.sendall(b"R");' + descendant_code + 's.recv(1);s.close()')
        calls = []
        if revoker is None:
            revoker = lambda invocation: calls.append(invocation)
        try:
            life = NativeCreativeLifetime([sys._base_executable, '-I', '-c', code,
                str(listener.getsockname()[1])], Path.cwd(), dict(os.environ),
                candidate_sha256='a'*64, revoke_invocation=revoker)
            handle = self.retain(life.process.hp)
            connection = None
            def cleanup():
                try:
                    # Tests may temporarily inject failure in revocation; the
                    # cleanup callback only concerns this synthetic invocation.
                    life._revoke = lambda invocation: None
                    if not life.closed:
                        result = life.close()
                        if result.job_drained is not None:
                            self.assertTrue(result.job_drained, 'Owned fixture job did not drain')
                    if connection is not None:
                        connection.close()  # The acknowledged fixture exits on EOF.
                    completed = _winapi.WaitForSingleObject(handle, 3000) == 0
                    if not completed:
                        _winapi.TerminateProcess(handle, 98)
                        _winapi.WaitForSingleObject(handle, 3000)
                    self.assertTrue(completed, 'Owned fixture did not exit after EOF/job abort')
                finally:
                    _winapi.CloseHandle(handle)
            self.addCleanup(cleanup)
            connection, _ = listener.accept(); connection.settimeout(5)
            self.assertEqual(receive_exact(connection, 1), b'R')
            return life, connection, handle, calls
        finally:
            listener.close()

    def test_pre_ack_abort_revokes_before_terminating_and_drains(self):
        life, connection, handle, calls = self.spawn()
        observed = []
        def revoke(invocation):
            observed.append((invocation is life.invocation, invocation.alive(), life.process.job is not None))
        life._revoke = revoke
        result = life.close()
        self.assertEqual(observed, [(True, True, True)])
        self.assertFalse(result.acknowledged)
        self.assertTrue(result.termination_requested)
        self.assertTrue(result.job_drained)
        self.assertFalse(self.alive(handle))
        self.assertFalse(life.invocation.alive())
        self.assertIs(life.close(), result)
        self.assertEqual(len(observed), 1)

    def test_ack_close_survives_and_never_uses_worker_termination(self):
        life, connection, handle, calls = self.spawn()
        life.acknowledge_handoff(life.invocation)
        self.assertTrue(life.invocation.alive())
        with patch.object(life.process, 'close', side_effect=AssertionError('Worker termination called')):
            result = life.close()
            self.assertIs(life.close(), result)
        self.assertTrue(result.acknowledged)
        self.assertFalse(result.termination_requested)
        self.assertIsNone(result.job_drained)
        self.assertTrue(self.alive(handle))
        self.assertEqual(calls, [life.invocation])
        self.assertFalse(life.invocation.alive())
        for name in ('hp', 'job', 'stdin', 'stdout', 'stderr'):
            self.assertIsNone(getattr(life.process, name))
        connection.sendall(b'X')
        self.assertEqual(_winapi.WaitForSingleObject(handle, 3000), 0)
        self.assertEqual(_winapi.GetExitCodeProcess(handle), 0)

    def test_ack_preserves_other_job_limits(self):
        life, connection, handle, calls = self.spawn()
        limits = life._query_limits()
        limits.BasicLimitInformation.LimitFlags |= 0x8  # ACTIVE_PROCESS limit.
        limits.BasicLimitInformation.ActiveProcessLimit = 3
        self.assertTrue(life._api.SetInformationJobObject(life.process.job, 9,
            ctypes.byref(limits), ctypes.sizeof(limits)))
        before = life._query_limits()
        life.acknowledge_handoff(life.invocation)
        after = life._query_limits()
        self.assertEqual(after.BasicLimitInformation.LimitFlags,
            before.BasicLimitInformation.LimitFlags & ~0x2000)
        self.assertEqual(after.BasicLimitInformation.ActiveProcessLimit, 3)
        life.acknowledge_handoff(life.invocation)  # Idempotent exact live ACK.

    def test_pre_ack_abort_drains_actual_descendant_job(self):
        life, connection, handle, calls = self.spawn(descendant=True)
        pid = int.from_bytes(receive_exact(connection, 4), 'little')
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        descendant = api.OpenProcess(0x100000 | 0x1000, False, pid)
        self.assertTrue(descendant)
        self.addCleanup(_winapi.CloseHandle, descendant)
        self.assertTrue(self.alive(descendant))
        result = life.close()
        self.assertTrue(result.job_drained)
        self.assertFalse(self.alive(handle))
        self.assertEqual(_winapi.WaitForSingleObject(descendant, 3000), 0)

    def test_wrong_ack_identity_and_ack_after_close_are_denied(self):
        life, connection, handle, calls = self.spawn()
        with patch.object(life, '_query_limits') as query:
            with self.assertRaises(NativeLifetimeError):
                life.acknowledge_handoff(object())
            query.assert_not_called()
        life.close()
        with self.assertRaises(NativeLifetimeError):
            life.acknowledge_handoff(life.invocation)

    def test_failed_disarm_keeps_launch_unacknowledged_and_abortable(self):
        life, connection, handle, calls = self.spawn()
        with patch.object(life._api, 'SetInformationJobObject', return_value=0):
            with self.assertRaises(NativeLifetimeError):
                life.acknowledge_handoff(life.invocation)
        self.assertFalse(life.acknowledged)
        self.assertTrue(life._query_limits().BasicLimitInformation.LimitFlags & 0x2000)
        self.assertTrue(life.close().job_drained)

    def test_revocation_failure_releases_nothing_and_is_retryable(self):
        for acknowledged in (False, True):
            with self.subTest(acknowledged=acknowledged):
                life, connection, handle, calls = self.spawn()
                if acknowledged:
                    life.acknowledge_handoff(life.invocation)
                hp, job = life.process.hp, life.process.job
                with patch.object(life, '_revoke', side_effect=RuntimeError('Synthetic revoke failure')):
                    with self.assertRaises(RuntimeError):
                        life.close()
                self.assertFalse(life.closed)
                self.assertEqual((life.process.hp, life.process.job), (hp, job))
                self.assertTrue(life.invocation.alive())
                result = life.close()
                self.assertEqual(result.acknowledged, acknowledged)
                self.assertEqual(self.alive(handle), acknowledged)

    def test_actual_grant_and_lease_are_revoked_before_release(self):
        store = CreativeHandoffs()
        life, connection, handle, calls = self.spawn()
        scope = CreativeScope('firebase:test:synthetic-owner', 'synthetic-project', 'r0', 'b'*64, 'a'*64)
        grant = store.issue(scope, life.invocation, auth_deadline=time.monotonic()+60)
        lease = store.redeem(grant, life.invocation)
        store.authorize(lease, life.invocation, project=scope.project, operation='read')
        observed = []
        def revoke(invocation):
            self.assertTrue(invocation.alive())
            store.revoke_invocation(invocation)
            with self.assertRaises(HandoffDenied):
                store.authorize(lease, invocation, project=scope.project, operation='read')
            observed.append(True)
        life._revoke = revoke
        life.acknowledge_handoff(life.invocation)
        life.close()
        self.assertEqual(observed, [True])
        self.assertTrue(self.alive(handle))

    def test_concurrent_release_revokes_only_once(self):
        life, connection, handle, calls = self.spawn()
        life.acknowledge_handoff(life.invocation)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: life.close(), range(16)))
        self.assertTrue(all(result is results[0] for result in results))
        self.assertEqual(calls, [life.invocation])
        self.assertTrue(self.alive(handle))

    def test_reentrant_or_async_revocation_is_not_claimed_complete(self):
        life, connection, handle, calls = self.spawn()
        with patch.object(life, '_revoke', side_effect=lambda invocation: life.close()):
            with self.assertRaises(NativeLifetimeError):
                life.close()
        self.assertFalse(life.closed)
        async def async_revoke():
            pass
        with patch.object(life, '_revoke', side_effect=lambda invocation: async_revoke()):
            with self.assertRaises(NativeLifetimeError):
                life.close()
        self.assertFalse(life.closed)
        self.assertTrue(life.invocation.alive())

    def test_invalid_startup_does_not_launch(self):
        async def async_revoke(invocation):
            pass
        for changes in ({'candidate_sha256':'bad'}, {'revoke_invocation':None},
                        {'revoke_invocation':async_revoke}, {'argv':'python.exe'}):
            args = dict(argv=[sys._base_executable], cwd=Path.cwd(), env=dict(os.environ),
                candidate_sha256='a'*64, revoke_invocation=lambda invocation: None)
            args.update(changes)
            with patch('security.native_creative_lifetime._WinProcess') as launch:
                with self.assertRaises(ValueError):
                    NativeCreativeLifetime(**args)
                launch.assert_not_called()

    def test_acknowledged_child_survives_actual_backend_exit(self):
        self.check_backend_exit(acknowledge=True)

    def test_unacknowledged_child_dies_on_actual_backend_exit(self):
        self.check_backend_exit(acknowledge=False)

    def check_backend_exit(self, *, acknowledge):
        # This separate synthetic supervisor exits via os._exit: no Python
        # cleanup/destructors. Windows closes its last real job handle.
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0)); listener.listen(); listener.settimeout(5)
        self.addCleanup(listener.close)
        child = ('import socket,sys; s=socket.create_connection(("127.0.0.1",int(sys.argv[1])));'
            's.settimeout(20);s.sendall(b"C");s.recv(1);s.close()')
        supervisor = '''
import os,socket,struct,sys
# Base Python avoids the venv redirector PID. Reuse the explicitly pinned test
# environment's dependency directory; -I deliberately ignores PYTHONPATH.
sys.path.insert(0,sys.argv[5]);sys.path.insert(0,sys.argv[1])
from security.native_creative_lifetime import NativeCreativeLifetime
s=socket.create_connection(('127.0.0.1',int(sys.argv[2])));s.settimeout(10);s.sendall(b'S')
life=NativeCreativeLifetime([sys._base_executable,'-I','-c',sys.argv[3],sys.argv[2]],os.getcwd(),dict(os.environ),candidate_sha256='a'*64,revoke_invocation=lambda invocation:None)
if sys.argv[4]=='1':life.acknowledge_handoff(life.invocation)
s.sendall(b'A'+struct.pack('<IQ',life.process.pid,life.invocation._birth))
if s.recv(1)!=b'X':raise RuntimeError('Missing synthetic exit command')
os._exit(0)
'''
        process = subprocess.Popen([sys._base_executable, '-I', '-c', supervisor,
            str(Path(__file__).resolve().parents[2]/'backend'),
            str(listener.getsockname()[1]), child, '1' if acknowledge else '0',
            sysconfig.get_path('purelib')],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
        control = connection = None
        handle = None
        def cleanup():
            try:
                for stream in (control, connection):
                    if stream is not None:
                        stream.close()
                if process.poll() is None:
                    process.terminate()  # Exact retained synthetic supervisor only.
                process.wait(timeout=5)
                if handle:
                    completed = _winapi.WaitForSingleObject(handle, 3000) == 0
                    if not completed:
                        _winapi.TerminateProcess(handle, 98)
                        _winapi.WaitForSingleObject(handle, 3000)
                    self.assertTrue(completed, 'Owned backend-loss child did not exit on EOF')
            finally:
                if handle:
                    _winapi.CloseHandle(handle)
        self.addCleanup(cleanup)
        for _ in range(2):
            stream, _ = listener.accept(); stream.settimeout(5)
            kind = receive_exact(stream, 1)
            if kind == b'S' and control is None:
                control = stream
            elif kind == b'C' and connection is None:
                connection = stream
            else:
                stream.close(); self.fail('Unexpected owned fixture handshake')
        self.assertIsNotNone(control); self.assertIsNotNone(connection)
        self.assertEqual(receive_exact(control, 1), b'A')
        pid, birth = struct.unpack('<IQ', receive_exact(control, 12))
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.GetProcessTimes.argtypes = [wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        api.GetProcessTimes.restype = wintypes.BOOL
        handle = api.OpenProcess(0x100000 | 0x1000 | 1, False, pid)
        self.assertTrue(handle)
        times = [wintypes.FILETIME() for _ in range(4)]
        self.assertTrue(api.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]))
        self.assertEqual(times[0].dwLowDateTime | times[0].dwHighDateTime << 32, birth)
        self.assertTrue(self.alive(handle))
        control.sendall(b'X')
        self.assertEqual(process.wait(timeout=5), 0)
        if acknowledge:
            self.assertTrue(self.alive(handle), 'Acknowledged editor died with backend')
            connection.sendall(b'X')
            self.assertEqual(_winapi.WaitForSingleObject(handle, 3000), 0)
            self.assertEqual(_winapi.GetExitCodeProcess(handle), 0)
        else:
            # KILL_ON_JOB_CLOSE specifies termination, not a particular exit
            # status. This host reports 0; the still-open application socket
            # received no release byte and the retained handle must signal.
            self.assertEqual(_winapi.WaitForSingleObject(handle, 3000), 0)


if __name__ == '__main__':
    unittest.main()
