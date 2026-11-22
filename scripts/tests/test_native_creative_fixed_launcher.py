"""Fixed launcher import boundary plus actual owned source-fenced GUI smoke."""
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys,tempfile,threading,time,types,unittest,uuid
from types import SimpleNamespace
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2]
LAUNCHER=ROOT/'runtime/devtools/native_creative_writer.py'
WORK=Path('C:/Users/Administrator/Documents/Codex/2026-11-10/c-ai-bs/work')

def load_launcher():
    spec=importlib.util.spec_from_file_location('aibs_fixed_creative_launcher',LAUNCHER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def diagnostic_writer_startup():
    """Test-only staged startup with synthetic in-memory transport, no bootstrap.

    This is not authentication evidence. It exposes only exception locations
    hidden by the production entry's intentionally sanitized failure response.
    """
    import traceback
    sys.path[:0]=[str(ROOT),str(ROOT/'runtime/recovery-20261110/Lib/site-packages')]
    from native_studio import native_creative_entry as entry
    from native_studio.creative_session import CreativeSession,Bootstrap
    from scripts.tests.test_native_rich_writer import fixture
    import httpx
    packet=Bootstrap('nch_g_'+'x'*43,'Fixture','a'*64,'a'*64,'b'*64)
    class Channel:
        def request(self,*args):return httpx.Response(200,json=fixture())
        def close(self):return True
    session=CreativeSession(headers_provider=lambda:(_ for _ in ()).throw(AssertionError('No headers')))
    session._scope=packet;session._lease='nch_l_'+'x'*43;session._deadline=time.monotonic()+30;session._channel=Channel()
    create=entry.create_native_creative_window
    def close_after_creation(*args):
        window=create(*args)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100,window.close)
        return window
    try:
        with patch.object(entry,'create_native_creative_window',side_effect=close_after_creation):
            result=load_launcher()._run_verified_writer(session,packet)
        print(json.dumps({'status':'PASS','result':result}),flush=True)
    except BaseException as error:
        print(json.dumps({'status':'FAILED','exception_class':type(error).__name__,
            'locations':[{'file':Path(frame.filename).name,'line':frame.lineno}for frame in traceback.extract_tb(error.__traceback__)]}),flush=True)
        raise


class FixedLauncherBoundary(unittest.TestCase):
    def test_import_does_not_change_paths_or_import_qt(self):
        before=list(sys.path);qt={name for name in sys.modules if name.startswith('PyQt6')}
        module=load_launcher()
        self.assertEqual(sys.path,before);self.assertEqual(qt,{name for name in sys.modules if name.startswith('PyQt6')})
        self.assertEqual(module.PROJECT_ROOT,ROOT)
        self.assertEqual(module.RECOVERY_SITE_PACKAGES,ROOT/'runtime/recovery-20261110/Lib/site-packages')

    def test_ordinary_legacy_or_extra_arguments_refuse_before_entry(self):
        module=load_launcher();fake=types.ModuleType('native_studio.native_creative_entry');fake.main=Mock()
        before=list(sys.path)
        with patch.dict(sys.modules,{'native_studio.native_creative_entry':fake}):
            for argv in ([],['writer'],['writer','--native-creative-bootstrap'],
                         ['writer',module.BOOTSTRAP_FLAG,'C:/untrusted'],['writer','--endpoint=http://example.invalid']):
                with self.subTest(argv=argv):self.assertEqual(module.main(argv),2)
        fake.main.assert_not_called();self.assertEqual(sys.path,before)

    def test_explicit_mode_uses_only_fixed_dependencies_and_existing_entry(self):
        module=load_launcher();fake=types.ModuleType('native_studio.native_creative_entry');fake.main=Mock(return_value=0)
        before=list(sys.path)
        try:
            with patch.dict(sys.modules,{'native_studio.native_creative_entry':fake}):
                self.assertEqual(module.main(['writer',module.BOOTSTRAP_FLAG]),0)
            fake.main.assert_called_once_with(['writer',module.BOOTSTRAP_FLAG],run_writer=module._run_verified_writer)
            self.assertEqual(sys.path[:2],[str(module.PROJECT_ROOT),str(module.RECOVERY_SITE_PACKAGES)])
            self.assertNotIn(str(module.QT_SITE_PACKAGES),sys.path[:2])
        finally:sys.path[:]=before

    def test_post_redemption_callback_keeps_dll_scope_through_writer_disposal(self):
        module=load_launcher();events=[];fake=types.ModuleType('native_studio.native_creative_entry')
        def run_writer(*args):
            self.assertEqual(os.environ['PATH'],module.QT_RUNTIME_PATH)
            self.assertNotIn('untrusted',os.environ['PATH'])
            events.append('writer');return 0
        fake._run_writer=Mock(side_effect=run_writer)
        dll=Mock();dll.__enter__=Mock(side_effect=lambda:events.append('dll-open'));dll.__exit__=Mock(side_effect=lambda *args:events.append('dll-close'))
        before=list(sys.path)
        try:
            with patch.dict(sys.modules,{'native_studio.native_creative_entry':fake}),patch.object(os,'add_dll_directory',return_value=dll)as add, \
                    patch.dict(os.environ,{'PATH':'C:/untrusted-provider-bin'}):
                self.assertEqual(module._run_verified_writer('session','packet'),0)
            add.assert_called_once_with(str(module.QT_DLL_DIRECTORY));fake._run_writer.assert_called_once_with('session','packet')
            self.assertEqual(events,['dll-open','writer','dll-close']);self.assertEqual(sys.path[0],str(module.QT_SITE_PACKAGES))
        finally:sys.path[:]=before


@unittest.skipUnless(os.name=='nt'and os.environ.get('AI_BS_FIXED_LAUNCHER_CUA')=='1',
    'Opt-in external CUA coordination required (AI_BS_FIXED_LAUNCHER_CUA=1)')
class FixedLauncherOwnedGui(unittest.TestCase):
    def test_fixed_actual_candidate_redemption_rich_read_and_normal_window_close(self):
        import _winapi
        from scripts.tests import test_native_creative_pipe_controller as fixture
        from scripts.tests.test_fdx_source_documents import XML,OWNER,fdx
        from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
        from security.firebase_auth import VerifiedFirebaseContext
        from security.native_creative_handoff import CreativeHandoffs
        from security.native_creative_controller import NativeCreativeController,ReviewedCandidate,PIPE_BOOTSTRAP_CONTRACT
        evidence=WORK/('native-fixed-launcher-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));evidence.mkdir()
        root=Path(tempfile.mkdtemp(prefix='native-fixed-launcher-',dir=ROOT/'t'));projects=root/'projects';projects.mkdir()
        project=projects/'Fixed Launcher Synthetic FDX';opening=fdx.import_project(project,XML,OWNER,uuid.uuid4().hex)
        before={p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in project.rglob('*')if p.is_file()}
        router=fixture.pdf.PdfWorkflowFixture();router.root=root;router.projects=projects
        ns=router.router_scope();ns.update(BaseModel=fixture.BaseModel,StrictInt=fixture.StrictInt)
        tree=ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8-sig'))
        nodes=[n for n in tree.body if getattr(n,'name','')in {'WriteScreenplayPayload','_issue_native_creative_grant'}]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual fixed-launcher grant/write payload>','exec'),ns)
        services=SimpleNamespace(**ns);observed=threading.Event();read=services.read_screenplay;responses=[]
        def observed_read(*args,**kwargs):
            value=read(*args,**kwargs);responses.append({'revision':value['revision'],'rich_document':value.get('source')=='rich_fdx'and isinstance(value.get('fdx_document'),dict)});observed.set();return value
        services.read_screenplay=observed_read
        names=('creative_session.py','creative_pipe_bootstrap.py','creative_pipe_transport.py','creative_pipe_io.py','creative_wire.py',
            'screenplay_client.py','native_creative_entry.py','screenwriting_view.py','engine.py','rich_screenplay_draft.py','theme.py')
        candidate=ReviewedCandidate(fixture.pin(sys._base_executable),
            ('-I','-B',str(LAUNCHER),'--native-creative-pipe-bootstrap'),str(ROOT),
            (('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1')),
            tuple(fixture.pin(p)for p in [LAUNCHER,*[ROOT/'native_studio'/name for name in names]]),PIPE_BOOTSTRAP_CONTRACT)
        controller=NativeCreativeController.create(candidate,CreativeHandoffs(),ns['_issue_native_creative_grant'],services=services)
        record=None;retained=None;report={'status':'RUNNING','scope':'Actual fixed launcher / synthetic owned rich source; external CUA desktop coordination, no real Firebase login',
            'candidate_sha256':candidate.sha256,'source_pins':[{'path':p.path,'sha256':p.sha256}for p in candidate.files],
            'fixture_root':str(root),'fixture_termination_requested':False,'original_hashes':before}
        try:
            deliver=controller._deliver
            def retain_before_delivery(owned,packet):
                nonlocal retained
                task_current=_winapi.GetCurrentProcess()
                retained=_winapi.DuplicateHandle(task_current,owned._lifetime.process.hp,task_current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
                return deliver(owned,packet)
            with patch.object(controller,'_deliver',side_effect=retain_before_delivery):
                record=controller.launch(VerifiedFirebaseContext(OWNER,time.monotonic()+180),project=project.name,
                    revision=opening['revision'],source_sha256=hashlib.sha256(XML).hexdigest())
            report['pid']=record.pid
            self.assertTrue(record._acked.wait(15));self.assertTrue(record.acknowledged)
            self.assertTrue(observed.wait(15));self.assertEqual(responses,[{'revision':opening['revision'],'rich_document':True}])
            self.assertEqual(_winapi.WaitForSingleObject(retained,0),258)
            # Desktop inspection and closing belong to the CUA tool. This test
            # publishes only exact owned-process readiness, then observes its
            # retained handle. It never enumerates or messages desktop windows.
            # Earlier raw Win32 UI witnesses remain historical; accepted desktop
            # qualification requires the separately recorded CUA interaction.
            ready=dict(report,status='READY_FOR_CUA_CLOSE',owned_child_pid=record.pid,
                acknowledged=True,read_responses=responses,expected_window_title='AI-BS — Connected Screenwriting Project',
                external_close_wait_seconds=90,ready_utc=datetime.now(timezone.utc).isoformat())
            readiness=evidence/'ready-for-cua.json'
            readiness.write_text(json.dumps(ready,indent=2)+'\n',encoding='utf-8')
            print('FIXED_LAUNCHER_READY='+str(readiness),flush=True)
            self.assertEqual(_winapi.WaitForSingleObject(retained,90000),0)
            report['normal_exit_after_external_cua_handoff']=True
            report['child_exit']=_winapi.GetExitCodeProcess(retained);self.assertEqual(report['child_exit'],0)
            closed=controller.close(record)
            if record._cleanup_worker is not None:record._cleanup_worker.join(timeout=3)
            report['controller']={'acknowledged':closed.acknowledged,'termination_requested':closed.termination_requested,'cleanup_failed':controller.cleanup_failed}
            self.assertTrue(closed.acknowledged);self.assertFalse(closed.termination_requested);self.assertFalse(controller.cleanup_failed)
            self.assertFalse(record._pipes._fds)
            after={p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in project.rglob('*')if p.is_file()}
            self.assertEqual(after,before);report['original_hashes_after']=after;report['read_responses']=responses
            report['status']='PASS'
        except BaseException as error:
            report['status']='FAILED_OR_INTERRUPTED';report['failure_class']=type(error).__name__;raise
        finally:
            if retained is not None:
                if _winapi.WaitForSingleObject(retained,0)==258:
                    report['fixture_termination_requested']=True;_winapi.TerminateProcess(retained,99);_winapi.WaitForSingleObject(retained,5000)
                report.setdefault('child_exit',_winapi.GetExitCodeProcess(retained))
                _winapi.CloseHandle(retained)
            if record is not None:controller.close(record)
            report['finished_utc']=datetime.now(timezone.utc).isoformat()
            (evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('FIXED_LAUNCHER_EVIDENCE='+str(evidence),flush=True)
if __name__=='__main__':unittest.main(verbosity=2)
