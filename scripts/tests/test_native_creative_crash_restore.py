"""Full synthetic crash -> retained project -> fresh owned GUI recovery chain."""
from datetime import datetime,timezone
from pathlib import Path
import ctypes,hashlib,json,os,socket,subprocess,sys,sysconfig,unittest
from ctypes import wintypes
from unittest.mock import patch
from scripts.tests import test_native_creative_backend_loss as loss
ROOT=loss.ROOT
WORK=loss.WORK

@unittest.skipUnless(os.name=='nt','Windows exact owned process chain')
class CrashRestore(unittest.TestCase):
    def test_actual_crash_then_replacement_host_and_fresh_gui_recovery(self):
        import _winapi
        evidence=WORK/('native-crash-restore-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));evidence.mkdir()
        report={'status':'RUNNING','scope':'Synthetic source-fenced PDF plain projection / actual fresh owned GUI; no real Firebase login',
            'replacement_gui_cleanup_termination_requested':False}
        backend=None;gui=None;listener=None;connections=[]
        try:
            with patch.object(loss,'WORK',evidence):
                loss.BackendLoss().test_actual_backend_death_preserves_live_gui_and_private_unsaved_draft()
            initial_path=next(evidence.glob('native-backend-loss-*/result.json'))
            initial=json.loads(initial_path.read_text(encoding='utf-8'));self.assertEqual(initial['status'],'PASS')
            report['backend_loss_receipt']=str(initial_path);report['backend_loss_receipt_sha256']=hashlib.sha256(initial_path.read_bytes()).hexdigest()
            host=initial['host'];result=initial['gui_result'];root=Path(host['fixture_root']);project=Path(host['project'])
            recovery=Path(result['recovery_path']);recovery_before=recovery.read_bytes()
            copies_before={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in recovery.parent.glob('*.json')}
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(2);listener.settimeout(20)
            command=[sys._base_executable,'-I','-B',str(ROOT/'scripts/tests/fixtures/native_creative_crash_restore_host.py'),
                str(listener.getsockname()[1]),str(root),str(recovery),sysconfig.get_path('purelib')]
            backend=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,cwd=ROOT)
            meta={}
            for _ in range(2):
                connection,_=listener.accept();connection.settimeout(25);connections.append(connection)
                value=loss.receive(connection);self.assertNotEqual(value['kind'],'failure',value);meta[value['kind']]=(connection,value)
            host_channel,replacement=meta['replacement_host'];gui_channel,restored=meta['restore_gui']
            self.assertEqual(replacement['pid'],backend.pid);self.assertEqual(replacement['gui_pid'],restored['pid'])
            self.assertNotEqual(restored['pid'],initial['ready']['pid'])
            self.assertNotEqual(backend.pid,host['pid'])
            gui=_winapi.DuplicateHandle(int(backend._handle),replacement['gui_handle'],_winapi.GetCurrentProcess(),0,False,_winapi.DUPLICATE_SAME_ACCESS)
            api=ctypes.WinDLL('kernel32',use_last_error=True);api.GetProcessId.argtypes=[wintypes.HANDLE];api.GetProcessId.restype=wintypes.DWORD
            api.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
            fields=[wintypes.FILETIME()for _ in range(4)]
            self.assertEqual(api.GetProcessId(gui),restored['pid']);self.assertTrue(api.GetProcessTimes(gui,*[ctypes.byref(f)for f in fields]))
            self.assertEqual(fields[0].dwHighDateTime<<32|fields[0].dwLowDateTime,replacement['gui_birth'])
            self.assertEqual(_winapi.WaitForSingleObject(gui,0),258)
            report['replacement']=replacement;report['restored']=restored
            for field in ('dirty','recovery_button_used','restored_complete_draft','gui_drained','descriptors_closed'):self.assertTrue(restored[field])
            self.assertFalse(restored['uncertain']);self.assertFalse(restored['loaded_rich_document'])
            self.assertEqual(restored['host_operations_during_restore'],0);self.assertEqual(restored['http_calls'],0)
            self.assertEqual(restored['recovery_sha256'],result['recovery_sha256'])
            self.assertEqual(restored['revision'],replacement['revision'])
            gui_channel.sendall(b'X');self.assertEqual(_winapi.WaitForSingleObject(gui,10000),0)
            self.assertEqual(_winapi.GetExitCodeProcess(gui),0)
            completed=loss.receive(host_channel);report['replacement_completion']=completed
            self.assertEqual(completed['kind'],'host_complete');self.assertEqual(completed['writes'],0)
            self.assertTrue(completed['acknowledged']);self.assertFalse(completed['termination_requested'])
            self.assertTrue(completed['pipes_closed']);self.assertFalse(completed['cleanup_failed'])
            self.assertEqual(backend.wait(timeout=5),0)
            self.assertEqual(recovery.read_bytes(),recovery_before)
            for path,digest in copies_before.items():self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),digest)
            hashes={name:hashlib.sha256((project/name).read_bytes()).hexdigest()for name in host['hashes']}
            self.assertEqual(hashes,host['hashes'])
            report['source_hashes_after']=hashes;report['prior_recovery_hashes_unchanged']=copies_before
            report['fresh_gui_normal_exit']=True;report['status']='PASS'
        except BaseException as error:
            report['status']='FAILED_OR_INTERRUPTED';report['failure_class']=type(error).__name__;raise
        finally:
            if gui is not None:
                if _winapi.WaitForSingleObject(gui,0)==258:
                    report['replacement_gui_cleanup_termination_requested']=True;_winapi.TerminateProcess(gui,99);_winapi.WaitForSingleObject(gui,5000)
                _winapi.CloseHandle(gui)
            if backend is not None:
                if backend.poll()is None:backend.kill();backend.wait(timeout=5)
                report['replacement_backend_exit']=backend.returncode
                for name,stream in (('stdout',backend.stdout),('stderr',backend.stderr)):
                    raw=stream.read();(evidence/('replacement-'+name+'.log')).write_bytes(raw);stream.close()
                backend._handle.Close()
            for connection in connections:connection.close()
            if listener is not None:listener.close()
            report['finished_utc']=datetime.now(timezone.utc).isoformat()
            (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('CRASH_RESTORE_EVIDENCE='+str(evidence),flush=True)
if __name__=='__main__':unittest.main(verbosity=2)
