import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import json,tempfile,time,unittest
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_client import ContentClient
from native_studio.game_engine.content_jobs import ContentProposalJobs
from native_studio.game_engine.content_commands import open_document,decode_description,decode_page,snapshot_page,edit_command
from native_studio.game_engine.creator_commands import scoped,prepared_handle,Status
from native_studio.game_engine.creator_wire import Opcode

EXE=Path(__file__).resolve().parents[1]/'out/windows-msvc/Debug/aibs_content_host.exe'
class NativeContentJobTests(unittest.TestCase):
    def test_actual_owner_job_publishes_once_and_late_result_cannot_rebind(self):
        app=QApplication.instance() or QApplication([]);client=ContentClient();responses={};current=[]
        client.response.connect(lambda identity,reply:responses.__setitem__(identity,reply))
        jobs=ContentProposalJobs(client,lambda:tuple(current) if current else None)
        def wait(predicate):
            until=time.monotonic()+15
            while not predicate() and time.monotonic()<until:app.processEvents();time.sleep(.003)
            self.assertTrue(predicate(),client.stderr_tail)
        def call(opcode,payload,revision=None):
            identity=client.request(opcode,payload,revision);wait(lambda:identity in responses);return responses[identity]
        with tempfile.TemporaryDirectory() as directory:
            try:
                client.start(EXE,Path(directory));wait(lambda:client.state=='ready')
                opened=call(Opcode.OPEN,open_document('job-test','main',True));self.assertEqual(opened.status,Status.OK)
                scope=opened.scope;description=decode_description(call(Opcode.DESCRIBE,scoped(scope)).body)
                rows=[];cursor=''
                while True:
                    reply=call(Opcode.SNAPSHOT_PAGE,snapshot_page(scope,client.head.checkpoint_id,cursor))
                    page,cursor,more=decode_page(reply.body);rows.extend(page)
                    if not more:break
                current[:]=[description.definition_id,description.fingerprint,tuple(rows)]
                door=next(r for r in rows if r.type_id=='firstboot.Door' and dict(r.fields)['role']=='main')
                job,_=jobs.begin([door.uuid]);late,_=jobs.begin([door.uuid])
                source=json.dumps({'version':1,'label':'Scoped async job','edits':[{'entity_id':door.uuid,'field':'x','value':-32.5}]})
                packet=jobs.consume(job,source)
                preview=call(Opcode.PREVIEW,edit_command(scope,packet),0);self.assertEqual(preview.status,Status.PREPARED,preview.message)
                result=call(Opcode.APPLY_PREPARED,prepared_handle(scope,preview.token),0);self.assertEqual(result.status,Status.APPLIED)
                description=decode_description(call(Opcode.DESCRIBE,scoped(scope)).body);current[1]=description.fingerprint
                with self.assertRaises(ValueError):jobs.consume(late,source)
                self.assertEqual(jobs.pending_count,0)
                self.assertEqual(call(Opcode.SAVE,scoped(scope)).status,Status.SAVED)
                jobs.begin([door.uuid]);client.stop();wait(lambda:client.state=='closed')
                self.assertEqual(jobs.pending_count,0);self.assertEqual(client.process_id,0)
            finally:
                client.stop();wait(lambda:client.state=='closed');client.deleteLater();app.processEvents()

if __name__=='__main__':unittest.main()
