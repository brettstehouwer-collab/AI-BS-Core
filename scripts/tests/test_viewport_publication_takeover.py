"""Actual Windows publication and classified failure checks; no GUI or GPU."""
import ast
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

@unittest.skipUnless(os.name=='nt','Windows publication contract')
class SnapshotPublicationTests(unittest.TestCase):
    def setUp(self):
        source=ROOT/'native_studio/game_engine/creator_viewport.py'
        nodes=[node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
               if getattr(node,'name','')=='_replace_snapshot']
        namespace=dict(os=os,Path=Path,time=time)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
        self.publish=namespace['_replace_snapshot']
        base=ROOT/'t'
        base.mkdir(exist_ok=True)
        self.directory=tempfile.TemporaryDirectory(prefix='vpub-',dir=base)
        self.addCleanup(self.directory.cleanup)
        self.target=Path(self.directory.name)/'scene.aibv'
        self.pending=Path(self.directory.name)/'scene.tmp'
        self.target.write_bytes(b'old-complete-scene')
        self.pending.write_bytes(b'new-complete-scene')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.real_replace=kernel.ReplaceFileW
        self.real_replace.argtypes=(wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,
                                  wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p)
        self.real_replace.restype=wintypes.BOOL

    def test_actual_temporary_reader_lock_recovers_without_partial_publication(self):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
                                    ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p)
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        handle=kernel.CreateFileW(str(self.target),0x80000000,1,None,3,0x80,None)
        self.assertNotEqual(ctypes.c_void_p(-1).value,handle)
        def release():
            time.sleep(.02)
            kernel.CloseHandle(handle)
        thread=threading.Thread(target=release)
        thread.start()
        try:
            self.publish(self.pending,self.target)
        finally:
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(b'new-complete-scene',self.target.read_bytes())
        self.assertFalse(self.pending.exists())

    def test_1175_recovers_with_original_names_preserved_before_retry(self):
        calls=[]
        def replace(*args):
            calls.append(args)
            if len(calls)<3:
                self.assertEqual(b'old-complete-scene',self.target.read_bytes())
                self.assertEqual(b'new-complete-scene',self.pending.read_bytes())
                ctypes.set_last_error(1175)
                return False
            return self.real_replace(*args)
        with patch('ctypes.WinDLL',return_value=SimpleNamespace(ReplaceFileW=replace)):
            observed=self.publish(self.pending,self.target)
        self.assertEqual(3,len(calls))
        self.assertEqual({'attempts':3,'transient_errors':[1175,1175]},observed)
        self.assertEqual(b'new-complete-scene',self.target.read_bytes())

    def test_persistent_failure_is_bounded_and_retains_both_files(self):
        calls=[]
        def replace(*args):
            calls.append(args)
            ctypes.set_last_error(1175)
            return False
        start=time.monotonic()
        with patch('ctypes.WinDLL',return_value=SimpleNamespace(ReplaceFileW=replace)):
            with self.assertRaises(OSError) as raised:
                self.publish(self.pending,self.target)
        self.assertEqual(1175,raised.exception.winerror)
        self.assertEqual(len(calls),raised.exception.publication_attempts)
        self.assertEqual([1175]*len(calls),raised.exception.publication_errors)
        self.assertGreaterEqual(len(calls),2)
        self.assertLessEqual(len(calls),10)
        self.assertLess(time.monotonic()-start,1)
        self.assertEqual(b'old-complete-scene',self.target.read_bytes())
        self.assertEqual(b'new-complete-scene',self.pending.read_bytes())

    def test_partial_rename_error_is_not_blindly_retried(self):
        calls=[]
        def replace(*args):
            calls.append(args)
            ctypes.set_last_error(1176)
            return False
        with patch('ctypes.WinDLL',return_value=SimpleNamespace(ReplaceFileW=replace)):
            with self.assertRaises(OSError) as raised:
                self.publish(self.pending,self.target)
        self.assertEqual(1176,raised.exception.winerror)
        self.assertEqual(1,len(calls))
        self.assertTrue(self.pending.is_file())

    def test_actual_success_publishes_the_complete_pending_bytes(self):
        self.publish(self.pending,self.target)
        self.assertEqual(b'new-complete-scene',self.target.read_bytes())
        self.assertFalse(self.pending.exists())

if __name__=='__main__':
    unittest.main()
