import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import time
import unittest
import uuid
import threading
from PyQt6.QtWidgets import QApplication

from native_studio.game_engine.creator_client import CreatorClient, ClientError
from native_studio.game_engine.creator_wire import Opcode, Frame
from native_studio.game_engine.creator_payload import Transaction, EditRequest, Create, SetField, encode_edit, decode_edit, _Writer
from native_studio.game_engine.creator_commands import Status, open_document, scoped, prepared_handle, history

EXE=Path(__file__).resolve().parents[1]/'install/release/bin/aibs_creator_host.exe'
UUID='01234567-89ab-4cde-8fab-0123456789ab'


class CreatorClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        if not EXE.is_file():
            raise RuntimeError('Build/install the actual native creator host before these integration tests')

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='aibs-qt-owner-')
        self.client=CreatorClient()
        self.responses={};self.failures={};self.closed=[]
        self.client.response.connect(lambda identity,value:self.responses.__setitem__(identity,value))
        self.client.request_failed.connect(lambda identity,message:self.failures.__setitem__(identity,message))
        self.client.closed.connect(self.closed.append)

    def spin(self,predicate,seconds=5):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.002)
        self.assertTrue(predicate(),f'Qt wait expired; state={self.client.state}, stderr={self.client.stderr_tail!r}')

    def start(self,create=True):
        self.client.start(EXE,Path(self.directory.name))
        self.spin(lambda:self.client.state=='ready')
        opened=self.call(Opcode.OPEN,open_document('project','main',(('x',-100.,100.),),create))
        self.assertEqual(opened.status,Status.OK)
        return opened.scope

    def call(self,opcode,payload=b'',revision=None):
        identity=self.client.request(opcode,payload,revision=revision)
        self.spin(lambda:identity in self.responses or identity in self.failures)
        self.assertNotIn(identity,self.failures)
        return self.responses[identity]

    def tearDown(self):
        self.client.stop()
        self.spin(lambda:self.client.state=='closed')
        self.assertEqual(self.client.process_id,0)
        self.client.deleteLater();self.app.processEvents();self.directory.cleanup()

    def test_actual_qprocess_save_restart_history_and_duplicate_head(self):
        scope=self.start();self.assertGreater(self.client.process_id,0)
        original=Transaction('create',0,'Cube',(Create('cube','Cube',UUID,(('x',0.),)),))
        self.assertEqual(self.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(scope,original)),0).status,Status.APPLIED)
        move=Transaction('move',1,'Move',(SetField('cube','x',7.,UUID),))
        preview=self.call(Opcode.PREVIEW,encode_edit(EditRequest(scope,move)),1)
        self.assertEqual(preview.status,Status.PREPARED)
        self.assertEqual(self.client.prepared_count,1)
        self.assertEqual(self.call(Opcode.APPLY_PREPARED,prepared_handle(scope,preview.token),1).status,Status.APPLIED)
        self.assertEqual(self.client.prepared_count,0)
        self.assertTrue(self.client.dirty)
        self.assertEqual(self.call(Opcode.SAVE,scoped(scope),2).status,Status.SAVED)
        self.assertFalse(self.client.dirty)
        self.assertEqual(self.call(Opcode.HISTORY,history(scope,'undo',False),2).status,Status.UNDONE)
        duplicate=self.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(scope,original)),0)
        self.assertEqual((duplicate.status,duplicate.head_revision,duplicate.operation_revision),(Status.DUPLICATE,3,1))
        self.assertEqual(self.client.head.head_revision,3)
        self.call(Opcode.SAVE,scoped(scope),3)
        old_epoch=self.client.epoch;old_generation=self.client.generation
        self.client.stop();self.spin(lambda:self.client.state=='closed')
        scope2=self.start(False)
        self.assertNotEqual(scope2.host_epoch,scope.host_epoch)
        self.assertEqual(scope2.world_id,scope.world_id)
        self.assertNotEqual(self.client.epoch,old_epoch)
        self.assertGreater(self.client.generation,old_generation)
        self.assertEqual(self.client.head.head_revision,3)

    def test_pending_count_and_byte_admission_before_event_pump(self):
        scope=self.start()
        ids=[self.client.request(Opcode.DESCRIBE,scoped(scope)) for _ in range(8)]
        self.assertEqual(self.client.pending_count,8)
        with self.assertRaises(ClientError):self.client.request(Opcode.DESCRIBE,scoped(scope))
        self.spin(lambda:self.client.pending_count==0)
        self.assertTrue(all(identity in self.responses for identity in ids))
        self.client.request(Opcode.DESCRIBE,b'x'*600000)
        with self.assertRaises(ClientError):self.client.request(Opcode.DESCRIBE,b'x'*600000)
        self.assertLessEqual(self.client.queued_bytes,1024*1024)
        self.spin(lambda:self.client.pending_count==0)

    def test_close_drains_known_requests_and_joins_owner(self):
        scope=self.start();identity=self.client.request(Opcode.DESCRIBE,scoped(scope))
        self.client.stop()
        with self.assertRaises(ClientError):self.client.request(Opcode.DESCRIBE,scoped(scope))
        self.spin(lambda:self.client.state=='closed')
        self.assertIn(identity,self.responses)
        self.assertEqual(self.client.uncertain_operations,())
        self.assertEqual(len(self.closed),1)
        self.assertEqual(self.closed[0],'Requested close')
        self.assertEqual(self.failures,{})

    def test_invalid_acknowledgement_preserves_pending_write_for_recovery(self):
        scope=self.start()
        tx=Transaction('pending',0,'Cube',(Create('cube','Cube',UUID,(('x',0.),)),))
        payload=encode_edit(EditRequest(scope,tx))
        identity=self.client.request(Opcode.APPLY_TRANSACTION,payload,revision=0)
        # Fault-inject an invalid acknowledgement while the actual owner is live.
        w=_Writer();w.number(1,'H');w.number(Status.PREPARED,'H');w.text('Wrong result kind')
        for value in (scope.host_epoch,scope.project,scope.branch,scope.world_id):w.text(value)
        w.number(0,'Q');w.text('');w.number(0,'Q');w.text('');w.text('');w.number(0,'B');w.number(0,'Q');w.text('Not assessed')
        w.number(0,'I');w.number(0,'Q');w.number(0,'Q');w.number(0,'I')
        with self.assertRaises(ClientError):
            self.client._accept_frame(Frame(Opcode.APPLY_TRANSACTION,identity,self.client.epoch,0,bytes(w.data),True),
                                      self.client._process,self.client.generation)
        self.assertEqual(self.client.pending_count,1)
        self.client.abort('Invalid acknowledgement')
        self.spin(lambda:self.client.state=='closed')
        self.assertEqual(self.client.uncertain_operations[0].transaction_payload,payload)

    def test_abort_retains_original_prepared_transaction_and_reconciles_explicitly(self):
        scope=self.start()
        self.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(scope,Transaction('base',0,'',(Create('cube','Cube',UUID,(('x',0.),)),)))),0)
        self.call(Opcode.SAVE,scoped(scope),1)
        tx=Transaction('unknown-move',1,'Keep exact bits',(SetField('cube','x',-0.,UUID),))
        preview=self.call(Opcode.PREVIEW,encode_edit(EditRequest(scope,tx)),1)
        identity=self.client.request(Opcode.APPLY_PREPARED,prepared_handle(scope,preview.token),revision=1)
        self.client.abort('Test interruption')
        self.spin(lambda:self.client.state=='closed')
        records=self.client.uncertain_operations
        self.assertEqual(len(records),1)
        self.assertEqual(decode_edit(records[0].transaction_payload).transaction,tx)
        self.assertEqual(records[0].transaction_payload,encode_edit(EditRequest(scope,tx)))
        self.assertEqual(records[0].request_id,identity)
        scope2=self.start(False)
        result=self.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(scope2,tx)),1)
        self.assertEqual(result.status,Status.APPLIED)
        self.client.acknowledge_recovery(records[0].generation,records[0].request_id)
        self.assertEqual(self.client.uncertain_operations,())

    def test_old_generation_reply_cannot_touch_reopened_client(self):
        scope=self.start();generation=self.client.generation
        self.client.stop();self.spin(lambda:self.client.state=='closed')
        self.start()
        head=self.client.head;count=len(self.responses)
        self.client._accept_frame(Frame(Opcode.DESCRIBE,1,bytes(16),0,b'',True),None,generation)
        self.assertIs(self.client.head,head)
        self.assertEqual(len(self.responses),count)
        self.assertEqual(self.client.state,'ready')

    def test_timeout_terminates_real_process_without_fabricating_reply(self):
        scope=self.start()
        identity=self.client.request(Opcode.DESCRIBE,scoped(scope))
        self.client._tick(now=time.monotonic()+30)
        self.spin(lambda:self.client.state=='closed')
        self.assertIn(identity,self.failures)
        self.assertNotIn(identity,self.responses)

    def test_missing_executable_rejects_without_spawning(self):
        with self.assertRaises(ClientError):self.client.start(EXE.with_name('missing-owner.exe'),Path(self.directory.name))
        self.assertEqual(self.client.state,'closed')
        self.assertEqual(self.client.process_id,0)

    def test_uint64_request_identity_survives_qt_signals(self):
        scope=self.start()
        self.client._sequence=(1<<63)-1
        identity=self.client.request(Opcode.DESCRIBE,scoped(scope))
        self.spin(lambda:bool(self.responses) and (identity in self.responses or self.client.pending_count==0))
        self.assertEqual(identity,1<<63)
        self.assertIn(identity,self.responses)

    def test_valid_large_transaction_uses_full_logical_queue_budget(self):
        scope=self.start()
        edits=tuple(Create('node-'+str(i),'N'*4096,str(uuid.uuid4()),(('x',0.),)) for i in range(160))
        payload=encode_edit(EditRequest(scope,Transaction('large',0,'Large bounded command',edits)))
        self.assertGreater(len(payload),512*1024)
        result=self.call(Opcode.APPLY_TRANSACTION,payload,0)
        self.assertEqual(result.status,Status.APPLIED)
        self.assertEqual(result.world_count,160)

    def test_worker_thread_cannot_mutate_qt_transport(self):
        scope=self.start();errors=[]
        def worker():
            try:self.client.request(Opcode.DESCRIBE,scoped(scope))
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=worker);thread.start();thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],ClientError)
        self.assertEqual(self.client.pending_count,0)


if __name__=='__main__':unittest.main()
