"""Managed Qt transport for the real native authoring owner.

Single Qt-thread owner. Queued frames, retained preview originals, and uncertain
writes each have separate 8-item/1MiB logical bounds. They are not RSS limits.
Recovery records are in memory; this client never silently saves or replays them.
"""
from dataclasses import dataclass
from pathlib import Path
import time
from PyQt6.QtCore import QObject, QProcess, QTimer, QThread, QCoreApplication, pyqtSignal, pyqtSlot
from .creator_wire import Frame, Opcode, Parser, encode, UNSCOPED_REVISION
from .creator_payload import decode_edit, _Reader, _uuid
from .creator_commands import decode_response, Status

LIMIT=1024*1024
WRITES=frozenset((Opcode.APPLY_TRANSACTION,Opcode.APPLY_PREPARED,Opcode.HISTORY,
                  Opcode.SAVE,Opcode.START_PLAY,Opcode.STOP_PLAY))
INVALIDATES=frozenset((Status.APPLIED,Status.UNDONE,Status.REDONE,Status.SAVED))
RESULTS={
    Opcode.OPEN:{Status.OK},Opcode.DESCRIBE:{Status.OK},Opcode.SNAPSHOT_PAGE:{Status.OK},
    Opcode.PREVIEW:{Status.PREPARED,Status.DUPLICATE},
    Opcode.APPLY_PREPARED:{Status.APPLIED,Status.DUPLICATE},
    Opcode.APPLY_TRANSACTION:{Status.APPLIED,Status.DUPLICATE},
    Opcode.RELEASE_PREPARED:{Status.OK},Opcode.HISTORY:{Status.UNDONE,Status.REDONE,Status.DUPLICATE},
    Opcode.SAVE:{Status.SAVED},Opcode.START_PLAY:{Status.PLAYING},Opcode.STOP_PLAY:{Status.STOPPED},
    Opcode.SHUTDOWN:{Status.OK},
}


class ClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecoveryRequest:
    generation: int
    request_id: int
    workspace: str
    opcode: Opcode
    payload: bytes
    revision: int
    transaction_payload: bytes


@dataclass(frozen=True)
class _Pending:
    opcode: Opcode
    raw: bytes
    payload: bytes
    revision: int
    deadline: float
    transaction_payload: bytes=b''


def _handle(payload):
    reader=_Reader(payload)
    if reader.number('H')!=1:raise ClientError('Unsupported handle command')
    for _ in range(4):reader.text(True)
    value=_uuid(reader.text(True))
    if reader.offset!=len(payload):raise ClientError('Trailing handle command bytes')
    return value


def _recovery_charge(payload,original):
    # ApplyTransaction retains the same immutable bytes in both fields.
    # Prepared-handle commands retain their distinct original transaction too.
    return len(payload)+(0 if original is payload else len(original))


class CreatorClient(QObject):
    ready=pyqtSignal()
    # Qt's `int` signal type truncates the protocol's unsigned 64-bit IDs.
    response=pyqtSignal(object,object)
    request_failed=pyqtSignal(object,str)
    closed=pyqtSignal(str)
    state_changed=pyqtSignal(str)

    def __init__(self,parent=None,request_timeout_ms=10000,close_timeout_ms=3000,*,required_capability='numeric-authoring-v1',edit_revision=None):
        super().__init__(parent)
        if not 1<=request_timeout_ms<=60000 or not 1<=close_timeout_ms<=60000:
            raise ClientError('Invalid creator timeout')
        if type(required_capability) is not str or not required_capability or len(required_capability)>128:
            raise ClientError('Invalid creator capability')
        if edit_revision is not None and not callable(edit_revision):raise ClientError('Invalid edit validator')
        self._required_capability=required_capability
        self._edit_revision=edit_revision or (lambda payload:decode_edit(payload).transaction.revision)
        self._request_seconds=request_timeout_ms/1000
        self._close_seconds=close_timeout_ms/1000
        self._process=None;self._state='closed';self._generation=0
        self._epoch=bytes(16);self._head=None;self._saved_revision=None
        self._capabilities=frozenset()
        self._pending={};self._prepared={};self._uncertain=[];self._sequence=0
        self._parser=Parser();self._workspace='';self._stderr=bytearray()
        self._accepting=False;self._closing=False;self._killed=False;self._finalizing=False
        self._reason='';self._stop_deadline=0.;self._launch_deadline=0.
        self._shutdown_sent=False
        self._timer=QTimer(self);self._timer.setInterval(50);self._timer.timeout.connect(self._tick)
        app=QCoreApplication.instance()
        if app:app.aboutToQuit.connect(self._at_exit)

    @property
    def state(self):return self._state
    @property
    def capabilities(self):return self._capabilities
    @property
    def epoch(self):return self._epoch
    @property
    def generation(self):return self._generation
    @property
    def head(self):return self._head
    @property
    def dirty(self):return self._head is not None and self._head.head_revision!=self._saved_revision
    @property
    def pending_count(self):return len(self._pending)
    @property
    def queued_bytes(self):return sum(len(p.raw) for p in self._pending.values())
    @property
    def prepared_count(self):return len(self._prepared)
    @property
    def uncertain_operations(self):return tuple(self._uncertain)
    @property
    def process_id(self):return int(self._process.processId()) if self._process else 0
    @property
    def stderr_tail(self):return bytes(self._stderr).decode('utf-8',errors='replace')

    def _set_state(self,value):
        self._state=value;self.state_changed.emit(value)

    def _current(self,process,generation):
        return process is not None and process is self._process and generation==self._generation

    def _check_thread(self):
        if QThread.currentThread()!=self.thread():raise ClientError('Use the creator client on its owning Qt thread')

    def _hello_requirements(self):
        return frozenset((self._required_capability,))

    def _launch_arguments(self,workspace):
        return ['--workspace',workspace]

    def start(self,executable,workspace):
        self._check_thread()
        if self._process is not None or self._finalizing:raise ClientError('Creator owner is still active')
        executable=Path(executable);workspace=Path(workspace)
        if not executable.is_file() or not workspace.is_dir():raise ClientError('Select an existing owner executable and workspace')
        arguments=self._launch_arguments(str(workspace.resolve()))
        self._generation+=1;generation=self._generation
        self._workspace=str(workspace.resolve());self._epoch=bytes(16);self._head=None;self._saved_revision=None
        self._capabilities=frozenset()
        # Keep request IDs unique across this client's process restarts as well
        # as guarding callbacks by process object and generation.
        self._pending={};self._prepared={};self._parser=Parser();self._stderr.clear()
        self._accepting=True;self._closing=False;self._killed=False;self._reason=''
        self._shutdown_sent=False
        process=QProcess(self);self._process=process
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.started.connect(lambda:self._started(process,generation))
        process.readyReadStandardOutput.connect(lambda:self._read_stdout(process,generation))
        process.readyReadStandardError.connect(lambda:self._read_stderr(process,generation))
        process.finished.connect(lambda code,status:self._finished(process,generation,code))
        process.errorOccurred.connect(lambda error:self._error(process,generation,error))
        self._launch_deadline=time.monotonic()+self._request_seconds
        self._set_state('starting');self._timer.start()
        process.start(str(executable.resolve()),arguments)

    def _started(self,process,generation):
        if not self._current(process,generation):return
        if self._closing:self._fail('Closed during startup');return
        self._set_state('handshaking')
        self._send(Opcode.HELLO,b'',UNSCOPED_REVISION)

    def request(self,opcode,payload=b'',revision=None):
        self._check_thread()
        if self._state!='ready' or self._closing:raise ClientError('Creator connection is not accepting commands')
        try:opcode=Opcode(opcode)
        except (ValueError,TypeError) as error:raise ClientError('Unknown creator opcode') from error
        if opcode in (Opcode.HELLO,Opcode.SHUTDOWN):raise ClientError('Use managed start/stop for lifecycle commands')
        if opcode==Opcode.OPEN and (self._head or any(p.opcode==Opcode.OPEN for p in self._pending.values())):
            raise ClientError('A document is already open or opening')
        if revision is None:revision=UNSCOPED_REVISION if opcode==Opcode.OPEN else (self._head.head_revision if self._head else 0)
        return self._send(opcode,payload,revision)

    def _send(self,opcode,payload,revision):
        if self._process is None or self._process.state()!=QProcess.ProcessState.Running:
            raise ClientError('Creator owner is not running')
        if type(payload) is not bytes:raise ClientError('Creator payload must be immutable bytes')
        identity=self._sequence+1
        raw=encode(Frame(opcode,identity,self._epoch,revision,payload))
        if len(self._pending)>=8 or self.queued_bytes+len(raw)>LIMIT:raise ClientError('Creator pending request budget exceeded')
        original=b''
        if opcode in (Opcode.PREVIEW,Opcode.APPLY_TRANSACTION):
            if self._edit_revision(payload)!=revision:raise ClientError('Command revisions differ')
            original=payload
        elif opcode==Opcode.APPLY_PREPARED:
            original=self._prepared.get(_handle(payload),b'')
        if opcode==Opcode.PREVIEW:
            previews=[p for p in self._pending.values() if p.opcode==Opcode.PREVIEW]
            if len(self._prepared)+len(previews)>=8 or sum(map(len,self._prepared.values()))+sum(len(p.payload) for p in previews)+len(payload)>LIMIT:
                raise ClientError('Retained preview request budget exceeded')
        if opcode in WRITES:
            writes=[p for p in self._pending.values() if p.opcode in WRITES]
            charged=lambda p:_recovery_charge(p.payload,p.transaction_payload)
            if len(self._uncertain)+len(writes)>=8 or sum(charged(p) for p in self._uncertain)+sum(charged(p) for p in writes)+_recovery_charge(payload,original)>LIMIT:
                raise ClientError('Uncertain operation recovery budget exceeded')
        self._sequence=identity
        self._pending[identity]=_Pending(opcode,raw,payload,revision,time.monotonic()+self._request_seconds,original)
        if self._process.write(raw)!=len(raw):self._fail('Could not queue creator request')
        return identity

    def _read_stdout(self,process,generation):
        if not self._current(process,generation):return
        process.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        try:
            while self._current(process,generation) and process.bytesAvailable():
                chunk=bytes(process.read(min(65536,process.bytesAvailable())))
                if not chunk:break
                if not self._accepting:continue
                for frame in self._parser.feed(chunk):self._accept_frame(frame,process,generation)
        except Exception as error:self._fail('Invalid creator response: '+str(error))

    def _read_stderr(self,process,generation):
        if not self._current(process,generation):return
        process.setReadChannel(QProcess.ProcessChannel.StandardError)
        read=0
        while process.bytesAvailable() and read<65536:
            chunk=bytes(process.read(min(4096,process.bytesAvailable())));read+=len(chunk)
            if not chunk:break
            self._stderr.extend(chunk)
            if len(self._stderr)>16384:del self._stderr[:-16384]
        more=bool(process.bytesAvailable());process.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        if more:QTimer.singleShot(0,lambda:self._read_stderr(process,generation))

    def _accept_frame(self,frame,process,generation):
        if not self._current(process,generation) or not self._accepting:return
        pending=self._pending.get(frame.request_id)
        if not frame.response or pending is None or pending.opcode!=frame.opcode:
            raise ClientError('Uncorrelated creator response')
        if frame.request_id!=next(iter(self._pending)):raise ClientError('Creator replies arrived out of order')
        reply=decode_response(frame.payload)
        if frame.revision!=reply.head_revision:raise ClientError('Creator response revisions disagree')
        if pending.opcode==Opcode.HELLO:
            if reply.status!=Status.OK or frame.epoch==bytes(16) or reply.scope.world_id:
                raise ClientError('Creator negotiation failed')
            reader=_Reader(reply.body);capabilities=reader.text();maximum=reader.number('I');count=reader.number('I')
            if not self._hello_requirements()<=frozenset(capabilities.split(';')) or maximum!=LIMIT or count!=8 or reader.offset!=len(reply.body):
                raise ClientError('Unsupported creator capabilities')
            del self._pending[frame.request_id];self._epoch=frame.epoch
            self._capabilities=frozenset(capabilities.split(';'))
            self._set_state('ready')
            if self._state=='ready':self.ready.emit()
            return
        if frame.epoch!=self._epoch:raise ClientError('Creator process epoch mismatch')
        if reply.status!=Status.REJECTED and reply.status not in RESULTS.get(pending.opcode,set()):
            raise ClientError('Creator result kind does not match command')
        if reply.status==Status.PREPARED and (pending.opcode!=Opcode.PREVIEW or not reply.token):
            raise ClientError('Unexpected preparation')
        if self._head:
            if reply.scope!=self._head.scope or reply.head_revision<self._head.head_revision:
                raise ClientError('Creator document identity or head moved backward')
        elif pending.opcode==Opcode.OPEN and reply.status==Status.OK:
            if not reply.scope.world_id or not reply.scope.host_epoch:raise ClientError('Missing document identity')
            requested=_Reader(pending.payload)
            if requested.number('H')!=1 or (requested.text(True),requested.text(True))!=(reply.scope.project,reply.scope.branch):
                raise ClientError('Opened document does not match selected project')
            self._saved_revision=reply.head_revision if reply.checkpoint_id else None
        elif reply.scope.world_id:raise ClientError('Unexpected document identity')
        del self._pending[frame.request_id]
        if reply.scope.world_id:self._head=reply
        if reply.status==Status.PREPARED:
            self._prepared[reply.token]=pending.payload
        if reply.status in INVALIDATES:self._prepared.clear()
        if pending.opcode==Opcode.RELEASE_PREPARED and reply.status==Status.OK:
            self._prepared.pop(_handle(pending.payload),None)
        if reply.status==Status.SAVED:self._saved_revision=reply.head_revision
        if pending.opcode==Opcode.SHUTDOWN:
            if reply.status!=Status.OK:raise ClientError('Creator shutdown rejected')
            process.closeWriteChannel()
        else:self.response.emit(frame.request_id,reply)
        self._maybe_shutdown()

    def _settle_failed(self,reason):
        pending=self._pending;self._pending={}
        for identity,item in pending.items():
            if item.opcode in WRITES:
                self._uncertain.append(RecoveryRequest(self._generation,identity,self._workspace,item.opcode,
                                                       item.payload,item.revision,item.transaction_payload))
            self.request_failed.emit(identity,reason+(' (write outcome unknown)' if item.opcode in WRITES else ''))

    def acknowledge_recovery(self,generation,request_id):
        self._check_thread()
        self._uncertain=[r for r in self._uncertain if (r.generation,r.request_id)!=(generation,request_id)]

    def stop(self):
        self._check_thread()
        if self._process is None or self._closing:return
        self._closing=True;self._reason='Requested close';self._stop_deadline=time.monotonic()+self._close_seconds
        self._set_state('closing');self._maybe_shutdown()

    def _maybe_shutdown(self):
        if not self._closing or not self._accepting or self._pending or self._process is None or self._shutdown_sent:return
        if self._epoch==bytes(16):return
        if self._process.state()==QProcess.ProcessState.Running:
            self._shutdown_sent=True
            self._send(Opcode.SHUTDOWN,b'',UNSCOPED_REVISION)

    def abort(self,reason='Owner interrupted before completion'):
        self._check_thread()
        if self._process is not None:self._fail(str(reason))

    def _fail(self,reason):
        if self._process is None:return
        self._reason=reason;self._accepting=False;self._closing=True
        self._settle_failed(reason);self._prepared.clear();self._set_state('closing')
        process=self._process
        if process.state()==QProcess.ProcessState.NotRunning:self._finalize(process,self._generation,reason)
        elif not self._killed:self._killed=True;process.kill()

    def _tick(self,now=None):
        if self._process is None:return
        now=time.monotonic() if now is None else now
        if self._killed:return
        if self._closing and now>=self._stop_deadline:self._fail('Creator graceful close deadline expired')
        elif self._state=='starting' and now>=self._launch_deadline:self._fail('Creator launch timed out')
        elif any(now>=p.deadline for p in self._pending.values()):self._fail('Creator request timed out')

    def _error(self,process,generation,error):
        if self._current(process,generation) and not self._killed:self._fail('Creator process error: '+process.errorString())

    def _finished(self,process,generation,code):
        if not self._current(process,generation):return
        self._read_stdout(process,generation);self._read_stderr(process,generation)
        if not self._current(process,generation):return
        reason=self._reason or ('Creator exited' if code==0 else 'Creator exited with failure')
        if self._accepting:
            try:self._parser.finish()
            except Exception as error:reason='Truncated creator response: '+str(error)
        self._finalize(process,generation,reason)

    def _finalize(self,process,generation,reason):
        if not self._current(process,generation):return
        if process.state()!=QProcess.ProcessState.NotRunning:return
        self._finalizing=True;self._accepting=False;self._settle_failed(reason);self._prepared.clear()
        self._process=None;self._capabilities=frozenset();self._timer.stop();process.deleteLater();self._set_state('closed')
        self._finalizing=False;self.closed.emit(reason)

    @pyqtSlot()
    def _at_exit(self):
        if self._process is None:return
        process=self._process;generation=self._generation;self.stop()
        if not process.waitForFinished(500):
            self._fail('Application exited before creator completed')
            if self._current(process,generation):process.waitForFinished(1000)
