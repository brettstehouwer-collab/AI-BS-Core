"""Actual offscreen rich GUI over owned v2 pipes and synthetic screenplay stores.

No HTTP service, provider, Firebase credential lookup, original document or focus
interaction. Candidate pins cover listed source only, not the whole DLL closure.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import sysconfig
import time
import unittest
from unittest.mock import patch

from scripts.tests import test_native_creative_pipe_controller as controller_fixture
from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_controller import NativeCreativeController,ReviewedCandidate,PIPE_BOOTSTRAP_CONTRACT
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal

MARKER='NATIVE PIPE GUI FIXTURE EDIT'
pin,ROOT,pdf=controller_fixture.pin,controller_fixture.ROOT,controller_fixture.pdf
SOURCE_FILES=('original.pdf','source_packet.json','source_exports/layout.fdx','source_exports/layout.pdf')
WORK=Path('C:/Users/Administrator/Documents/Codex/2026-11-10/c-ai-bs/work')


def validate_export_artifacts(evidence,report):
    """Independent read-only export verification, reusable without GUI replay."""
    import xml.etree.ElementTree as ET
    import fitz
    phases=report['phases']
    if len(phases)!=2 or phases[0]['pid']==phases[1]['pid']:raise AssertionError('Fresh process evidence missing')
    for phase in phases:
        if (phase['status']!='PASS' or phase['child_exit']!=0
                or phase['fixture_termination_requested']
                or not phase['controller_result']['acknowledged']
                or phase['controller_result']['termination_requested']):raise AssertionError('Lifecycle evidence missing')
    first,second=(p['child_result']for p in phases)
    if not first['saved_edit_present'] or not second['reopened_edit_present']:raise AssertionError('Edit readback missing')
    exports={}
    for fmt in ('fdx','pdf'):
        path=Path(evidence)/'reopen-export'/('reformatted.'+fmt)
        raw=path.read_bytes();receipt=second['exports'][fmt]
        digest=hashlib.sha256(raw).hexdigest()
        if len(raw)!=receipt['bytes'] or digest!=receipt['sha256']:raise AssertionError('Export bytes changed')
        if fmt=='fdx':
            document=ET.fromstring(raw)
            if document.tag!='FinalDraft':raise AssertionError('FDX document type')
            text=' '.join(document.itertext())
        else:
            with fitz.open(stream=raw,filetype='pdf')as document:
                text=' '.join(page.get_text()for page in document)
        if MARKER not in ' '.join(text.split()):raise AssertionError('Export lost edit')
        exports[fmt]={'bytes':len(raw),'sha256':digest,'edit_present':True}
    return {'status':'PASS','exports':exports,'fresh_processes':True,'normal_exit_zero':True,
            'fixture_or_controller_termination':False,'scope':'Frozen actual GUI phase evidence and independent export readback; no GUI replay'}


@unittest.skipUnless(os.name=='nt','Windows owned GUI workflow')
class NativePipeGuiWorkflow(unittest.TestCase):
    def setUp(self):
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.evidence=WORK/('native-pipe-gui-'+stamp);self.evidence.mkdir(exist_ok=False)
        self.report={'started_utc':datetime.now(timezone.utc).isoformat(),'status':'RUNNING',
            'scope':'Real offscreen writer / real owned v2 jobs / synthetic stores; no HTTP or original data',
            'source_pins_limited_import_closure':True,'phases':[],'failure':None}
        self.host=controller_fixture.PipeControllerTests();self.host.setUp()
        self.addCleanup(self.host.doCleanups)
        self.addCleanup(self.persist)
        self.originals={name:hashlib.sha256((self.host.directory/name).read_bytes()).hexdigest()for name in SOURCE_FILES}
        self.report['original_source_sha256']=self.originals

    def persist(self):
        if self.report['status']=='RUNNING':self.report['status']='FAILED_OR_INTERRUPTED'
        self.report['finished_utc']=datetime.now(timezone.utc).isoformat()
        (self.evidence/'result.json').write_text(json.dumps(self.report,indent=2)+'\n',encoding='utf-8')
        print('PIPE_GUI_EVIDENCE='+str(self.evidence),flush=True)

    def current(self):
        token=bind_memory_principal(pdf.OWNER)
        try:return self.host.services.read_screenplay(project_name='Pipe Project')
        finally:reset_memory_principal(token)

    def receive(self,connection):
        raw=bytearray()
        while not raw.endswith(b'\n'):
            if len(raw)>=8192:raise AssertionError('Coordination bound')
            block=connection.recv(8192-len(raw))
            if not block:raise AssertionError('Coordination EOF')
            raw.extend(block)
        value=json.loads(bytes(raw))
        self.assertIs(type(value),dict)
        return value

    def run_phase(self,phase):
        import _winapi
        item={'phase':phase,'status':'STARTING','fixture_termination_requested':False,
              'child_exit':None,'controller_result':None}
        self.report['phases'].append(item)
        directory=self.host.fixture.root/phase;directory.mkdir(exist_ok=False)
        self.assertTrue(directory.resolve().is_relative_to((ROOT/'t').resolve()))
        destination=self.evidence/phase;destination.mkdir(exist_ok=False)
        coordination=socket.socket();coordination.bind(('127.0.0.1',0));coordination.listen(1)
        coordination.settimeout(.2);connection=None;record=None
        try:
            # The real grant store admits one launch per owner per second.
            # Wait for that known interval BEFORE creating the next candidate;
            # do not retry a refused launch or weaken its admission policy.
            with self.host.grants._lock:
                issued=self.host.grants._issued.get(pdf.OWNER)
                delay=0 if issued is None else max(0,issued+1.02-self.host.grants._clock())
            self.assertLessEqual(delay,1.02)
            item['grant_admission_wait_seconds']=delay
            if delay:time.sleep(delay)
            self.host.record=None
            fixture=ROOT/'scripts/tests/fixtures/native_creative_pipe_gui_child.py'
            names=('creative_session.py','creative_pipe_bootstrap.py','creative_pipe_transport.py',
                'creative_pipe_io.py','creative_wire.py','screenplay_client.py','native_creative_entry.py',
                'screenwriting_view.py','engine.py','rich_screenplay_draft.py','theme.py')
            dependencies=[fixture,*[ROOT/'native_studio'/name for name in names]]
            qt=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin'
            environment=(('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1'),
                ('PATH',str(qt)+';'+str(Path(os.environ['SYSTEMROOT'])/'System32')))
            arguments=('-I','-B',str(fixture),phase,str(coordination.getsockname()[1]),str(directory),
                       sysconfig.get_path('purelib'),'--native-creative-pipe-bootstrap')
            candidate=ReviewedCandidate(pin(sys._base_executable),arguments,str(ROOT),environment,
                tuple(pin(path)for path in dependencies),PIPE_BOOTSTRAP_CONTRACT)
            item['candidate_sha256']=candidate.sha256
            item['source_pins']=[{'path':p.path,'sha256':p.sha256}for p in candidate.files]
            self.host.controller=NativeCreativeController.create(candidate,self.host.grants,
                self.host.ns['_issue_native_creative_grant'],services=self.host.services)
            deliver=self.host.controller._deliver
            def retain_before_delivery(owned,payload):
                self.host.record=owned
                current=_winapi.GetCurrentProcess()
                self.host.retained=_winapi.DuplicateHandle(current,owned._lifetime.process.hp,
                    current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
                return deliver(owned,payload)
            snapshot=self.current()
            with patch.object(self.host.controller,'_deliver',side_effect=retain_before_delivery):
                record=self.host.controller.launch(VerifiedFirebaseContext(pdf.OWNER,time.monotonic()+240),
                    project='Pipe Project',revision=snapshot['revision'],source_sha256=self.host.source['source_sha256'])
            self.host.record=record;item['pid']=record.pid
            deadline=time.monotonic()+12
            while connection is None:
                try:connection,_=coordination.accept()
                except socket.timeout:
                    if time.monotonic()>=deadline:raise TimeoutError('Child coordination readiness')
                    if _winapi.WaitForSingleObject(self.host.retained,0)==0:raise AssertionError('Child exited before ready')
            connection.settimeout(45)
            ready=self.receive(connection);item['ready']=ready
            self.assertEqual(ready.get('kind'),'ready',ready)
            self.assertEqual(ready.get('pid'),record.pid)
            self.assertTrue(ready.get('bootstrap_before_qt'))
            self.assertTrue(ready.get('pipe_mode'));self.assertEqual(ready.get('http_calls'),0)
            connection.sendall(b'R')
            completed=self.receive(connection);item['child_result']=completed
            self.assertEqual(completed.get('kind'),'complete',completed)
            self.assertEqual(completed.get('pid'),record.pid)
            for field in ('actual_rich_writer','only_writing_page','gui_worker_drained',
                          'session_cleared_after_close','adopted_descriptors_closed','close_retained_until_channel_drain'):
                self.assertIs(completed.get(field),True,field)
            self.assertEqual(completed.get('http_calls'),0)
            self.assertEqual(completed.get('forbidden_modules_loaded'),[])
            connection.sendall(b'X')
            self.assertEqual(_winapi.WaitForSingleObject(self.host.retained,10000),0)
            item['child_exit']=_winapi.GetExitCodeProcess(self.host.retained)
            self.assertEqual(item['child_exit'],0)
            result=self.host.controller.close(record)
            item['controller_result']={'acknowledged':result.acknowledged,
                'termination_requested':result.termination_requested,'job_drained':result.job_drained}
            self.assertTrue(result.acknowledged);self.assertFalse(result.termination_requested)
            self.assertEqual(record._pipes._fds,set())
            self.assertIsNone(record._lifetime.process.hp);self.assertIsNone(record._lifetime.process.job)
            if record._cleanup_worker is not None:
                record._cleanup_worker.join(timeout=3);self.assertFalse(record._cleanup_worker.is_alive())
            self.assertFalse(self.host.controller.cleanup_failed)
            item['source_sha256_after']={name:hashlib.sha256((self.host.directory/name).read_bytes()).hexdigest()
                                        for name in SOURCE_FILES}
            self.assertEqual(item['source_sha256_after'],self.originals)
            item['status']='PASS'
            return completed
        except BaseException as error:
            item['status']='FAILED';item['failure_class']=type(error).__name__
            self.report['failure']={'phase':phase,'exception_class':type(error).__name__}
            raise
        finally:
            if connection is not None:connection.close()
            coordination.close()
            if self.host.retained is not None:
                if _winapi.WaitForSingleObject(self.host.retained,2000)==258:
                    item['fixture_termination_requested']=True
                    _winapi.TerminateProcess(self.host.retained,99)
                    self.assertEqual(_winapi.WaitForSingleObject(self.host.retained,5000),0)
                item['child_exit']=_winapi.GetExitCodeProcess(self.host.retained)
                _winapi.CloseHandle(self.host.retained);self.host.retained=None
            if self.host.record is not None:
                try:self.host.controller.close(self.host.record)
                except Exception as cleanup:item['cleanup_exception_class']=type(cleanup).__name__
            for name in ('result.json','failure.json','reformatted.fdx','reformatted.pdf'):
                source=directory/name
                if source.is_file():shutil.copy2(source,destination/name)

    def test_actual_rich_gui_save_fresh_process_reopen_and_explicit_exports(self):
        first=self.run_phase('edit-save')
        self.assertTrue(first['saved_edit_present'])
        self.assertEqual(self.current()['revision'],first['saved_revision'])
        second=self.run_phase('reopen-export')
        self.assertTrue(second['reopened_edit_present'])
        self.assertNotEqual(self.report['phases'][0]['pid'],self.report['phases'][1]['pid'])
        self.report['independent_export_validation']=validate_export_artifacts(self.evidence,self.report)
        self.assertFalse(any(p['fixture_termination_requested']for p in self.report['phases']))
        self.report['status']='PASS'

    def test_fresh_gui_restores_private_unsaved_draft_without_host_write(self):
        before=self.current()
        first=self.run_phase('draft-preserve')
        self.assertTrue(first['recovery_preserved'])
        self.assertEqual(self.current(),before)
        second=self.run_phase('draft-restore')
        self.assertTrue(second['recovery_restored'])
        self.assertFalse(second['rich_document_loaded'])
        self.assertNotEqual(self.report['phases'][0]['pid'],self.report['phases'][1]['pid'])
        self.assertEqual(self.current(),before)
        self.assertFalse(any(p['fixture_termination_requested']for p in self.report['phases']))
        self.report['host_unchanged_after_restore']=True
        self.report['status']='PASS'


if __name__=='__main__':unittest.main(verbosity=2)
