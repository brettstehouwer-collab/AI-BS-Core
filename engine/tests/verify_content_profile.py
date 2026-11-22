"""Exercise profile selection/restart through actual native pipe owners."""
from pathlib import Path
import json, sys, tempfile, struct
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from verify_creator_process import Peer
from verify_content_process import opened, page, description
from native_studio.game_engine.creator_wire import Opcode
from native_studio.game_engine.creator_commands import Status, scoped, snapshot_page
from native_studio.game_engine.content_commands import export_content, decode_content_export

def verify(executable, output):
    checks=[]
    def check(value, text):
        if not value: raise AssertionError(text)
        checks.append(text)
    def connect(root, modern):
        return Peer(executable, root, ('--asset-profile','warm-beginning') if modern else ())
    def rows(peer, head):
        result=[];cursor=''
        while True:
            reply=peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(head.scope,head.checkpoint_id,cursor,32),head.head_revision)
            check(reply.status==Status.OK,'Read authoritative profile row')
            cursor,more,part=page(reply);result.extend(part)
            if not more:return result
    def payload(peer, head):
        definition,revision,fp,dirty,known=description(peer.call(Opcode.DESCRIBE,scoped(head.scope),head.head_revision))
        blob=bytearray()
        while True:
            reply=peer.call(Opcode.DESCRIBE,export_content(head.scope,len(blob),65536,fp),head.head_revision)
            check(reply.status==Status.OK,'Canonical content export chunk')
            chunk=decode_content_export(reply.body);blob.extend(chunk.payload)
            if len(blob)==chunk.total:return bytes(blob)
    with tempfile.TemporaryDirectory(prefix='aibs-profile-owner-') as temporary:
        root=Path(temporary)
        modern=root/'modern';modern.mkdir();legacy=root/'legacy';legacy.mkdir()
        for directory,selected,version in [(modern,True,3),(legacy,False,1)]:
            peer=connect(directory,selected)
            try:
                hello=peer.call(Opcode.HELLO);check(hello.status==Status.OK,'Owner profile negotiation succeeds')
                head=peer.call(Opcode.OPEN,opened('profile-proof'))
                check(head.status==Status.OK,'Explicit native profile create succeeds')
                authored=rows(peer,head)
                settings=next(r for r in authored if r[1]=='authoring.ChapterSettings')
                if selected:check(settings[3]['asset_profile']=='warm_beginning','Profile comes from native v3 content')
                data=payload(peer,head)
                check(data[:4]==b'AIBD' and struct.unpack_from('<H',data,4)[0]==version,'Canonical version matches selected profile')
                saved=peer.call(Opcode.SAVE,scoped(head.scope),head.head_revision)
                check(saved.status==Status.SAVED,'Selected profile authoring document saves')
            finally:peer.close(graceful=peer.epoch!=bytes(16))
            retained=(directory/'chapter.aiba').read_bytes()
            peer=connect(directory,not selected)
            try:
                peer.call(Opcode.HELLO);head=peer.call(Opcode.OPEN,opened('profile-proof',create=False))
                check(head.status==Status.REJECTED,'Metadata/native profile disagreement rejects')
            finally:peer.close()
            check((directory/'chapter.aiba').read_bytes()==retained,'Wrong-profile open never rewrites document')
            peer=connect(directory,selected)
            try:
                peer.call(Opcode.HELLO);head=peer.call(Opcode.OPEN,opened('profile-proof',create=False))
                check(head.status==Status.OK and payload(peer,head)==data,'Fresh native process restores exact selected content')
            finally:peer.close()
    output.write_text(json.dumps({'schema_version':1,'status':'passed','completed_at':datetime.now(timezone.utc).isoformat(),'checks':checks},indent=2)+'\n')
    print(f'PASS {len(checks)} native profile creation, canonical export, save/restart and mismatch checks')

if __name__=='__main__':verify(Path(sys.argv[1]),Path(sys.argv[2]))
