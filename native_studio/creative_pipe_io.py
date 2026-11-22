"""Serialized, cancellable Windows pipe framing; no document authority.

The controller retains ownership of both descriptors and MUST NOT close them
until close() returns True. Revoke authority before closing this transport.
Failure permanently poisons this endpoint: a timed-out save may have completed,
so neither retry nor an HTTP/reconnect fallback is safe. Cancellation is an OS
request, not a guaranteed drain; incomplete cleanup retains the exact thread
handle and operation for a later close(). No production entrypoint uses this yet.
"""
import ctypes
from ctypes import wintypes
import math
import os
import threading
import time

from native_studio.creative_wire import encode, read_message


class PipeIOError(RuntimeError):
    def __init__(self, *, cleanup_complete):
        super().__init__('Creative channel unavailable; operation outcome may be unknown.')
        self.cleanup_complete = cleanup_complete


class PipeBusyError(RuntimeError):
    """No queued work and no transfer: caller must not automatically retry."""


class _Operation:
    def __init__(self):
        self.start = threading.Event()
        self.cancel = threading.Event()
        self.done = threading.Event()
        self.thread = None
        self.handle = None
        self.value = None
        self.failed = False
        self.native_finished = False


class PipeEndpoint:
    """One outstanding bounded framed operation, with no background queue.

    Calls must run outside the GUI thread. Only these dedicated I/O threads may
    touch the borrowed pipe descriptors; do not share them with another reader.
    The endpoint takes no authority from a PID or pipe name.
    """
    def __init__(self, read_fd, write_fd, *, receive_timeout_limit=30):
        if os.name != 'nt':
            raise OSError('Windows creative pipe transport required.')
        if (type(read_fd) is not int or type(write_fd) is not int
                or read_fd < 0 or write_fd < 0 or read_fd == write_fd):
            raise ValueError('Two distinct owned pipe descriptors are required.')
        self._receive_timeout_limit = self._seconds(receive_timeout_limit, 300)
        import msvcrt
        self._api = ctypes.WinDLL('kernel32', use_last_error=True)
        self._api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self._api.OpenThread.restype = wintypes.HANDLE
        self._api.CancelSynchronousIo.argtypes = [wintypes.HANDLE]
        self._api.CancelSynchronousIo.restype = wintypes.BOOL
        self._api.CloseHandle.argtypes = [wintypes.HANDLE]
        self._api.CloseHandle.restype = wintypes.BOOL
        self._api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self._api.WaitForSingleObject.restype = wintypes.DWORD
        self._api.GetFileType.argtypes = [wintypes.HANDLE]
        self._api.GetFileType.restype = wintypes.DWORD
        if any(self._api.GetFileType(msvcrt.get_osfhandle(fd)) != 3
               for fd in (read_fd, write_fd)):
            raise ValueError('Pipe descriptors are required.')
        self._read_fd, self._write_fd = read_fd, write_fd
        self._state = threading.Lock()
        self._serial = threading.Lock()
        self._closed = False
        self._operation = None

    @staticmethod
    def _seconds(value, maximum):
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not 0 < value <= maximum):
            raise ValueError('A finite bounded timeout is required.')
        return value

    def _work(self, op, frame, receive):
        try:
            op.start.wait()
            def check():
                if op.cancel.is_set():
                    raise OSError('Cancelled')
            if frame is not None:
                offset = 0
                while offset < len(frame):
                    check()
                    count = os.write(self._write_fd, frame[offset:offset + 65536])
                    if count <= 0:
                        raise OSError('Incomplete write')
                    offset += count
            if receive:
                def read(length):
                    check()
                    return os.read(self._read_fd, min(length, 65536))
                op.value = read_message(read)
            check()
        except BaseException:
            # Never retain a traceback, private frame or native exception text.
            op.value = None
            op.failed = True
        finally:
            op.done.set()

    def _drain(self, op, seconds):
        deadline = time.monotonic() + seconds
        if op.thread.ident is None:
            # A failed/interrupted start may have an unknown native outcome.
            # Retain it rather than claiming that the gated thread has exited.
            return False
        while True:
            with self._state:
                if op.handle is not None:
                    status = self._api.WaitForSingleObject(op.handle, 0)
                    if status == 0:
                        if not self._api.CloseHandle(op.handle):
                            return False
                        op.handle = None
                        op.native_finished = True
                        return True
                    if status != 258:
                        return False
                    if op.cancel.is_set():
                        # Native handle, not Python's interruptible join flag,
                        # proves which thread to cancel and whether it exited.
                        self._api.CancelSynchronousIo(op.handle)
                elif op.native_finished:
                    return True
                elif op.done.is_set() and not op.thread.is_alive():
                    # Startup failed before a handle was available. The gate
                    # was cancelled first; no native I/O was ever admitted.
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            # No join dependency: an interrupted join can corrupt Python's
            # liveness observation while the native I/O is still outstanding.
            time.sleep(min(.005, remaining))

    def _run(self, frame, receive, timeout, cleanup_timeout):
        self._seconds(timeout, self._receive_timeout_limit if frame is None and receive else 30)
        self._seconds(cleanup_timeout, 5)
        if not self._serial.acquire(blocking=False):
            raise PipeBusyError('Creative channel already has an operation.')
        op = None
        try:
            with self._state:
                if self._closed:
                    raise PipeIOError(cleanup_complete=self._operation is None)
                op = _Operation()
                self._operation = op
                op.thread = threading.Thread(target=self._work, args=(op, frame, receive),
                                             name='AI-BS creative pipe I/O', daemon=False)
                try:
                    op.thread.start()
                except BaseException:
                    self._closed = True
                    op.cancel.set()
                    op.start.set()
                    raise
                # Worker cannot perform I/O until we retain its exact handle.
                op.handle = self._api.OpenThread(0x100001, False, op.thread.native_id)
                if not op.handle:
                    op.handle = None
                    self._closed = True
                    op.cancel.set()
                op.start.set()
            completed = op.done.wait(timeout)
            with self._state:
                refused = self._closed or not completed or op.failed
                if refused:
                    self._closed = True
                    op.cancel.set()
            drained = self._drain(op, cleanup_timeout)
            with self._state:
                if drained:
                    self._operation = None
                if refused or not drained or self._closed:
                    self._closed = True
                    op.value = None
                    raise PipeIOError(cleanup_complete=drained)
                return op.value
        except PipeIOError:
            # The ordinary refusal path has already attempted bounded cleanup.
            raise
        except BaseException:
            with self._state:
                self._closed = True
                if op is not None:
                    op.cancel.set()
                    op.start.set()
            if op is not None and op.thread is not None:
                drained = self._drain(op, cleanup_timeout)
                if drained:
                    with self._state:
                        if self._operation is op:
                            self._operation = None
                op.value = None
            raise
        finally:
            self._serial.release()

    def exchange(self, value, *, timeout=10, cleanup_timeout=2):
        return self._run(encode(value), True, timeout, cleanup_timeout)

    def receive(self, *, timeout=10, cleanup_timeout=2):
        return self._run(None, True, timeout, cleanup_timeout)

    def send(self, value, *, timeout=10, cleanup_timeout=2):
        return self._run(encode(value), False, timeout, cleanup_timeout)

    def close(self, *, cleanup_timeout=2):
        self._seconds(cleanup_timeout, 5)
        with self._state:
            self._closed = True
            op = self._operation
            if op is None:
                return True
            op.cancel.set()
            op.start.set()
        drained = self._drain(op, cleanup_timeout)
        with self._state:
            if drained and self._operation is op:
                self._operation = None
        return drained
