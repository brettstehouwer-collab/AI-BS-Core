import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile,time,unittest,uuid
import struct
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_client import ContentClient
from native_studio.game_engine.content_commands import (open_document,decode_description,decode_page,
    snapshot_page,encode_scoped_edit,decode_scoped_edit,edit_command,SetField,CreateFixture,EraseFixture,decode_preview,history,command_revision)
from native_studio.game_engine.creator_commands import Status,scoped,prepared_handle
from native_studio.game_engine.creator_payload import Scope,PayloadError
from native_studio.game_engine.creator_wire import Opcode

EXE=Path(os.environ.get('AIBS_CONTENT_HOST_EXE',Path(__file__).resolve().parents[1]/'out/windows-msvc/Debug/aibs_content_host.exe'))
class ContentCodecTests(unittest.TestCase):
    def test_revision_validation_and_foreign_wrapper_scope_reject(self):
        scope=Scope('typed','main',str(uuid.uuid4()),str(uuid.uuid4()))
        packet=encode_scoped_edit(scope,str(uuid.uuid4()),'edit',7,'ab'*32,'Label',(SetField(str(uuid.uuid4()),'x',-0.),))
        self.assertEqual(command_revision(edit_command(scope,packet)),7)
        with self.assertRaises(ValueError):edit_command(Scope('foreign','main',scope.world_id,scope.host_epoch),packet)
        with self.assertRaises(ValueError):command_revision(edit_command(scope,packet)+b'x')
    def test_typed_values_and_fixture_float32_roundtrip(self):
        scope=Scope('typed','main',str(uuid.uuid4()),str(uuid.uuid4()));uid=str(uuid.uuid4())
        values=(True,-7,.4,'Adam remembers \u2014 BS builds')
        packet=encode_scoped_edit(scope,str(uuid.uuid4()),'typed',0,'ab'*32,'Types',tuple(SetField(uid,'field'+str(i),v) for i,v in enumerate(values)))
        actual=tuple(edit.value for edit in decode_scoped_edit(packet).edits)
        self.assertEqual(actual,values);self.assertEqual(tuple(map(type,actual)),tuple(map(type,values)))
        fixture=CreateFixture(uid,'Seat');packet=encode_scoped_edit(scope,str(uuid.uuid4()),'fixture',0,'ab'*32,'Fixture',(fixture,))
        self.assertEqual(decode_scoped_edit(packet).edits[0].center[1],struct.unpack('<f',struct.pack('<f',.4))[0])
        with self.assertRaises(PayloadError):encode_scoped_edit(scope,str(uuid.uuid4()),'bad',0,'ab'*32,'Bad',(CreateFixture(uid,'Bad',emission=float('inf')),))
        with self.assertRaises(PayloadError):snapshot_page(scope,'',limit=33)

class ContentClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        if not EXE.is_file():raise RuntimeError('Build actual typed owner before running integration checks')
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='aibs-typed-client-');self.client=ContentClient()
        self.responses={};self.failures={};self.client.response.connect(lambda i,r:self.responses.__setitem__(i,r));self.client.request_failed.connect(lambda i,s:self.failures.__setitem__(i,s))
    def spin(self,predicate):
        end=time.monotonic()+12
        while not predicate() and time.monotonic()<end:self.app.processEvents();time.sleep(.003)
        self.assertTrue(predicate(),self.client.stderr_tail)
    def call(self,opcode,payload=b'',revision=None):
        i=self.client.request(opcode,payload,revision);self.spin(lambda:i in self.responses or i in self.failures)
        self.assertNotIn(i,self.failures);return self.responses[i]
    def start(self,create=True):
        self.client.start(EXE,Path(self.directory.name));self.spin(lambda:self.client.state=='ready')
        r=self.call(Opcode.OPEN,open_document('typed','main',create));self.assertEqual(r.status,Status.OK)
        return r.scope
    def rows(self,scope):
        result=[];cursor=''
        while True:
            reply=self.call(Opcode.SNAPSHOT_PAGE,snapshot_page(scope,self.client.head.checkpoint_id,cursor))
            rows,cursor,more=decode_page(reply.body);result.extend(rows)
            if not more:return tuple(result)
    def tearDown(self):
        self.client.stop();self.spin(lambda:self.client.state=='closed');self.assertEqual(self.client.process_id,0)
        self.client.deleteLater();self.app.processEvents();self.directory.cleanup()
    def test_real_typed_rows_preview_history_save_reopen(self):
        scope=self.start();description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body)
        rows=self.rows(scope);door=next(r for r in rows if r.type_id=='firstboot.Door' and dict(r.fields)['role']=='main')
        self.assertNotIn('unlocked',dict(door.fields));self.assertTrue(any(type(v) is str for r in rows for _,v in r.fields))
        packet=encode_scoped_edit(scope,description.definition_id,'door',0,description.fingerprint,'Move doorway',(SetField(door.uuid,'x',-32.5),))
        preview=self.call(Opcode.PREVIEW,edit_command(scope,packet),0);self.assertEqual(preview.status,Status.PREPARED,preview.message)
        self.assertTrue(preview.save_compatible);self.assertTrue(decode_preview(preview.body).collision_rebuild)
        self.assertEqual(self.client.head.head_revision,0)
        self.assertEqual(self.call(Opcode.APPLY_PREPARED,prepared_handle(scope,preview.token),0).status,Status.APPLIED)
        description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body)
        self.assertEqual(self.call(Opcode.HISTORY,history(scope,'undo',False,description.fingerprint),1).status,Status.UNDONE)
        self.assertEqual(self.call(Opcode.APPLY_TRANSACTION,edit_command(scope,packet),0).status,Status.DUPLICATE)
        self.call(Opcode.SAVE,scoped(scope));self.assertFalse(self.client.dirty)
        world=scope.world_id;head=self.client.head.head_revision
        self.client.stop();self.spin(lambda:self.client.state=='closed');scope2=self.start(False)
        self.assertEqual(scope2.world_id,world);self.assertNotEqual(scope2.host_epoch,scope.host_epoch);self.assertEqual(self.client.head.head_revision,head)
    def test_fixture_and_unknown_pending_transaction_retain_exact_bytes(self):
        scope=self.start();description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body)
        uid=str(uuid.uuid4());packet=encode_scoped_edit(scope,description.definition_id,'fixture',0,description.fingerprint,'Seat',(CreateFixture(uid,'Seat',center=(-35.,.4,10.),half_extent=(.4,.4,.4)),))
        preview=self.call(Opcode.PREVIEW,edit_command(scope,packet),0);self.assertEqual(preview.status,Status.PREPARED,preview.message)
        payload=prepared_handle(scope,preview.token);i=self.client.request(Opcode.APPLY_PREPARED,payload,0)
        self.client.abort('Typed pending write interrupted');self.spin(lambda:self.client.state=='closed')
        recovery=self.client.uncertain_operations;self.assertEqual(len(recovery),1)
        self.assertEqual(recovery[0].transaction_payload,edit_command(scope,packet));self.assertEqual(recovery[0].request_id,i)
    def test_real_fixture_create_delete_and_redo(self):
        scope=self.start();uid=str(uuid.uuid4())
        def apply(identity,edit):
            description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body);head=self.client.head.head_revision
            packet=encode_scoped_edit(scope,description.definition_id,identity,head,description.fingerprint,identity,(edit,))
            preview=self.call(Opcode.PREVIEW,edit_command(scope,packet),head);self.assertEqual(preview.status,Status.PREPARED,preview.message)
            self.assertEqual(self.call(Opcode.APPLY_PREPARED,prepared_handle(scope,preview.token),head).status,Status.APPLIED)
        apply('place',CreateFixture(uid,'BS workbench',center=(-35.,.4,10.)))
        self.assertEqual(next(row for row in self.rows(scope) if row.uuid==uid).name,'BS workbench')
        apply('remove',EraseFixture(uid));self.assertFalse(any(row.uuid==uid for row in self.rows(scope)))
        description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body)
        self.assertEqual(self.call(Opcode.HISTORY,history(scope,'undo-remove',False,description.fingerprint),2).status,Status.UNDONE)
        self.assertTrue(any(row.uuid==uid for row in self.rows(scope)))
        description=decode_description(self.call(Opcode.DESCRIBE,scoped(scope)).body)
        self.assertEqual(self.call(Opcode.HISTORY,history(scope,'redo-remove',True,description.fingerprint),3).status,Status.REDONE)
        self.assertFalse(any(row.uuid==uid for row in self.rows(scope)))

if __name__=='__main__':unittest.main()
