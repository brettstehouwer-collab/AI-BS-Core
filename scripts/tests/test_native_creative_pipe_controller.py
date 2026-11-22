"""Real suspended/job-owned v2 client + existing synthetic screenplay services."""
import ast
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sys
import sysconfig
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

from pydantic import BaseModel,StrictInt
from scripts.tests import test_chat_pdf_workflow as pdf
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_controller import NativeCreativeController, ReviewedCandidate, ReviewedFile, PIPE_BOOTSTRAP_CONTRACT, OwnedLaunch, NativeControllerError
from security.native_creative_handoff import CreativeHandoffs,CreativeScope,HandoffDenied

ROOT=pdf.ROOT
def pin(path):
    path=Path(path).resolve()
    return ReviewedFile(str(path),hashlib.sha256(path.read_bytes()).hexdigest())


@unittest.skipUnless(os.name=='nt','Windows owned jobs/inherited pipes')
class PipeControllerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=pdf.PdfWorkflowFixture();self.fixture._setupAsyncioRunner()
        self.addCleanup(self.fixture._tearDownAsyncioRunner);self.addCleanup(self.fixture.doCleanups)
        self.fixture._callSetUp()
        self.source=self.fixture.stage();self.opening=self.fixture.import_source(self.source,name='Pipe Project')
        self.directory=self.fixture.projects/'Pipe Project'
        self.source_before={name:(self.directory/name).read_bytes() for name in
            ('original.pdf','source_packet.json','source_exports/layout.fdx','source_exports/layout.pdf')}
        ns=self.fixture.router_scope();ns.update(BaseModel=BaseModel,StrictInt=StrictInt)
        tree=ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8-sig'))
        names={'WriteScreenplayPayload','_issue_native_creative_grant'}
        selected=[n for n in tree.body if getattr(n,'name','') in names]
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual native grant/write model>','exec'),ns)
        self.ns=ns;self.services=SimpleNamespace(**ns)
        self.grants=CreativeHandoffs();self.controller=None;self.record=None;self.retained=None
        self.addCleanup(self.cleanup_owned)

    def cleanup_owned(self):
        import _winapi
        # Exact retained synthetic test child only, never discovery by PID/port.
        if self.retained is not None:
            if _winapi.WaitForSingleObject(self.retained,0)==258:
                _winapi.TerminateProcess(self.retained,99)
            self.assertEqual(_winapi.WaitForSingleObject(self.retained,5000),0)
        if self.controller is not None and self.record is not None:
            self.controller.close(self.record)
            if self.record._cleanup_worker is not None:self.record._cleanup_worker.join(timeout=3)
        if self.retained is not None:
            _winapi.CloseHandle(self.retained);self.retained=None

    def launch(self,mode='save-exit',lifetime=60):
        import _winapi
        fixture=ROOT/'scripts/tests/fixtures/native_creative_pipe_child.py'
        dependencies=[fixture,*[ROOT/'native_studio'/name for name in
            ('creative_session.py','creative_pipe_bootstrap.py','creative_pipe_transport.py',
             'creative_pipe_io.py','creative_wire.py','screenplay_client.py')]]
        candidate=ReviewedCandidate(pin(sys._base_executable),
            ('-I','-B',str(fixture),str(ROOT),mode,sysconfig.get_path('purelib'),'--native-creative-pipe-bootstrap'),str(ROOT),
            (('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1')),
            tuple(pin(path) for path in dependencies),PIPE_BOOTSTRAP_CONTRACT)
        self.controller=NativeCreativeController.create(candidate,self.grants,self.ns['_issue_native_creative_grant'],services=self.services)
        deliver=self.controller._deliver
        def retain_before_delivery(record,packet):
            self.record=record
            current=_winapi.GetCurrentProcess()
            self.retained=_winapi.DuplicateHandle(current,record._lifetime.process.hp,current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
            return deliver(record,packet)
        with patch.object(self.controller,'_deliver',side_effect=retain_before_delivery):
            self.record=self.controller.launch(VerifiedFirebaseContext(pdf.OWNER,time.monotonic()+lifetime),
                project='Pipe Project',revision=self.opening['revision'],source_sha256=self.source['source_sha256'])
        return self.record

    def test_actual_owned_v2_read_save_readback_exit_and_cleanup(self):
        import _winapi
        record=self.launch()
        self.assertEqual(_winapi.WaitForSingleObject(self.retained,10000),0)
        self.assertEqual(_winapi.GetExitCodeProcess(self.retained),0)
        result=self.controller.close(record)
        self.assertTrue(result.acknowledged)
        self.assertFalse(result.termination_requested)
        self.assertIn('Synthetic owned pipe edit.',(self.directory/'screenplay.fountain').read_text(encoding='utf-8'))
        self.assertEqual(record._pipes._fds,set())
        self.assertIsNone(record._lifetime.process.hp)
        self.assertIsNone(record._lifetime.process.job)
        for name,original in self.source_before.items():self.assertEqual((self.directory/name).read_bytes(),original)

    def test_acknowledged_idle_client_survives_controller_close(self):
        import _winapi
        observed=threading.Event();read=self.services.read_screenplay
        def actual_read(*args,**kwargs):
            value=read(*args,**kwargs);observed.set();return value
        self.services.read_screenplay=actual_read
        record=self.launch('read-hold')
        self.assertTrue(observed.wait(10))
        self.assertTrue(record.acknowledged)
        result=self.controller.close(record)
        self.assertFalse(result.termination_requested)
        self.assertEqual(_winapi.WaitForSingleObject(self.retained,0),258)
        self.assertEqual(record._pipes._fds,set())

    def test_valid_lease_survives_more_than_thirty_seconds_idle_then_reads(self):
        import _winapi
        started=time.monotonic()
        record=self.launch('idle-read-exit',lifetime=90)
        self.assertEqual(_winapi.WaitForSingleObject(self.retained,40000),0)
        self.assertEqual(_winapi.GetExitCodeProcess(self.retained),0)
        self.assertGreater(time.monotonic()-started,30)
        self.assertTrue(self.controller.close(record).acknowledged)

    def test_expired_lease_revokes_channel_without_killing_acknowledged_child(self):
        import _winapi
        observed=threading.Event();read=self.services.read_screenplay
        def actual_read(*args,**kwargs):
            value=read(*args,**kwargs);observed.set();return value
        self.services.read_screenplay=actual_read
        record=self.launch('read-hold',lifetime=3)
        self.assertTrue(observed.wait(2))
        lease=record._dispatcher._lease
        self.assertTrue(record._service_done.wait(6))
        result=self.controller.close(record)
        self.assertTrue(result.acknowledged)
        self.assertFalse(result.termination_requested)
        self.assertEqual(_winapi.WaitForSingleObject(self.retained,0),258)
        with self.assertRaises(HandoffDenied):
            self.grants.authorize(lease,record.invocation,project='Pipe Project',operation='read')
        self.assertEqual(record._pipes._fds,set())

    def test_blocked_service_retains_resources_until_explicit_drain_retry(self):
        import _winapi
        entered=threading.Event();release=threading.Event();read=self.services.read_screenplay
        self.addCleanup(release.set)
        def blocked_read(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise RuntimeError('Synthetic blocking deadline')
            return read(*args,**kwargs)
        self.services.read_screenplay=blocked_read
        record=self.launch('read-hold')
        try:
            self.assertTrue(entered.wait(3))
            lease=record._dispatcher._lease
            with self.assertRaises(NativeControllerError):self.controller.close(record)
            self.assertIsNone(record._result)
            self.assertEqual(len(record._pipes._fds),2)
            self.assertIsNotNone(record._lifetime.process.hp)
            self.assertIn(record.invocation,self.controller._records)
            self.assertEqual(_winapi.WaitForSingleObject(self.retained,0),258)
            with self.assertRaises(HandoffDenied):
                self.grants.authorize(lease,record.invocation,project='Pipe Project',operation='read')
        finally:
            release.set()
        result=self.controller.close(record)
        self.assertTrue(result.acknowledged)
        self.assertFalse(result.termination_requested)
        self.assertEqual(record._pipes._fds,set())

    def test_interrupted_preflight_revokes_and_drains_owned_launch(self):
        original=self.ns['_issue_native_creative_grant']
        captured=[]
        def interrupted(context,invocation,*args,**kwargs):
            captured.append(invocation)
            original(context,invocation,*args,**kwargs)
            raise KeyboardInterrupt()
        self.ns['_issue_native_creative_grant']=interrupted
        with self.assertRaises(KeyboardInterrupt):self.launch('read-hold')
        self.assertEqual(len(captured),1)
        self.assertFalse(captured[0].alive())
        self.assertEqual(self.controller._pending,0)
        self.assertEqual(self.controller._records,{})
        self.assertEqual(self.grants._grants,{})


class CleanupRetentionTests(unittest.TestCase):
    def test_undrained_endpoint_prevents_descriptor_and_lifetime_release(self):
        controller=object.__new__(NativeCreativeController)
        controller._grants=MagicMock();controller._adapter=MagicMock();controller._lock=threading.Lock()
        controller._cleanup_failed=False;controller._records={}
        life=MagicMock();pins=MagicMock();pipes=MagicMock();endpoint=MagicMock()
        endpoint.close.return_value=False
        record=OwnedLaunch(controller,life,pins,CreativeScope('firebase:fixture:owner','project','r','a'*64,'b'*64),())
        record._pipes=pipes;record._endpoint=endpoint
        with self.assertRaises(NativeControllerError):controller.close(record)
        life.close.assert_not_called();pins.close.assert_not_called();pipes.close.assert_not_called()
        self.assertIsNone(record._result);self.assertTrue(controller.cleanup_failed)


if __name__=='__main__':unittest.main(verbosity=2)
