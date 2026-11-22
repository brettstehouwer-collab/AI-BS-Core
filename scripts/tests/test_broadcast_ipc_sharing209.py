"""Windows sharing fixtures under C backups; never operational broadcast IPC."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch
import uuid
import threading

ROOT=Path(__file__).resolve().parents[2]

class IpcSharing209Tests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('_audit_ipc_share209',ROOT/'native_studio/broadcast_ipc.py')
        self.ipc=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.ipc)
        self.fixture=ROOT/'backups/native_broadcast_preview209_work/ipc_hotfix209/fixtures'/uuid.uuid4().hex
        self.fixture.mkdir(parents=True)

    def test_concurrent_writer_retries_short_reader_and_reader_returns_captured_bytes(self):
        import win32file
        target=self.fixture/'reader.json';temporary=self.fixture/'replacement.json'
        target.write_bytes(b'original');temporary.write_bytes(b'replacement')
        actual_read=win32file.ReadFile;actual_replace=self.ipc.os.replace;attempted=threading.Event();errors=[];worker=[]
        def replace(source,destination):
            try:return actual_replace(source,destination)
            finally:attempted.set()
        def write():
            try:self.ipc._replace_shared(temporary,target)
            except Exception as error:errors.append(type(error).__name__)
        def replace_during_read(handle,size):
            thread=threading.Thread(target=write);worker.append(thread);thread.start()
            self.assertTrue(attempted.wait(.2))
            return actual_read(handle,size)
        with patch.object(win32file,'ReadFile',side_effect=replace_during_read),patch.object(self.ipc.os,'replace',side_effect=replace):
            self.assertEqual(self.ipc.read_shared_bytes(target,16),b'original')
            worker[0].join(.5)
            self.assertFalse(worker[0].is_alive());self.assertEqual(errors,[])
        self.assertEqual(target.read_bytes(),b'replacement')

    def test_reader_closes_handle_after_read_error_and_enforces_exact_limits(self):
        import win32file
        target=self.fixture/'limit';target.write_bytes(b'abcd')
        for limit in (True,0,-1,65537):
            with self.assertRaises(ValueError):self.ipc.read_shared_bytes(target,limit)
        self.assertEqual(self.ipc.read_shared_bytes(target,4),b'abcd')
        with self.assertRaises(ValueError):self.ipc.read_shared_bytes(target,3)
        with patch.object(win32file,'ReadFile',side_effect=OSError('synthetic read failure')):
            with self.assertRaises(OSError):self.ipc.read_shared_bytes(target,4)
        target.unlink();self.assertFalse(target.exists())

    def error(self,code):
        error=OSError('synthetic replace failure');error.winerror=code;return error

    def test_replace_retries_only_transient_windows_sharing_codes_with_bounded_backoff(self):
        for code in (5,32,33):
            with patch.object(self.ipc.os,'replace',side_effect=[self.error(code),None]) as replace,patch.object(self.ipc.time,'sleep') as sleep:
                self.ipc._replace_shared('fixture.tmp','fixture.json')
            self.assertEqual(replace.call_count,2);self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list),.2)
        for code in (2,3,87,None):
            with patch.object(self.ipc.os,'replace',side_effect=self.error(code)) as replace,patch.object(self.ipc.time,'sleep') as sleep:
                with self.assertRaises(OSError):self.ipc._replace_shared('fixture.tmp','fixture.json')
            self.assertEqual(replace.call_count,1);sleep.assert_not_called()
        with patch.object(self.ipc.os,'replace',side_effect=self.error(32)) as replace,patch.object(self.ipc.time,'sleep') as sleep:
            with self.assertRaises(OSError):self.ipc._replace_shared('fixture.tmp','fixture.json')
        self.assertLessEqual(replace.call_count,6);self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list),.2)

    def test_private_reader_keeps_validation_and_exact_json_limit(self):
        target=self.fixture/'private.json';target.write_bytes(b'{"x":1}')
        with patch.object(self.ipc,'validate_private_path') as validate:
            self.assertEqual(self.ipc.read_private_json(target,7),{'x':1})
        validate.assert_called_once_with(target,allow_missing=False)
        with patch.object(self.ipc,'validate_private_path'):
            with self.assertRaises(ValueError):self.ipc.read_private_json(target,6)

    def test_native_reader_errors_are_oserror_for_bounded_manifest_worker(self):
        import win32file,pywintypes
        target=self.fixture/'native_error';target.write_bytes(b'x')
        with patch.object(win32file,'ReadFile',side_effect=pywintypes.error(5,'ReadFile','synthetic fixture')):
            with self.assertRaises(OSError):self.ipc.read_shared_bytes(target,2)
        target.unlink()

if __name__=='__main__':unittest.main()
