"""Real FDX import -> owned Qt rich recovery -> CAS save -> fresh export."""
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,shutil,socket,sys,sysconfig,tempfile,time,unittest,uuid
from types import SimpleNamespace
from unittest.mock import patch
from pydantic import BaseModel,StrictInt
from scripts.tests import test_native_creative_pipe_controller as fixture
from scripts.tests.test_fdx_source_documents import XML,OWNER,fdx
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_handoff import CreativeHandoffs
from security.native_creative_controller import NativeCreativeController,ReviewedCandidate,PIPE_BOOTSTRAP_CONTRACT,NativeControllerError
ROOT=fixture.ROOT
WORK=Path('C:/Users/Administrator/Documents/Codex/2026-11-10/c-ai-bs/work')

def receive(connection):
    raw=bytearray()
    while not raw.endswith(b'\n'):
        if len(raw)>=32768:raise ValueError('Coordination bound')
        block=connection.recv(32768-len(raw))
        if not block:raise EOFError()
        raw.extend(block)
    return json.loads(raw)

@unittest.skipUnless(os.name=='nt','Windows owned Qt FDX workflow')
class RichNativeGui(unittest.TestCase):
    def test_real_rich_source_recovery_save_fresh_reopen_and_preserved_export(self):
        import _winapi
        evidence=WORK/('native-rich-gui-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));evidence.mkdir()
        root=Path(tempfile.mkdtemp(prefix='native-rich-gui-',dir=ROOT/'t'));projects=root/'projects';projects.mkdir()
        project=projects/'Rich GUI Project';initial=fdx.import_project(project,XML,OWNER,uuid.uuid4().hex)
        router=fixture.pdf.PdfWorkflowFixture();router.root=root;router.projects=projects
        ns=router.router_scope();ns.update(BaseModel=BaseModel,StrictInt=StrictInt)
        tree=ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8-sig'))
        nodes=[n for n in tree.body if getattr(n,'name','')in {'WriteScreenplayPayload','_issue_native_creative_grant'}]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual rich grant/write payload>','exec'),ns)
        services=SimpleNamespace(**ns);grants=CreativeHandoffs()
        immutable={'original.fdx':XML,'fdx_versions/'+initial['revision']+'/document.fdx':XML,
            'fdx_versions/'+initial['revision']+'/state.json':(project/'fdx_versions'/initial['revision']/'state.json').read_bytes()}
        report={'status':'RUNNING','scope':'Actual owned Qt rich FDX / synthetic verified context, not real Firebase login',
            'fixture_root':str(root),'original_revision':initial['revision'],'phases':[],'original_hashes':{p:hashlib.sha256(b).hexdigest()for p,b in immutable.items()}}
        current=lambda:fdx.read_project(project,OWNER)
        try:
            for phase in ('preserve','restore-save','reopen-export'):
                directory=root/phase;directory.mkdir()
                listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.2)
                child=ROOT/'scripts/tests/fixtures/native_creative_rich_gui_child.py'
                names=('creative_session.py','creative_pipe_bootstrap.py','creative_pipe_transport.py','creative_pipe_io.py','creative_wire.py',
                    'screenplay_client.py','native_creative_entry.py','screenwriting_view.py','engine.py','rich_screenplay_draft.py','theme.py')
                qt=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin'
                candidate=ReviewedCandidate(fixture.pin(sys._base_executable),
                    ('-I','-B',str(child),phase,str(listener.getsockname()[1]),str(directory),sysconfig.get_path('purelib'),'--native-creative-pipe-bootstrap'),str(ROOT),
                    (('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1'),('PATH',str(qt)+';'+str(Path(os.environ['SYSTEMROOT'])/'System32'))),
                    tuple(fixture.pin(p)for p in [child,*[ROOT/'native_studio'/name for name in names]]),PIPE_BOOTSTRAP_CONTRACT)
                controller=NativeCreativeController.create(candidate,grants,ns['_issue_native_creative_grant'],services=services)
                retained=None;record=None;connection=None
                item={'phase':phase,'status':'RUNNING','fixture_termination_requested':False,'candidate_sha256':candidate.sha256,
                    'source_pins':[{'path':p.path,'sha256':p.sha256}for p in candidate.files]};report['phases'].append(item)
                try:
                    if phase=='preserve':
                        before={p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in project.rglob('*')if p.is_file()}
                        with self.assertRaises(NativeControllerError):
                            controller.launch(VerifiedFirebaseContext(OWNER,time.monotonic()+180),project=project.name,
                                revision=initial['revision'],source_sha256='0'*64)
                        self.assertEqual(before,{p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in project.rglob('*')if p.is_file()})
                        report['wrong_source_preflight_refused']=True
                    with grants._lock:
                        issued=grants._issued.get(OWNER);delay=0 if issued is None else max(0,issued+1.02-grants._clock())
                    if delay:time.sleep(delay)
                    deliver=controller._deliver
                    def retain_before_delivery(owned,packet):
                        nonlocal retained
                        task_current=_winapi.GetCurrentProcess()
                        retained=_winapi.DuplicateHandle(task_current,owned._lifetime.process.hp,task_current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
                        return deliver(owned,packet)
                    with patch.object(controller,'_deliver',side_effect=retain_before_delivery):
                        record=controller.launch(VerifiedFirebaseContext(OWNER,time.monotonic()+180),project=project.name,
                            revision=current()['revision'],source_sha256=hashlib.sha256(XML).hexdigest())
                    item['pid']=record.pid;deadline=time.monotonic()+15
                    while connection is None:
                        try:connection,_=listener.accept()
                        except socket.timeout:
                            if time.monotonic()>deadline or _winapi.WaitForSingleObject(retained,0)==0:raise TimeoutError('Rich GUI readiness')
                    connection.settimeout(25);result=receive(connection);item['child_result']=result
                    self.assertEqual(result['kind'],'complete',result)
                    for key in ('loaded_rich_document','bootstrap_before_qt','only_writing_page','gui_drained','session_cleared','descriptors_closed'):self.assertTrue(result[key],key)
                    self.assertEqual(result['warning_count'],0);self.assertEqual(result['http_calls'],0)
                    connection.sendall(b'X');self.assertEqual(_winapi.WaitForSingleObject(retained,10000),0)
                    item['child_exit']=_winapi.GetExitCodeProcess(retained);self.assertEqual(item['child_exit'],0)
                    closed=controller.close(record)
                    if record._cleanup_worker is not None:record._cleanup_worker.join(timeout=3)
                    item['controller']={'acknowledged':closed.acknowledged,'termination_requested':closed.termination_requested,'cleanup_failed':controller.cleanup_failed}
                    self.assertTrue(closed.acknowledged);self.assertFalse(closed.termination_requested);self.assertFalse(controller.cleanup_failed)
                    self.assertFalse(record._pipes._fds)
                    for name,raw in immutable.items():self.assertEqual((project/name).read_bytes(),raw)
                    if phase=='preserve':
                        self.assertEqual(current()['revision'],initial['revision'])
                        recovery=Path(result['recovery_path']);self.assertEqual(hashlib.sha256(recovery.read_bytes()).hexdigest(),result['recovery_sha256'])
                        shutil.copy2(recovery,evidence/'rich-recovery.json')
                    elif phase=='restore-save':
                        self.assertNotEqual(current()['revision'],initial['revision'])
                        self.assertEqual(result['saved_revision'],current()['revision'])
                        self.assertEqual(result['recovery_sha256'],report['phases'][0]['child_result']['recovery_sha256'])
                    else:
                        exported=Path(result['export_path']).read_bytes()
                        self.assertEqual(exported,fdx.export_project(project,current()['revision'],OWNER))
                        shutil.copy2(result['export_path'],evidence/'preserved.fdx')
                    item['status']='PASS'
                finally:
                    if connection is not None:connection.close()
                    listener.close()
                    if retained is not None:
                        if _winapi.WaitForSingleObject(retained,0)==258:
                            item['fixture_termination_requested']=True;_winapi.TerminateProcess(retained,99);_winapi.WaitForSingleObject(retained,5000)
                        _winapi.CloseHandle(retained)
                    if record is not None:controller.close(record)
            self.assertEqual(len({p['pid']for p in report['phases']}),3)
            final=current();self.assertEqual(final['fdx_document']['blocks'][0]['text'],'Bold & carefully literal *stars*')
            self.assertEqual(final['fdx_document']['blocks'][0]['notes'],initial['fdx_document']['blocks'][0]['notes'])
            self.assertEqual(final['fdx_document']['preserved_sections'],initial['fdx_document']['preserved_sections'])
            self.assertEqual(final['fdx_document']['blocks'][1:],initial['fdx_document']['blocks'][1:])
            self.assertEqual(final['fdx_document']['title_page'],initial['fdx_document']['title_page'])
            # DOM patching can legitimately split one styled run around an
            # insertion. Compare every character's style rather than run count.
            def styled_characters(block):
                return [(character,run['attributes'])for run in block['runs']for character in run['text']]
            original_styled=styled_characters(initial['fdx_document']['blocks'][0])
            final_styled=styled_characters(final['fdx_document']['blocks'][0])
            insertion_start=len('Bold & ');insertion='carefully ';insertion_end=insertion_start+len(insertion)
            self.assertEqual(final_styled[:insertion_start]+final_styled[insertion_end:],original_styled)
            self.assertEqual(original_styled[insertion_start][1],{'Style':'Italic'})
            self.assertEqual(final_styled[insertion_start:insertion_end],
                [(character,original_styled[insertion_start][1])for character in insertion])
            report['final_revision']=final['revision'];report['original_hashes_after']={p:hashlib.sha256((project/p).read_bytes()).hexdigest()for p in immutable}
            report['status']='PASS'
        except BaseException as error:
            report['status']='FAILED_OR_INTERRUPTED';report['failure_class']=type(error).__name__;raise
        finally:
            report['finished_utc']=datetime.now(timezone.utc).isoformat()
            (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('RICH_GUI_EVIDENCE='+str(evidence),flush=True)
if __name__=='__main__':unittest.main(verbosity=2)
