"""Interactive typed-owner proof; synthetic workspaces, no player saves."""
from pathlib import Path
from dataclasses import replace
import json,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from verify_creator_process import Peer
from native_studio.game_engine.creator_wire import Opcode,UNSCOPED_REVISION
from native_studio.game_engine.creator_commands import Status,scoped,prepared_handle,snapshot_page
from native_studio.game_engine.creator_payload import _Reader,_Writer
from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal

def opened(project='typed-proof',branch='main',create=True):
    w=_Writer();w.number(1,'H');w.text(project,True);w.text(branch,True);w.number(create,'B');return bytes(w.data)
def description(reply):
    r=_Reader(reply.body);value=(r.text(True),r.number('Q'),r.text(True),r.number('B'),r.number('I'))
    assert r.offset==len(reply.body);return value
def page(reply):
    r=_Reader(reply.body);cursor=r.text();more=r.number('B');count=r.number('I');rows=[]
    for _ in range(count):
        uid,kind,name=r.text(True),r.text(True),r.text();fields={}
        for _ in range(r.number('I')):
            key=r.text(True);tag=r.number('B')
            fields[key]=r.number('B') if tag==0 else r.number('q') if tag==1 else r.number('d') if tag==2 else r.text() if tag==3 else (_ for _ in ()).throw(ValueError('tag'))
        rows.append((uid,kind,name,fields))
    assert r.offset==len(reply.body);return cursor,bool(more),rows
def command(scope,blob):
    w=_Writer();w.append(scoped(scope));w.number(len(blob),'I');w.append(blob);return bytes(w.data)
def history(scope,identity,fingerprint,redo=False):
    w=_Writer();w.append(scoped(scope));w.text(identity,True);w.number(redo,'B');w.text(fingerprint,True);return bytes(w.data)

def verify(exe):
    checks=0
    def check(condition,why):
        nonlocal checks
        checks+=1
        if not condition:raise AssertionError(why)
    with tempfile.TemporaryDirectory(prefix='aibs-content-peer-') as temp:
        root=Path(temp);(root/'world.aibs').write_bytes(b'Unrelated retained player/authoring file')
        peer=Peer(exe,root)
        try:
            check(peer.call(Opcode.OPEN,opened()).status==Status.REJECTED,'Hello required')
            hello=peer.call(Opcode.HELLO);r=_Reader(hello.body)
            check('chapter-authoring-v1' in r.text().split(';'),'typed capability')
            check(r.number('I')==1024*1024 and r.number('I')==8,'bounded negotiation')
            check(peer.call(Opcode.OPEN,opened()+b'extra').status==Status.REJECTED,'trailing Open rejects')
            head=peer.call(Opcode.OPEN,opened());check(head.status==Status.OK,'create native template')
            check(not (root/'chapter.aiba').exists(),'no implicit initial save')
            describe=peer.call(Opcode.DESCRIBE,scoped(head.scope),head.head_revision);definition,version,fp,dirty,known=description(describe)
            check(version==0 and dirty==1 and known>0,'description actual content/head')
            cursor='';rows=[]
            while True:
                response=peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(head.scope,head.checkpoint_id,cursor,32),head.head_revision)
                check(response.status==Status.OK,'typed page')
                cursor,more,next_rows=page(response);rows.extend(next_rows)
                if not more:break
            check(len(rows)==head.world_count and len({row[0] for row in rows})==len(rows),'complete unique UUID page snapshot')
            check(max(len(row[3]) for row in rows)>64,'typed settings retain more than numeric-entity field limit')
            door=next(row for row in rows if row[1]=='firstboot.Door' and row[3].get('role')=='main')
            check('unlocked' not in door[3] and 'open' not in door[3],'runtime fields not exposed')
            context=ProposalContext.from_dict({'project':head.scope.project,'branch':head.scope.branch,'world_id':head.scope.world_id,'definition_id':definition,'revision':head.head_revision,'fingerprint':fp,'fields':[[door[0],'x','number']]})
            blob=encode_proposal(json.dumps({'version':1,'label':'Move doorway','edits':[{'entity_id':door[0],'field':'x','value':-32.5}]}),context,'typed-move')
            preview=peer.call(Opcode.PREVIEW,command(head.scope,blob),0)
            check(preview.status==Status.PREPARED and preview.save_compatible and preview.save_bytes>0,'private prepared authoring-save assessment')
            check(preview.head_revision==0,'preview does not publish')
            check(preview.body[:5]==bytes([0,1,1,1,1]),'real dependencies/new gameplay branch distinct from document save')
            check(peer.call(Opcode.APPLY_TRANSACTION,command(head.scope,blob)+b'extra',0).status==Status.REJECTED,'trailing edit wrapper rejects before publication')
            check(peer.call(Opcode.APPLY_TRANSACTION,command(head.scope,blob),1).status==Status.REJECTED,'frame/request head mismatch rejects')
            check(peer.call(Opcode.DESCRIBE,scoped(head.scope),0,epoch=bytes(16)).status==Status.REJECTED,'wrong process epoch rejects')
            wrong=replace(context,branch='other-branch')
            foreign=encode_proposal(json.dumps({'version':1,'label':'Wrong branch','edits':[{'entity_id':door[0],'field':'x','value':-32.5}]}),wrong,'foreign')
            check(peer.call(Opcode.APPLY_TRANSACTION,command(head.scope,foreign),0).status==Status.REJECTED,'inner AIBP and command scope must agree')
            forged=replace(context,fields=((door[0],'unlocked','boolean'),))
            runtime=encode_proposal(json.dumps({'version':1,'label':'No fake progress','edits':[{'entity_id':door[0],'field':'unlocked','value':True}]}),forged,'forged-state')
            check(peer.call(Opcode.APPLY_TRANSACTION,command(head.scope,runtime),0).status==Status.REJECTED,'engine denies runtime flag even if controller capability is forged')
            applied=peer.call(Opcode.APPLY_PREPARED,prepared_handle(head.scope,preview.token),0)
            check(applied.status==Status.APPLIED and applied.head_revision==1,'apply grouped edit')
            duplicate=peer.call(Opcode.APPLY_TRANSACTION,command(head.scope,blob),0)
            check(duplicate.status==Status.DUPLICATE and duplicate.head_revision==1,'exact old transaction retry')
            check(peer.call(Opcode.APPLY_PREPARED,prepared_handle(head.scope,preview.token),1).status==Status.REJECTED,'applied token expires')
            desc=description(peer.call(Opcode.DESCRIBE,scoped(head.scope),1));fp1=desc[2]
            undone=peer.call(Opcode.HISTORY,history(head.scope,'typed-undo',fp1),1)
            check(undone.status==Status.UNDONE and undone.head_revision==2,'history typed undo')
            check(description(peer.call(Opcode.DESCRIBE,scoped(head.scope),2))[2]==fp,'undo exact definition')
            redone=peer.call(Opcode.HISTORY,history(head.scope,'typed-redo',fp,True),2)
            check(redone.status==Status.REDONE and redone.head_revision==3,'redo')
            saved=peer.call(Opcode.SAVE,scoped(head.scope),3)
            check(saved.status==Status.SAVED and (root/'chapter.aiba').is_file(),'explicit authoring save')
            checkpoint=saved.checkpoint_id;world=head.scope.world_id;before=(root/'chapter.aiba').read_bytes()
            check(peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(head.scope,'','',32),3).status==Status.REJECTED,'saved checkpoint paging guard')
            check(peer.call(Opcode.START_PLAY,scoped(head.scope),3).status==Status.REJECTED,'unfinished Play explicitly rejects')
            check(peer.call(Opcode.SAVE,scoped(head.scope)+b'extra',3).status==Status.REJECTED,'full payload validation before Save')
            check((root/'chapter.aiba').read_bytes()==before,'rejected requests preserve durable bytes')
            current=replace(context,revision=3,fingerprint=fp1)
            candidate=json.dumps({'version':1,'label':'Another move','edits':[{'entity_id':door[0],'field':'x','value':-32.6}]})
            handles=[]
            for i in range(8):
                result=peer.call(Opcode.PREVIEW,command(head.scope,encode_proposal(candidate,current,'private-'+str(i))),3)
                check(result.status==Status.PREPARED,'bounded native prepared token')
                handles.append(result.token)
            check(peer.call(Opcode.PREVIEW,command(head.scope,encode_proposal(candidate,current,'ninth')),3).status==Status.REJECTED,'ninth prepared handle rejects')
            check(peer.call(Opcode.RELEASE_PREPARED,prepared_handle(head.scope,handles[0]),3).status==Status.OK,'explicit release frees strong handle')
            admitted=peer.call(Opcode.PREVIEW,command(head.scope,encode_proposal(candidate,current,'after-release')),3)
            check(admitted.status==Status.PREPARED,'preview budget recovers after release')
            unsaved=peer.call(Opcode.APPLY_PREPARED,prepared_handle(head.scope,admitted.token),3)
            check(unsaved.status==Status.APPLIED and unsaved.head_revision==4,'visible unsaved edit for shutdown proof')
            check((root/'chapter.aiba').read_bytes()==before,'Apply does not silently save')
        finally:peer.close()
        peer=Peer(exe,root)
        try:
            peer.call(Opcode.HELLO);reopened=peer.call(Opcode.OPEN,opened(create=False))
            check(reopened.scope.world_id==world and reopened.checkpoint_id==checkpoint and reopened.head_revision==3,'reopen exact scope/head/checkpoint')
            check(description(peer.call(Opcode.DESCRIBE,scoped(reopened.scope),3))[3]==0,'reopened clean')
            retry=peer.call(Opcode.APPLY_TRANSACTION,command(reopened.scope,blob),0)
            check(retry.status==Status.DUPLICATE and retry.operation_revision==1,'durable receipts survive host epoch')
            check(peer.call(Opcode.HISTORY,history(reopened.scope,'typed-undo',fp1),1).status==Status.DUPLICATE,'durable history retry')
            check((root/'world.aibs').read_bytes()==b'Unrelated retained player/authoring file','unrelated file unchanged')
            check((root/'chapter.aiba').read_bytes()==before,'read/retry never autosaves')
        finally:peer.close()
        check((root/'chapter.aiba').read_bytes()==before,'shutdown discarded unsaved visible candidate without rewriting checkpoint')
        malformed=Peer(exe,root)
        try:
            malformed.process.stdin.write(b'AIBC');malformed.process.stdin.close();malformed.process.wait(timeout=5)
            check(malformed.process.returncode==2,'truncated framing terminates with diagnostic')
            check((root/'chapter.aiba').read_bytes()==before,'malformed framing preserves file bytes')
        finally:malformed.close(graceful=False)
    return checks

if __name__=='__main__':
    count=verify(Path(sys.argv[1]));print(f'Typed native owner passed {count} checks')
    if len(sys.argv)>2:
        from datetime import datetime,timezone
        Path(sys.argv[2]).write_text(json.dumps({'schema_version':1,'status':'passed','completed_at':datetime.now(timezone.utc).isoformat(),'checks':count,'executable':str(Path(sys.argv[1]).resolve())},indent=2)+'\n',encoding='utf-8')
