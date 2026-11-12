"""Bounded v2 decoding/adoption and actual child stdin/pipe handoff, no Qt/API."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from native_studio.creative_session import Bootstrap,CreativeSession,CreativeSessionError,bootstrap_native_session
from native_studio.creative_pipe_bootstrap import decode_pipe_bootstrap,OwnedPipeResources,PipeBootstrapError


def packet():
    return {'version':1,'grant':'nch_g_'+'a'*43,'project':'fixture','revision':'r',
            'source_sha256':'a'*64,'candidate_sha256':'b'*64}


def envelope(handles=(100,104)):
    return {'version':2,'bootstrap':packet(),'channel':dict(zip(('read_handle','write_handle'),handles))}


class DecodeTests(unittest.TestCase):
    def test_returns_normal_bootstrap_and_exact_integer_pair(self):
        value,handles=decode_pipe_bootstrap(json.dumps(envelope()).encode())
        self.assertIs(type(value),Bootstrap)
        self.assertEqual(handles,(100,104))
        self.assertNotIn(packet()['grant'],repr(value))

    def test_rejects_malformed_oversized_duplicate_and_extra_fields_without_native_adoption(self):
        values=[b'x'*4097,b'{"version":2,"version":2}',b'[]',b'{}',
                json.dumps({**envelope(),'owner':'forged'}).encode(),
                json.dumps({**envelope(),'version':True}).encode(),
                json.dumps({**envelope(),'bootstrap':{**packet(),'version':2}}).encode()]
        with patch('native_studio.creative_pipe_bootstrap._kernel32',side_effect=AssertionError('No native adoption')):
            for raw in values:
                with self.subTest(raw=raw[:20]),self.assertRaises(CreativeSessionError):decode_pipe_bootstrap(raw)

    def test_handle_types_bounds_alias_and_bootstrap_scope_fields_rejected(self):
        for handles in ((True,104),(0,104),(-1,104),(100,100),(100,'104'),(100,1<<128)):
            with self.subTest(handles=handles),self.assertRaises(CreativeSessionError):
                decode_pipe_bootstrap(json.dumps(envelope(handles)).encode())
        for changes in ({'grant':'invalid'},{'source_sha256':'x'*64},{'project':''},{'candidate_sha256':None}):
            value=envelope();value['bootstrap'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(CreativeSessionError):
                decode_pipe_bootstrap(json.dumps(value).encode())

    def test_v2_flag_rejects_extra_args_before_stdin(self):
        with patch('native_studio.creative_pipe_bootstrap._read_bootstrap_bytes') as read:
            with self.assertRaises(CreativeSessionError):
                bootstrap_native_session(['app','--native-creative-pipe-bootstrap','extra'],object())
        read.assert_not_called()


@unittest.skipUnless(os.name=='nt','Windows inherited handles')
class AdoptionTests(unittest.TestCase):
    def setUp(self):
        import msvcrt
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.GetCurrentProcess.restype=wintypes.HANDLE
        self.api.DuplicateHandle.argtypes=[wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,
            ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.DuplicateHandle.restype=wintypes.BOOL
        self.api.GetFileType.argtypes=[wintypes.HANDLE]
        self.api.GetFileType.restype=wintypes.DWORD
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.originals=[]
        self.parent_read,child_write=os.pipe();child_read,self.parent_write=os.pipe()
        self.originals=[self.parent_read,child_write,child_read,self.parent_write]
        self.addCleanup(self.close_originals)
        self.duplicates=[]
        for fd in (child_read,child_write):
            result=wintypes.HANDLE()
            self.assertTrue(self.api.DuplicateHandle(self.api.GetCurrentProcess(),msvcrt.get_osfhandle(fd),
                self.api.GetCurrentProcess(),ctypes.byref(result),0,True,2))
            self.duplicates.append(result.value)
        self.claimed=False
        self.addCleanup(self.close_unclaimed)

    def close_originals(self):
        for fd in self.originals:os.close(fd)

    def close_unclaimed(self):
        if not self.claimed:
            for handle in self.duplicates:self.api.CloseHandle(handle)

    def adopt(self):
        self.claimed=True
        return OwnedPipeResources(tuple(self.duplicates))

    def test_actual_adoption_is_noninheritable_bidirectional_and_closes_only_claimed_handles(self):
        resources=self.adopt()
        try:
            self.assertFalse(any(os.get_handle_inheritable(h) for h in self.duplicates))
            os.write(self.parent_write,b'in')
            self.assertEqual(os.read(resources.endpoint._read_fd,2),b'in')
            os.write(resources.endpoint._write_fd,b'out')
            self.assertEqual(os.read(self.parent_read,3),b'out')
        finally:self.assertTrue(resources.close())
        self.assertTrue(resources.close())
        self.assertTrue(all(self.api.GetFileType(h)==0 for h in self.duplicates))
        os.write(self.parent_write,b'x')  # Original aliases still belong to fixture.

    def test_invalid_or_stdio_alias_pair_does_not_claim_or_close_peer(self):
        import msvcrt
        for handles in ((0,self.duplicates[1]),(msvcrt.get_osfhandle(0),self.duplicates[1])):
            with self.assertRaises(PipeBootstrapError):OwnedPipeResources(handles)
            self.assertEqual(self.api.GetFileType(self.duplicates[1]),3)
            self.assertTrue(os.get_handle_inheritable(self.duplicates[1]))

    def test_noninheritable_input_is_not_claimed(self):
        os.set_handle_inheritable(self.duplicates[0],False)
        with self.assertRaises(PipeBootstrapError):OwnedPipeResources(tuple(self.duplicates))
        self.assertEqual(self.api.GetFileType(self.duplicates[0]),3)
        self.assertEqual(self.api.GetFileType(self.duplicates[1]),3)

    def test_partial_crt_adoption_failure_closes_both_owned_handles(self):
        import msvcrt
        original=msvcrt.open_osfhandle;calls=[]
        def open_handle(handle,flags):
            calls.append(handle)
            if len(calls)==2:raise OSError('Synthetic adoption failure')
            return original(handle,flags)
        with patch.object(msvcrt,'open_osfhandle',side_effect=open_handle):
            with self.assertRaises(PipeBootstrapError) as caught:self.adopt()
        self.assertTrue(caught.exception.cleanup_complete)
        self.assertTrue(caught.exception.resources.close())
        self.assertTrue(all(self.api.GetFileType(h)==0 for h in self.duplicates))

    def test_incomplete_session_close_retains_owned_descriptors_for_retry(self):
        resources=self.adopt();session=CreativeSession(endpoint=resources.endpoint)
        session._attach_bootstrap_resources(resources)
        retained=set(resources._fds)
        try:
            with patch.object(resources.endpoint,'close',return_value=False):
                self.assertFalse(session.close())
                self.assertEqual(resources._fds,retained)
                self.assertTrue(all(self.api.GetFileType(h)==3 for h in self.duplicates))
            self.assertTrue(session.close())
            self.assertEqual(resources._fds,set())
        finally:self.assertTrue(resources.close())


@unittest.skipUnless(os.name=='nt','Actual Windows child bootstrap')
class ChildBootstrapTests(unittest.TestCase):
    def test_complete_packet_without_stdin_eof_is_not_released(self):
        child_code='''import sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root));sys.path.insert(0,str(root/'runtime/recovery-20261110/Lib/site-packages'))
from native_studio.creative_session import _read_bootstrap_bytes,CreativeSessionError
try:_read_bootstrap_bytes(sys.stdin.buffer,timeout=.15)
except CreativeSessionError:raise SystemExit(0)
raise SystemExit(19)
'''
        process=subprocess.Popen([sys._base_executable,'-I','-B','-c',child_code,str(ROOT)],
            cwd=ROOT,env={'SYSTEMROOT':os.environ['SYSTEMROOT'],'PYTHONUTF8':'1'},
            creationflags=subprocess.CREATE_NO_WINDOW,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            raw=json.dumps(envelope()).encode()
            self.assertEqual(process.stdin.write(raw),len(raw));process.stdin.flush()
            # Leave the writer open: complete JSON must not replace the EOF gate.
            self.assertEqual(process.wait(timeout=3),0)
            self.assertEqual(process.stdout.read(),b'')
            self.assertEqual(process.stderr.read(),b'')
        finally:
            if process.poll()is None:process.kill();process.wait(timeout=5)
            for stream in (process.stdin,process.stdout,process.stderr):stream.close()
            process._handle.Close()

    def test_actual_child_reads_eof_adopts_handles_sinks_output_redeems_and_closes(self):
        from security.native_creative_channel import CreativePipes
        from native_studio.creative_pipe_io import PipeEndpoint
        child_code='''import sys,os,ctypes
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root));sys.path.insert(0,str(root/'runtime/recovery-20261110/Lib/site-packages'))
from native_studio.creative_session import bootstrap_native_session,CreativeSession,Bootstrap
try:
 session,packet=bootstrap_native_session(['child','--native-creative-pipe-bootstrap'],sys.stdin.buffer)
 if type(session)is not CreativeSession or type(packet)is not Bootstrap:raise ValueError()
 result=session.channel_request('GET','/api/screenwriting/read',{'project_name':'fixture'})
 if result.json()!={'ok':True}:raise ValueError()
 if session.close()is not True:raise ValueError()
 if session._bootstrap_resources._fds:raise ValueError()
except BaseException:raise SystemExit(19)
raise SystemExit(0)
'''
        with CreativePipes() as resources:
            handles=resources.child_handles
            startup=subprocess.STARTUPINFO();startup.lpAttributeList={'handle_list':list(handles)}
            process=subprocess.Popen([sys._base_executable,'-I','-B','-c',child_code,str(ROOT)],
                cwd=ROOT,env={'SYSTEMROOT':os.environ['SYSTEMROOT'],'PYTHONUTF8':'1'},
                close_fds=True,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            endpoint=None
            try:
                resources.child_started()
                endpoint=PipeEndpoint(*resources.parent_fds)
                raw=json.dumps(envelope(handles)).encode()
                self.assertEqual(process.stdin.write(raw),len(raw));process.stdin.close()
                first=endpoint.receive(timeout=5)
                self.assertEqual(first['operation'],'redeem')
                self.assertEqual(first['payload'],{'grant':packet()['grant']})
                endpoint.send({'version':1,'id':first['id'],'status':200,'body':{
                    'lease':'nch_l_'+'b'*43,'project':'fixture','revision':'r',
                    'source_sha256':'a'*64,'expires_in':60}},timeout=5)
                second=endpoint.receive(timeout=5)
                self.assertEqual(second['operation'],'read')
                endpoint.send({'version':1,'id':second['id'],'status':200,'body':{'ok':True}},timeout=5)
                self.assertEqual(process.wait(timeout=5),0)
                self.assertEqual(process.stdout.read(),b'')
                self.assertEqual(process.stderr.read(),b'')
            finally:
                if process.poll()is None:process.kill();process.wait(timeout=5)
                if endpoint is not None:self.assertTrue(endpoint.close())
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream is not None:stream.close()
                process._handle.Close()


if __name__=='__main__':unittest.main(verbosity=2)
