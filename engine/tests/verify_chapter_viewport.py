"""Actual immutable export and optional DX12 chapter projection proof."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from verify_creator_process import Peer
from native_studio.game_engine.creator_wire import Opcode
from native_studio.game_engine.creator_commands import Status,scoped,prepared_handle
from native_studio.game_engine.creator_payload import _Reader,_Writer
from native_studio.game_engine.content_commands import open_document,decode_description,decode_page,snapshot_page,encode_scoped_edit,edit_command,SetField,decode_content_export

def request(scope,fingerprint,offset=0,limit=8192,tag=1):
    w=_Writer();w.append(scoped(scope));w.number(tag,'B');w.number(offset,'I');w.number(limit,'I');w.text(fingerprint,True);return bytes(w.data)
def chunk(data):
    r=_Reader(data);assert r.number('H')==1
    definition,fp,version,total,offset,n=r.text(True),r.text(True),r.number('Q'),r.number('I'),r.number('I'),r.number('I')
    blob=r.read(n);assert r.offset==len(data) and total<=1024*1024 and offset+n<=total
    return definition,fp,version,total,offset,blob
def verify(executable,output,viewport=None):
    output.mkdir(parents=True,exist_ok=True);checks=0
    def check(value,why):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(why)
    with tempfile.TemporaryDirectory(prefix='aibs-export-') as temporary:
        root=Path(temporary);peer=Peer(executable,root)
        try:
            hello=peer.call(Opcode.HELLO);reader=_Reader(hello.body)
            check({'chapter-content-export-v1','chapter-content-export-v2'}<=set(reader.text().split(';')),'immutable legacy/complete export capabilities missing')
            head=peer.call(Opcode.OPEN,open_document('chapter-export','main',True));check(head.status==Status.OK,'open')
            desc=decode_description(peer.call(Opcode.DESCRIBE,scoped(head.scope),0).body)
            def export(head,description,complete=False):
                result=b'';total=None
                while total is None or len(result)<total:
                    reply=peer.call(Opcode.DESCRIBE,request(head.scope,description.fingerprint,len(result),tag=2 if complete else 1),head.head_revision)
                    check(reply.status==Status.OK,'export chunk response')
                    if complete:
                        decoded=decode_content_export(reply.body)
                        check(decoded.version==2 and decoded.dependencies==(),'Complete export declares the exact empty dependency closure')
                        definition,fp,version,total,offset,blob=decoded.definition_id,decoded.fingerprint,decoded.content_revision,decoded.total,decoded.offset,decoded.payload
                    else:definition,fp,version,total,offset,blob=chunk(reply.body)
                    check((definition,fp,version)==(description.definition_id,description.fingerprint,description.content_revision),'pinned immutable export identity')
                    check(offset==len(result) and len(blob)>0 and len(blob)<=8192,'ordered bounded export')
                    result+=blob
                check(result[:4]==b'AIBD' and len(result)==total,'complete native content definition')
                check(hashlib.sha256(result).hexdigest()==description.fingerprint,'content bytes match pinned native fingerprint');return result
            original=export(head,desc)
            check(export(head,desc,True)==original,'Complete export preserves exact legacy AIBD bytes')
            for tag in (1,2):
                for body in (request(head.scope,desc.fingerprint,limit=0,tag=tag),request(head.scope,desc.fingerprint,limit=262145,tag=tag),request(head.scope,desc.fingerprint,offset=len(original)+1,tag=tag),request(head.scope,'0'*64,tag=tag),request(head.scope,desc.fingerprint,tag=255),request(head.scope,desc.fingerprint,tag=tag)+b'x',request(replace(head.scope,branch='foreign'),desc.fingerprint,tag=tag),request(replace(head.scope,world_id='22222222-2222-4222-8222-222222222222'),desc.fingerprint,tag=tag)):
                    check(peer.call(Opcode.DESCRIBE,body,0).status==Status.REJECTED,'invalid export rejected')
            check(peer.call(Opcode.DESCRIBE,request(head.scope,desc.fingerprint),0,epoch=bytes(16)).status==Status.REJECTED,'foreign export process epoch')
            final=peer.call(Opcode.DESCRIBE,request(head.scope,desc.fingerprint,len(original),262144),0)
            check(final.status==Status.OK and chunk(final.body)[-1]==b'','terminal offset produces no extra bytes')
            rows=[];cursor=''
            while True:
                reply=peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(head.scope,'',cursor),0);page,cursor,more=decode_page(reply.body);rows.extend(page)
                if not more:break
            door=next(r for r in rows if r.type_id=='firstboot.Door' and dict(r.fields)['role']=='main')
            fixture=next(r for r in rows if r.type_id=='authoring.Fixture' and max(dict(r.fields)[k] for k in ('half_x','half_y','half_z'))<2)
            packet=encode_scoped_edit(head.scope,desc.definition_id,'export-proof',0,desc.fingerprint,'Authored doorway',(SetField(door.uuid,'x',-32.5),))
            prepared=peer.call(Opcode.PREVIEW,edit_command(head.scope,packet),0);check(prepared.status==Status.PREPARED,'private candidate')
            check(export(head,desc)==original,'preview cannot leak private content')
            head=peer.call(Opcode.APPLY_PREPARED,prepared_handle(head.scope,prepared.token),0);check(head.status==Status.APPLIED,'publish')
            check(peer.call(Opcode.DESCRIBE,request(head.scope,desc.fingerprint),1).status==Status.REJECTED,'old fingerprint rejected')
            check(peer.call(Opcode.DESCRIBE,scoped(head.scope),0).status==Status.REJECTED,'old head rejected')
            desc=decode_description(peer.call(Opcode.DESCRIBE,scoped(head.scope),1).body);content=export(head,desc)
            check(export(head,desc,True)==content,'Both export contracts preserve the current edited definition')
            check(content!=original,'export reflects actual edited definition');check(not (root/'chapter.aiba').exists(),'export never autosaves')
            content_path=output/'chapter-export.aibd';content_path.write_bytes(content)
            snapshot_id='11111111-1111-4111-8111-111111111111';w=_Writer();w.append(b'AIBV');w.number(1,'H');w.number(2,'B')
            for value in (snapshot_id,head.scope.project,head.scope.branch,head.scope.world_id,head.checkpoint_id):w.text(value)
            w.number(head.head_revision,'Q');w.text(fixture.uuid);w.number(len(content),'I');envelope=bytes(w.data)+content
            source=output/'chapter-preview.aibv';source.write_bytes(envelope)
            gpu=None
            if viewport is not None:
                stop=output/'chapter-preview.stop';check(not stop.exists(),'fresh probe stop path')
                run=subprocess.run([str(viewport),'--snapshot',str(source),'--stop-file',str(stop),'--self-test','--capture',str(output/'chapter-preview.bmp'),'--report',str(output/'chapter-preview.json')],capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                check(run.returncode==0,'DX12 chapter preview: '+run.stderr)
                gpu=json.loads((output/'chapter-preview.json').read_text())
                check(gpu['selected_uuid']==fixture.uuid and gpu['nonbackground_pixels']>500 and gpu['debug_errors']==0,'actual rendered/clicked authored fixture')
                check(f'AIBV1 READY {snapshot_id} {head.scope.world_id} 1' in run.stdout and f'AIBV1 PICK {snapshot_id} {head.scope.world_id} 1 {fixture.uuid}' in run.stdout,'correlated native READY/PICK')
        finally:peer.close()
    return {'status':'passed','checks':checks,'content_sha256':hashlib.sha256(content).hexdigest(),'content_fingerprint':desc.fingerprint,'content_bytes':len(content),'world_id':head.scope.world_id,'selected_uuid':fixture.uuid,'gpu':gpu}
if __name__=='__main__':
    report=verify(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]) if len(sys.argv)>3 else None)
    (Path(sys.argv[2])/'chapter-export-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
