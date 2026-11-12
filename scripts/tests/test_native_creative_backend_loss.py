"""Exact owned backend termination after GUI ack; synthetic stores only."""
from datetime import datetime,timezone
from pathlib import Path
import ctypes,hashlib,json,os,socket,subprocess,sys,sysconfig,time,unittest
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/Administrator/Documents/Codex/2026-11-10/c-ai-bs/work')
MARKER='UNSAVED BACKEND LOSS SYNTHETIC EDIT'
def receive(connection):
    raw=bytearray()
    while not raw.endswith(b'\n'):
        if len(raw)>32768:raise ValueError('Metadata bound')
        part=connection.recv(32768-len(raw))
        if not part:raise EOFError()
        raw.extend(part)
    return json.loads(raw)
@unittest.skipUnless(os.name=='nt','Windows exact process handles')
class BackendLoss(unittest.TestCase):
    def test_actual_backend_death_preserves_live_gui_and_private_unsaved_draft(self):
        import _winapi
        evidence=WORK/('native-backend-loss-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));evidence.mkdir()
        report={'status':'RUNNING','scope':'Synthetic backend/real offscreen GUI only','backend_termination_requested':False,'gui_cleanup_termination_requested':False}
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(2);listener.settimeout(20)
        backend=None;gui=None;connections=[]
        try:
            command=[sys._base_executable,'-I','-B',str(ROOT/'scripts/tests/fixtures/native_creative_backend_loss_host.py'),
                str(listener.getsockname()[1]),sysconfig.get_path('purelib')]
            backend=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,cwd=ROOT)
            meta={}
            for _ in range(2):
                connection,_=listener.accept();connection.settimeout(20);connections.append(connection)
                value=receive(connection);meta[value['kind']]=(connection,value)
            host=meta['host_ready'][1];channel,ready=meta['gui_ready']
            self.assertEqual(host['pid'],backend.pid);self.assertEqual(host['gui_pid'],ready['pid'])
            self.assertTrue(host['acknowledged']);self.assertTrue(ready['unsaved'])
            current=_winapi.GetCurrentProcess()
            gui=_winapi.DuplicateHandle(int(backend._handle),host['gui_handle'],current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
            api=ctypes.WinDLL('kernel32',use_last_error=True);api.GetProcessId.argtypes=[wintypes.HANDLE];api.GetProcessId.restype=wintypes.DWORD
            api.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
            fields=[wintypes.FILETIME()for _ in range(4)]
            self.assertEqual(api.GetProcessId(gui),ready['pid']);self.assertTrue(api.GetProcessTimes(gui,*[ctypes.byref(f)for f in fields]))
            self.assertEqual(fields[0].dwHighDateTime<<32|fields[0].dwLowDateTime,host['gui_birth'])
            self.assertEqual(_winapi.WaitForSingleObject(gui,0),258)
            report['host']=host;report['ready']=ready
            report['backend_termination_requested']=True
            _winapi.TerminateProcess(int(backend._handle),77);self.assertEqual(backend.wait(timeout=5),77)
            self.assertEqual(_winapi.WaitForSingleObject(gui,0),258)
            channel.sendall(b'L');result=receive(channel);report['gui_result']=result
            self.assertEqual(result['kind'],'complete',result)
            for key in ('dirty','uncertain','previous_recovery_unchanged','recovery_matches_complete_draft','gui_drained','descriptors_closed'):self.assertTrue(result[key])
            self.assertEqual(result['http_calls'],0)
            self.assertEqual(result['save_attempts'],1)
            project=Path(host['project']).resolve();root=Path(host['fixture_root']).resolve()
            self.assertEqual(root.parent,(ROOT/'t').resolve());self.assertTrue(project.is_relative_to(root))
            recovery=Path(result['recovery_path']).resolve();self.assertTrue(recovery.is_relative_to(root))
            raw=recovery.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),result['recovery_sha256'])
            self.assertIn(MARKER,json.loads(raw)['content'])
            after={n:hashlib.sha256((project/n).read_bytes()).hexdigest()for n in host['hashes']}
            self.assertEqual(after,host['hashes']);report['source_hashes_after']=after
            channel.sendall(b'X');self.assertEqual(_winapi.WaitForSingleObject(gui,10000),0)
            report['gui_exit_code']=_winapi.GetExitCodeProcess(gui);self.assertEqual(report['gui_exit_code'],0)
            report['status']='PASS'
        except BaseException as error:
            report['status']='FAILED_OR_INTERRUPTED';report['failure_class']=type(error).__name__;raise
        finally:
            if gui is not None:
                if _winapi.WaitForSingleObject(gui,0)==258:
                    report['gui_cleanup_termination_requested']=True;_winapi.TerminateProcess(gui,99);_winapi.WaitForSingleObject(gui,5000)
                _winapi.CloseHandle(gui)
            if backend is not None:
                if backend.poll()is None:backend.kill();backend.wait(timeout=5)
                for stream in (backend.stdout,backend.stderr):stream.close()
                backend._handle.Close()
            for c in connections:c.close()
            listener.close();report['finished_utc']=datetime.now(timezone.utc).isoformat()
            (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('BACKEND_LOSS_EVIDENCE='+str(evidence),flush=True)
if __name__=='__main__':unittest.main(verbosity=2)
