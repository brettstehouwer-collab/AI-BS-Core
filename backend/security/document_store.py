"""Admission for document text snapshots and compare-and-swap writes.

Participating Windows API workers share a named mutex without creating sidecars
beside manuscripts. External editors and other write APIs do not use this lock.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import threading

from fastapi import HTTPException


_THREAD_LOCKS = tuple(threading.RLock() for _ in range(64))


@contextmanager
def document_path_lock(path: Path, timeout_ms: int = 15000):
    identity = os.path.normcase(str(Path(path).resolve()))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    thread_lock = _THREAD_LOCKS[int(digest[:8], 16) % len(_THREAD_LOCKS)]
    busy = 'The document is busy. Keep your draft and retry shortly.'
    if not thread_lock.acquire(timeout=timeout_ms / 1000):
        raise HTTPException(status_code=503, detail=busy)
    handle, acquired, api = None, False, None
    try:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
            api.CreateMutexW.restype = wintypes.HANDLE
            api.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            api.WaitForSingleObject.restype = wintypes.DWORD
            api.ReleaseMutex.argtypes = (wintypes.HANDLE,)
            api.ReleaseMutex.restype = wintypes.BOOL
            api.CloseHandle.argtypes = (wintypes.HANDLE,)
            api.CloseHandle.restype = wintypes.BOOL
            handle = api.CreateMutexW(None, False, 'Global\\AI-BS-Documents-v1-' + digest)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            outcome = api.WaitForSingleObject(handle, timeout_ms)
            # WAIT_ABANDONED grants ownership. The caller re-reads actual disk bytes.
            if outcome not in (0, 0x80):
                if outcome == 0x102:
                    raise HTTPException(status_code=503, detail=busy)
                raise ctypes.WinError(ctypes.get_last_error())
            acquired = True
        # Non-Windows callers have thread admission only; deployed worker admission
        # is the Windows named mutex, tested separately with spawned processes.
        yield
    finally:
        try:
            if handle is not None:
                try:
                    if acquired and not api.ReleaseMutex(handle):
                        raise ctypes.WinError(ctypes.get_last_error())
                finally:
                    api.CloseHandle(handle)
        finally:
            thread_lock.release()
