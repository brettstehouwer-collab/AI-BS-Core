import hashlib,os,struct,unittest,uuid,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from native_studio.game_engine.content_commands import ContentExportChunk,decode_content_export,export_content
from native_studio.game_engine.content_preview import ContentExportAssembly,encode_content_snapshot
from native_studio.game_engine.content_play import ContentPlayClient
from native_studio.game_engine.creator_payload import Scope,_Writer
from native_studio.game_engine.content_commands import ContentDescription
from native_studio.game_engine.content_preview import ContentSnapshot
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QApplication

class ContentProjectionTests(unittest.TestCase):
    def setUp(self):
        self.scope=Scope('project','main',str(uuid.uuid4()),str(uuid.uuid4()))
        self.data=b'AIBD content from native only';self.fp=hashlib.sha256(self.data).hexdigest()
        self.definition=str(uuid.uuid4());self.checkpoint=str(uuid.uuid4())
        self.description=ContentDescription(self.definition,3,self.fp,True,4)
    def test_chunk_assembly_is_pinned_to_every_context_field_and_hash(self):
        assembly=ContentExportAssembly(self.scope,7,12,self.checkpoint,self.description,())
        first=ContentExportChunk(self.definition,self.fp,3,len(self.data),0,self.data[:8])
        self.assertIsNone(assembly.accept(first,self.scope,7,12,self.checkpoint))
        self.assertEqual(assembly.offset,8)
        final=ContentExportChunk(self.definition,self.fp,3,len(self.data),8,self.data[8:])
        for args in ((self.scope,8,12,self.checkpoint),(self.scope,7,13,self.checkpoint),
                     (Scope('other','main',self.scope.world_id,self.scope.host_epoch),7,12,self.checkpoint),
                     (self.scope,7,12,str(uuid.uuid4()))):
            with self.assertRaises(ValueError):assembly.accept(final,*args)
        result=assembly.accept(final,self.scope,7,12,self.checkpoint)
        self.assertEqual(result.payload,self.data);self.assertEqual(result.fingerprint,self.fp)
        self.assertEqual(result.generation,7)
        bad=ContentExportAssembly(self.scope,7,12,self.checkpoint,self.description,())
        corrupt=ContentExportChunk(self.definition,self.fp,3,len(self.data),0,b'X'*len(self.data))
        with self.assertRaisesRegex(ValueError,'hash'):bad.accept(corrupt,self.scope,7,12,self.checkpoint)
    def test_export_codec_and_typed_viewport_envelope_are_bounded(self):
        body=_Writer();body.number(1,'H');body.text(self.definition,True);body.text(self.fp,True)
        body.number(3,'Q');body.number(len(self.data),'I');body.number(0,'I');body.number(len(self.data),'I');body.append(self.data)
        chunk=decode_content_export(bytes(body.data));self.assertEqual(chunk.payload,self.data)
        with self.assertRaises(ValueError):decode_content_export(bytes(body.data)+b'trailing')
        for offset,limit in ((-1,1),(0,0),(0,256*1024+1),(1024*1024+1,1)):
            with self.assertRaises(ValueError):export_content(self.scope,offset,limit,self.fp)
        encoded=encode_content_snapshot(str(uuid.uuid4()),self.scope,12,self.checkpoint,self.data,None)
        self.assertEqual(encoded[:7],b'AIBV'+struct.pack('<HB',1,2))
        self.assertTrue(encoded.endswith(struct.pack('<I',len(self.data))+self.data))
        self.assertGreater(len(encode_content_snapshot(str(uuid.uuid4()),self.scope,12,self.checkpoint,b'X'*(1024*1024),None)),1024*1024)
        with self.assertRaises(ValueError):encode_content_snapshot(str(uuid.uuid4()),self.scope,12,self.checkpoint,b'X'*(1024*1024+1),None)
    def test_invalid_play_protocol_cannot_be_repaired_into_a_graceful_claim(self):
        app=QApplication.instance() or QApplication([])
        client=ContentPlayClient();client.snapshot=ContentSnapshot(self.scope,7,12,self.checkpoint,
            self.definition,3,self.fp,self.data,frozenset());client.session_id=str(uuid.uuid4())
        client.state='ready'
        event={'event':'aibs.play.ready','play_session':client.session_id,'world_id':self.scope.world_id,
            'content_fingerprint':self.fp,'saved':True,'durable_revision':1}
        client._line(json.dumps(event).encode())
        with self.assertRaises(ValueError):client._line(json.dumps({**event,'play_session':str(uuid.uuid4())}).encode())
        client._stop_requested=True
        client._line(json.dumps({**event,'event':'aibs.play.stopped'}).encode())
        process=QProcess();client._process=process
        client._finished(process,0,QProcess.ExitStatus.NormalExit)
        self.assertFalse(client.last_result['graceful']);self.assertFalse(client.last_result['saved'])
        self.assertIn('another snapshot',client.last_result['reason'])
    def test_stdout_framing_error_after_receipt_invalidates_durability_claim(self):
        app=QApplication.instance() or QApplication([])
        client=ContentPlayClient();client.snapshot=ContentSnapshot(self.scope,7,12,self.checkpoint,
            self.definition,3,self.fp,self.data,frozenset());client.session_id=str(uuid.uuid4())
        client.state='stopping';client._ready_seen=True;client._stop_requested=True
        event={'event':'aibs.play.stopped','play_session':client.session_id,'world_id':self.scope.world_id,
            'content_fingerprint':self.fp,'saved':True,'durable_revision':1}
        class FaultingOutput:
            def __init__(self,data):self.data=bytearray(data);self.channel=QProcess.ProcessChannel.StandardOutput
            def setReadChannel(self,channel):self.channel=channel
            def bytesAvailable(self):return len(self.data) if self.channel==QProcess.ProcessChannel.StandardOutput else 0
            def read(self,count):result=bytes(self.data[:count]);del self.data[:count];return result
            def deleteLater(self):pass
        process=FaultingOutput(json.dumps(event).encode()+b'\n'+b'x'*8193+b'\n');client._process=process
        client._stdout(process);client._finished(process,0,QProcess.ExitStatus.NormalExit)
        self.assertFalse(client.last_result['graceful']);self.assertFalse(client.last_result['saved'])
        self.assertIn('line limit',client.last_result['reason'])

if __name__=='__main__':unittest.main()
