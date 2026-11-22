"""Actual interactive native owner lifecycle, using synthetic test worlds only."""
from pathlib import Path
import hashlib
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio.game_engine.creator_wire import Frame, Opcode, Parser, encode, UNSCOPED_REVISION
from native_studio.game_engine.creator_payload import EditRequest, Transaction, Create, SetField, encode_edit
from native_studio.game_engine.creator_commands import (
    Status, decode_response, open_document, scoped, prepared_handle, history, snapshot_page, decode_page, decode_description,
)

UUID = '01234567-89ab-4cde-8fab-0123456789ab'


class Peer:
    def __init__(self, exe, directory, extra_args=()):
        self.process = subprocess.Popen([str(exe), '--workspace', str(directory), *extra_args],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.messages = queue.Queue(maxsize=8)
        self.sequence = 0
        self.epoch = bytes(16)
        def reader():
            parser = Parser()
            try:
                while chunk := os.read(self.process.stdout.fileno(), 65536):
                    for frame in parser.feed(chunk):
                        self.messages.put(frame, timeout=3)
                parser.finish()
                self.messages.put(EOFError('Native owner closed'), timeout=3)
            except Exception as error:
                self.messages.put(error, timeout=3)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()

    def call(self, opcode, payload=b'', revision=UNSCOPED_REVISION, epoch=None):
        self.sequence += 1
        self.process.stdin.write(encode(Frame(opcode, self.sequence, self.epoch if epoch is None else epoch,
                                             revision, payload)))
        self.process.stdin.flush()
        frame = self.messages.get(timeout=10)
        if isinstance(frame, Exception):
            raise frame
        assert frame.response and frame.opcode == opcode and frame.request_id == self.sequence
        response = decode_response(frame.payload)
        assert frame.revision == response.head_revision
        if opcode == Opcode.HELLO and response.status == Status.OK:
            assert frame.epoch != bytes(16)
            self.epoch = frame.epoch
        else:
            assert frame.epoch == self.epoch
        return response

    def close(self, graceful=True):
        try:
            if graceful and self.process.poll() is None:
                assert self.call(Opcode.SHUTDOWN).status == Status.OK
                self.process.wait(timeout=5)
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=5)
            try:
                self.process.stdin.close()
            except BrokenPipeError:
                pass
            self.reader.join(timeout=3)
            assert not self.reader.is_alive()
            self.process.stdout.close()
            stderr = self.process.stderr.read(8192)
            self.process.stderr.close()
        if graceful:
            assert self.process.returncode == 0, stderr


def verify(exe):
    checks = 0
    def require(condition, message):
        nonlocal checks
        checks += 1
        assert condition, message

    with tempfile.TemporaryDirectory(prefix='aibs-owner-process-') as temp:
        directory = Path(temp)
        peer = Peer(exe, directory)
        try:
            require(peer.call(Opcode.OPEN, open_document('project','main',(('x',-100.,100.),),True)).status == Status.REJECTED,
                    'Open before Hello must reject')
            require(peer.call(Opcode.HELLO,b'invalid').status==Status.REJECTED,'Malformed Hello does not negotiate')
            require(peer.call(Opcode.HELLO).status == Status.OK, 'Hello negotiates epoch')
            require(peer.call(Opcode.OPEN,open_document('project','main',(('x',-100.,100.),),True)+b'bad').status==Status.REJECTED,
                    'Trailing Open bytes reject before document replacement')
            opened = peer.call(Opcode.OPEN, open_document('project','main',(('x',-100.,100.),),True))
            require(opened.status == Status.OK and opened.head_revision == 0, 'Open synthetic blank world')
            scope = opened.scope
            description=peer.call(Opcode.DESCRIBE,scoped(scope),0)
            require(decode_description(description.body)==(('x',-100.,100.),),'Describe returns actual registered metadata')
            require(not (directory/'world.aibs').exists(), 'Open never silently saves')
            tx = Transaction('create',0,'Author cube',(Create('cube','Cube',UUID,(('x',-0.),)),))
            payload = encode_edit(EditRequest(scope,tx))
            prepared = peer.call(Opcode.PREVIEW,payload,0)
            require(prepared.status == Status.PREPARED and prepared.token and prepared.save_compatible, 'Preview with save assessment')
            require(prepared.head_revision == 0, 'Preview does not publish')
            require(peer.call(Opcode.RELEASE_PREPARED,prepared_handle(scope,prepared.token),0).status==Status.OK,'Release private preparation')
            require(peer.call(Opcode.APPLY_PREPARED,prepared_handle(scope,prepared.token),0).status==Status.REJECTED,'Released preparation cannot apply')
            prepared=peer.call(Opcode.PREVIEW,payload,0)
            applied = peer.call(Opcode.APPLY_PREPARED,prepared_handle(scope,prepared.token),0)
            require(applied.status == Status.APPLIED and applied.head_revision == 1,'Private server token applies')
            current = peer.call(Opcode.APPLY_TRANSACTION,payload,0)
            require(current.status == Status.DUPLICATE and current.head_revision == 1 and current.operation_revision == 1,
                    'Original operation retry uses old request revision')
            page = peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(scope,current.checkpoint_id),1)
            rows, cursor, more = decode_page(page.body)
            require(len(rows)==1 and rows[0].alias=='cube' and not more,'UUID snapshot page')
            bad = peer.call(Opcode.DESCRIBE,scoped(scope),1,epoch=bytes(16))
            require(bad.status == Status.REJECTED and bad.head_revision == 1,'Foreign transport epoch cannot mutate')
            saved = peer.call(Opcode.SAVE,scoped(scope),1)
            require(saved.status == Status.SAVED and saved.checkpoint_id,'Save publishes scoped world')
            before = hashlib.sha256((directory/'world.aibs').read_bytes()).hexdigest()
            stale = peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(scope,current.checkpoint_id),1)
            require(stale.status == Status.REJECTED,'Save invalidates cursor without revision change')
            malformed = peer.call(Opcode.APPLY_TRANSACTION,payload+b'bad',0)
            require(malformed.status == Status.REJECTED and malformed.head_revision==1,'Malformed payload leaves document unchanged')
            require(peer.call(Opcode.SAVE,scoped(scope),0).status == Status.REJECTED,'Stale save blocked before writing')
            require(hashlib.sha256((directory/'world.aibs').read_bytes()).hexdigest()==before,'Rejected operations preserve durable bytes')
            undone = peer.call(Opcode.HISTORY,history(scope,'undo',False),1)
            require(undone.status==Status.UNDONE and undone.head_revision==2,'Undo through host')
            require(peer.call(Opcode.HISTORY,history(scope,'undo',False),1).status==Status.DUPLICATE,'History retry remains epoch-local')
            redone = peer.call(Opcode.HISTORY,history(scope,'redo',True),2)
            require(redone.status==Status.REDONE and redone.head_revision==3,'Redo through host')
            playing = peer.call(Opcode.START_PLAY,scoped(scope),3)
            require(playing.status==Status.PLAYING and playing.play_epoch,'Explicit isolated in-process Play')
            require(peer.call(Opcode.STOP_PLAY,prepared_handle(scope,playing.play_epoch),3).status==Status.STOPPED,'Stop matching Play epoch')
            require(peer.call(Opcode.SAVE,scoped(scope),3).status==Status.SAVED,'Save final authored history')
        finally:
            peer.close()
        original_scope,original_tx=scope,tx
        unicode_dir=directory/'Pencil_✏';unicode_dir.mkdir()
        peer=Peer(exe,unicode_dir)
        try:
            peer.call(Opcode.HELLO)
            opened=peer.call(Opcode.OPEN,open_document('Pencil ✏','main',(('x',-100.,100.),),True))
            require(opened.status==Status.OK,'Unicode selected workspace and project')
            scope=opened.scope
            uuids=(UUID,'11234567-89ab-4cde-8fab-0123456789ab','21234567-89ab-4cde-8fab-0123456789ab')
            request=Transaction('three',0,'Three nodes',tuple(Create(alias,alias,uuid,(('x',1.),)) for alias,uuid in zip(('a','b','c'),uuids)))
            require(peer.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(scope,request)),0).status==Status.APPLIED,'Grouped authored nodes')
            cursor='';seen=[]
            while True:
                page=peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(scope,'',cursor,1),1)
                rows,cursor,more=decode_page(page.body)
                seen.extend(row.uuid for row in rows)
                if not more:break
            require(seen==list(uuids),'Pinned pages visit every unique UUID in order')
            tokens=[]
            for i in range(8):
                tx=Transaction('prepare-'+str(i),1,'Move',(SetField('a','x',float(i),UUID),))
                reply=peer.call(Opcode.PREVIEW,encode_edit(EditRequest(scope,tx)),1)
                require(reply.status==Status.PREPARED,'Bounded server preparation admitted')
                tokens.append(reply.token)
            ninth=encode_edit(EditRequest(scope,Transaction('ninth',1,'',(SetField('a','x',9.,UUID),))))
            require(peer.call(Opcode.PREVIEW,ninth,1).status==Status.REJECTED,'Ninth strong server preparation rejected')
            require(peer.call(Opcode.RELEASE_PREPARED,prepared_handle(scope,tokens.pop()),1).status==Status.OK,'Release frees admission slot')
            require(peer.call(Opcode.PREVIEW,ninth,1).status==Status.PREPARED,'Released slot reusable')
            require(peer.call(Opcode.SAVE,scoped(scope),1).status==Status.SAVED,'Save Unicode workspace')
            require(peer.call(Opcode.APPLY_PREPARED,prepared_handle(scope,tokens[0]),1).status==Status.REJECTED,
                    'Successful save releases handles even at unchanged revision')
        finally:
            peer.close()
        # A malformed frame terminates the connection without touching saved bytes.
        durable=hashlib.sha256((unicode_dir/'world.aibs').read_bytes()).hexdigest()
        peer=Peer(exe,unicode_dir)
        try:
            peer.call(Opcode.HELLO)
            peer.call(Opcode.OPEN,open_document('Pencil ✏','main',(('x',-100.,100.),),False))
            peer.process.stdin.write(b'FAIL'+bytes(44));peer.process.stdin.flush()
            peer.process.wait(timeout=5)
            require(peer.process.returncode==2,'Invalid frame terminates owner')
            require(hashlib.sha256((unicode_dir/'world.aibs').read_bytes()).hexdigest()==durable,'Fatal parser failure preserves checkpoint bytes')
        finally:
            peer.close(False)
        scope,tx=original_scope,original_tx
        peer = Peer(exe,directory)
        try:
            peer.call(Opcode.HELLO)
            reopened = peer.call(Opcode.OPEN,open_document('project','main',(('x',-100.,100.),),False))
            require(reopened.status==Status.OK and reopened.scope.world_id==scope.world_id and reopened.head_revision==3,
                    'Fresh process restores authored history/world identity')
            new_scope = reopened.scope
            require(new_scope.host_epoch != scope.host_epoch,'Fresh host epoch after restart')
            require(peer.call(Opcode.APPLY_TRANSACTION,encode_edit(EditRequest(new_scope,tx)),0).status==Status.DUPLICATE,
                    'Persisted original request resolves in fresh process')
            require(peer.call(Opcode.DESCRIBE,scoped(scope),3).status==Status.REJECTED,'Old host epoch rejected')
            require(peer.call(Opcode.SNAPSHOT_PAGE,snapshot_page(new_scope,reopened.checkpoint_id),3).status==Status.OK,
                    'Fresh pinned snapshot works')
        finally:
            peer.close()
    return {'status':'passed','checks':checks,'completed_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Actual native owner process; synthetic numeric authoring world only'}


if __name__=='__main__':
    report=verify(Path(sys.argv[1]).resolve())
    if len(sys.argv)>2:
        Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
