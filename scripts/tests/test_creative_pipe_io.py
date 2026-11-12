"""Real Windows anonymous-pipe deadlines; synthetic bytes, no backend listener."""
import concurrent.futures
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from security.native_creative_channel import CreativePipes
from native_studio.creative_pipe_io import PipeEndpoint, PipeIOError, PipeBusyError
from native_studio.creative_wire import encode
from native_studio.creative_pipe_io import _Operation

CHILD = '''import os,sys,msvcrt,struct,json,time
r=msvcrt.open_osfhandle(int(sys.argv[1]),os.O_RDONLY|os.O_BINARY)
w=msvcrt.open_osfhandle(int(sys.argv[2]),os.O_WRONLY|os.O_BINARY)
mode=sys.argv[3]
def write(b):
 while b:
  n=os.write(w,b);b=b[n:]
def message(v):
 b=json.dumps(v).encode();write(struct.pack('!I',len(b))+b)
def exact(n):
 b=b''
 while len(b)<n:
  p=os.read(r,n-len(b))
  if not p:raise SystemExit(0)
  b+=p
 return b
message({'ready':True})
if mode=='partial-header':write(b'\\x00\\x00');time.sleep(60)
elif mode=='partial-body':write(struct.pack('!I',100)+b'{}');time.sleep(60)
elif mode=='malformed':write(struct.pack('!I',2)+b'[]');time.sleep(60)
elif mode=='stall':time.sleep(60)
elif mode=='exit':pass
else:
 while True:
  n=struct.unpack('!I',exact(4))[0]
  if not 1<=n<=8*1024*1024:raise SystemExit(2)
  v=json.loads(exact(n));message(v)
'''


@unittest.skipUnless(os.name == 'nt', 'Windows synchronous pipe cancellation')
class PipeIOTests(unittest.TestCase):
    @contextmanager
    def child(self, mode):
        pipes = CreativePipes()
        handles = pipes.child_handles
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {'handle_list': list(handles)}
        process = subprocess.Popen([sys._base_executable, '-I', '-B', '-c', CHILD,
            *map(str, handles), mode], close_fds=True, startupinfo=startup,
            creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        endpoint = None
        try:
            pipes.child_started()
            endpoint = PipeEndpoint(*pipes.parent_fds)
            self.assertEqual(endpoint.receive(timeout=5), {'ready': True})
            yield endpoint, process
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            # Closing a pipe while another thread uses it is expressly forbidden.
            drained = endpoint is None or endpoint.close(cleanup_timeout=5)
            self.assertTrue(drained)
            if drained:
                pipes.close()
            # Popen.wait() retains its owned process handle until finalization.
            # Close this known test handle explicitly before leak accounting.
            process._handle.Close()

    def test_unicode_and_large_fragmented_roundtrip(self):
        with self.child('echo') as (endpoint, _):
            value = {'text': 'synthetic é 日本語 ' * 100000}
            self.assertEqual(endpoint.exchange(value, timeout=5), value)
            self.assertEqual(endpoint.exchange({'next': True}), {'next': True})
            self.assertIsNone(endpoint._operation)

    def test_unread_multimegabyte_write_cancels_and_permanently_refuses(self):
        with self.child('stall') as (endpoint, process):
            started = time.monotonic()
            with self.assertRaises(PipeIOError) as caught:
                endpoint.send({'text': 'x' * (4 * 1024 * 1024)}, timeout=.15)
            self.assertTrue(caught.exception.cleanup_complete)
            self.assertLess(time.monotonic() - started, 3)
            self.assertIsNone(endpoint._operation)
            self.assertIsNone(process.poll())
            with self.assertRaises(PipeIOError): endpoint.exchange({'retry': True})

    def test_stalled_partial_header_and_body_cancel_without_acceptance(self):
        for mode in ('partial-header', 'partial-body'):
            with self.subTest(mode=mode), self.child(mode) as (endpoint, _):
                with self.assertRaises(PipeIOError) as caught:
                    endpoint.receive(timeout=.15)
                self.assertTrue(caught.exception.cleanup_complete)
                self.assertIsNone(endpoint._operation)

    def test_malformed_message_and_peer_exit_are_terminal(self):
        for mode in ('malformed', 'exit'):
            with self.subTest(mode=mode), self.child(mode) as (endpoint, _):
                with self.assertRaises(PipeIOError) as caught:
                    endpoint.receive(timeout=3)
                self.assertTrue(caught.exception.cleanup_complete)
                with self.assertRaises(PipeIOError): endpoint.receive(timeout=.1)

    def test_concurrent_close_cancels_read_and_no_work_is_queued(self):
        with self.child('stall') as (endpoint, process):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(endpoint.receive, timeout=5)
                deadline = time.monotonic() + 2
                while endpoint._operation is None and time.monotonic() < deadline:
                    time.sleep(.001)
                self.assertIsNotNone(endpoint._operation)
                with self.assertRaises(PipeBusyError): endpoint.send({'queued': True})
                self.assertTrue(endpoint.close())
                with self.assertRaises(PipeIOError) as caught: result.result(timeout=3)
                self.assertTrue(caught.exception.cleanup_complete)
            self.assertIsNone(process.poll())
            self.assertTrue(endpoint.close())

    def test_repeated_success_and_cancellation_leave_no_threads_or_handles(self):
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.GetCurrentProcess.restype = wintypes.HANDLE
        api.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        def count():
            value = wintypes.DWORD()
            self.assertTrue(api.GetProcessHandleCount(api.GetCurrentProcess(), ctypes.byref(value)))
            return value.value
        def cycle():
            with self.child('echo') as (endpoint, _):
                self.assertEqual(endpoint.exchange({'n': 1}), {'n': 1})
            with self.child('stall') as (endpoint, _):
                with self.assertRaises(PipeIOError): endpoint.receive(timeout=.05)
        # CPython lazily initializes Windows thread machinery. Measure steady
        # state after one controlled cycle and after fixture references release.
        cycle()
        before = count()
        for _ in range(4):
            cycle()
        self.assertFalse(any(t.name == 'AI-BS creative pipe I/O' for t in threading.enumerate()))
        self.assertLessEqual(count(), before)

    def test_failed_open_thread_poisoned_before_any_io(self):
        with self.child('stall') as (endpoint, _):
            with patch.object(endpoint._api, 'OpenThread', return_value=0):
                with self.assertRaises(PipeIOError) as caught: endpoint.receive(timeout=.1)
            self.assertTrue(caught.exception.cleanup_complete)
            self.assertIsNone(endpoint._operation)
            with self.assertRaises(PipeIOError): endpoint.receive(timeout=.1)

    def test_open_thread_exception_cleans_gated_worker_and_refuses_later_work(self):
        with self.child('stall') as (endpoint, _):
            with patch.object(endpoint._api, 'OpenThread', side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError): endpoint.receive(timeout=.1)
            self.assertIsNone(endpoint._operation)
            with self.assertRaises(PipeIOError): endpoint.receive(timeout=.1)

    def test_observation_exception_cancels_exact_worker(self):
        with self.child('stall') as (endpoint, _):
            op = _Operation()
            with patch('native_studio.creative_pipe_io._Operation', return_value=op), \
                    patch.object(op.done, 'wait', side_effect=RuntimeError('synthetic observation failure')):
                with self.assertRaises(RuntimeError): endpoint.receive(timeout=.1)
            self.assertFalse(op.thread.is_alive())
            self.assertIsNone(op.handle)
            self.assertIsNone(endpoint._operation)
            with self.assertRaises(PipeIOError): endpoint.receive(timeout=.1)

    def test_start_exception_after_native_start_does_not_strand_gated_worker(self):
        with self.child('stall') as (endpoint, _):
            start = threading.Thread.start
            op = _Operation()
            def interrupted_start(thread):
                start(thread)
                raise RuntimeError('synthetic startup interruption')
            with patch('native_studio.creative_pipe_io._Operation', return_value=op), \
                    patch.object(threading.Thread, 'start', interrupted_start):
                with self.assertRaises(RuntimeError): endpoint.receive(timeout=.1)
            self.assertFalse(op.thread.is_alive())
            self.assertIsNone(endpoint._operation)
            with self.assertRaises(PipeIOError): endpoint.receive(timeout=.1)

    def test_incomplete_drain_retains_operation_until_later_close(self):
        with self.child('stall') as (endpoint, _):
            with patch.object(endpoint, '_drain', return_value=False):
                with self.assertRaises(PipeIOError) as caught: endpoint.receive(timeout=.05)
                retained = endpoint._operation
                self.assertIsNotNone(retained)
                self.assertIsNotNone(retained.handle)
                self.assertFalse(caught.exception.cleanup_complete)
            self.assertTrue(endpoint.close())
            self.assertIsNone(retained.handle)
            self.assertIsNone(endpoint._operation)

    def test_cancel_immediately_before_native_read_is_repeated_until_drained(self):
        with self.child('stall') as (endpoint, _):
            entered, release = threading.Event(), threading.Event()
            original_read = os.read
            original_cancel = endpoint._api.CancelSynchronousIo
            def read(fd, length):
                entered.set()
                if not release.wait(3): raise RuntimeError('Test barrier deadline')
                return original_read(fd, length)
            def cancel(handle):
                result = original_cancel(handle)
                release.set()
                return result
            with patch('native_studio.creative_pipe_io.os.read', side_effect=read), \
                    patch.object(endpoint._api, 'CancelSynchronousIo', side_effect=cancel) as calls:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(endpoint.receive, timeout=5)
                    try:
                        self.assertTrue(entered.wait(2))
                        self.assertTrue(endpoint.close())
                        with self.assertRaises(PipeIOError): future.result(timeout=3)
                        self.assertGreaterEqual(calls.call_count, 2)
                    finally:
                        release.set()

    def test_native_handle_cancellation_survives_stale_python_liveness(self):
        with self.child('stall') as (endpoint, _):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(endpoint.receive, timeout=5)
                deadline = time.monotonic() + 2
                while endpoint._operation is None and time.monotonic() < deadline:
                    time.sleep(.001)
                op = endpoint._operation
                self.assertIsNotNone(op)
                # Simulate an interrupted Python join's false stopped flag.
                with patch.object(op.thread, 'is_alive', return_value=False):
                    self.assertTrue(endpoint.close())
                    with self.assertRaises(PipeIOError): future.result(timeout=3)
                self.assertIsNone(op.handle)
                self.assertTrue(op.native_finished)

    def test_invalid_timeouts_and_descriptor_types_do_not_start_io(self):
        for value in (True, 0, -1, float('nan'), float('inf'), 31):
            with self.child('echo') as (endpoint, _):
                with self.assertRaises(ValueError): endpoint.receive(timeout=value)
                self.assertIsNone(endpoint._operation)

    def test_server_receive_can_use_longer_limit_without_extending_client_requests(self):
        with CreativePipes() as pipes:
            endpoint=PipeEndpoint(*pipes.parent_fds,receive_timeout_limit=300)
            try:
                os.write(pipes._child_write,encode({'server_idle':True}))
                self.assertEqual(endpoint.receive(timeout=31),{'server_idle':True})
                with self.assertRaises(ValueError):endpoint.exchange({'request':True},timeout=31)
                with self.assertRaises(ValueError):endpoint.send({'request':True},timeout=31)
            finally:
                self.assertTrue(endpoint.close())


if __name__ == '__main__':
    unittest.main(verbosity=2)
