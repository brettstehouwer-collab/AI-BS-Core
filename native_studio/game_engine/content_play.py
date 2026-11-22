"""Owned native Play against one immutable chapter in disposable scratch storage."""
from pathlib import Path
import hashlib,json,os,tempfile,time,uuid
from PyQt6.QtCore import QCoreApplication,QObject,QProcess,QThread,QTimer,pyqtSignal
from .project_assets import ProjectAssetClient
from .opening_fields import require_inspection_reader

class ContentPlayClient(QObject):
    state_changed=pyqtSignal(str)
    message=pyqtSignal(str)
    closed=pyqtSignal()
    def __init__(self,parent=None,start_timeout_ms=30000,stop_timeout_ms=15000,*,asset_cooker=None):
        super().__init__(parent)
        if not 1<=start_timeout_ms<=60000 or not 1<=stop_timeout_ms<=60000:raise ValueError('Invalid Play timeout')
        self.state='closed';self._process=None;self._directory=None;self._path=None
        self.snapshot=None;self.session_id=None;self.last_result=None
        self._start_seconds=start_timeout_ms/1000;self._stop_seconds=stop_timeout_ms/1000
        self._buffer=bytearray();self.stdout_tail=b'';self.stderr_tail=b'';self._deadline=None
        self._receipt=None;self._forced=False;self._reason='';self._stop_requested=False
        self._protocol_failed=False;self._ready_seen=False
        self._timer=QTimer(self);self._timer.setInterval(50);self._timer.timeout.connect(self._tick)
        self._stager=ProjectAssetClient(asset_cooker,self);self._stager.receipt.connect(self._stage_ready)
        self._stager.failed.connect(self._stage_failed);self._stager.closed.connect(self._stage_closed)
        self._staged_executable=None
        app=QCoreApplication.instance()
        if app:app.aboutToQuit.connect(self._shutdown)
    def _thread(self):
        if QThread.currentThread()!=self.thread():raise RuntimeError('Play must be used on its Qt thread')
    @property
    def process_id(self):return int(self._process.processId()) if self._process else 0
    @property
    def workspace_path(self):return self._path
    @property
    def dependency_process_id(self):return self._stager.process_id
    def _state(self,state):self.state=state;self.state_changed.emit(state)
    def start(self,executable,snapshot):
        self._thread()
        if self.state!='closed' or self._process is not None:raise RuntimeError('Stop the current Play session first')
        executable=Path(executable).resolve()
        if not executable.is_file():raise ValueError('The content-aware native PC player is not built')
        require_inspection_reader(executable,snapshot)
        if type(snapshot.payload) is not bytes or hashlib.sha256(snapshot.payload).hexdigest()!=snapshot.fingerprint:
            raise ValueError('Play snapshot hash mismatch')
        self._directory=tempfile.TemporaryDirectory(prefix='aibs-chapter-play-');self._path=Path(self._directory.name).resolve(strict=True)
        try:
            with (self._path/'chapter.aibd').open('xb') as stream:
                stream.write(snapshot.payload);stream.flush();os.fsync(stream.fileno())
        except Exception:
            self._directory.cleanup();self._directory=None;self._path=None;raise
        self.snapshot=snapshot;self.session_id=str(uuid.uuid4());self.last_result=None
        self._receipt=None;self._forced=False;self._reason='';self._stop_requested=False
        self._protocol_failed=False;self._ready_seen=False
        self._buffer.clear();self.stdout_tail=b'';self.stderr_tail=b''
        if snapshot.asset_refs:
            self._staged_executable=executable;self._state('staging')
            try:
                if snapshot.asset_store is None:raise ValueError('Chapter asset dependency store is unavailable')
                (self._path/'assets').mkdir()
                kwargs={'profile':snapshot.asset_profile} if snapshot.asset_profile!='legacy_v1' else {}
                self._stager.stage_store(snapshot.asset_store,self._path/'assets/packs',snapshot.asset_refs,**kwargs)
            except Exception:
                self._finish_stage_only();raise
            return
        try:self._launch(executable)
        except Exception:self._finish_stage_only();raise
    def _launch(self,executable):
        snapshot=self.snapshot
        require_inspection_reader(executable,snapshot)
        p=QProcess(self);self._process=p
        p.setWorkingDirectory(str(self._path));p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        p.readyReadStandardOutput.connect(lambda:self._stdout(p));p.readyReadStandardError.connect(lambda:self._stderr(p))
        p.finished.connect(lambda code,status:self._finished(p,code,status))
        p.errorOccurred.connect(lambda error:self._error(p,error))
        args=['--durable-world','--content-definition',str(self._path/'chapter.aibd'),
            '--database',str(self._path/'world.sqlite'),'--project',snapshot.scope.project,
            '--branch',snapshot.scope.branch,'--play-session',self.session_id,
            '--stop-file',str(self._path/'stop.request')]
        if snapshot.asset_refs:args+=['--asset-root',str(self._path/'assets/packs')]
        self._deadline=time.monotonic()+self._start_seconds;self._state('starting');self._timer.start()
        p.start(str(executable),args)
    def _stage_ready(self,mode,receipt):
        if mode=='stage' and self.state=='staging':
            try:self._launch(self._staged_executable)
            except Exception as error:self._stage_failed(str(error))
    def _stage_failed(self,error):
        self._reason='Asset dependency staging failed: '+error;self.message.emit(self._reason)
        if self._process is None and not self._stager.busy:self._finish_stage_only()
    def _stage_closed(self):
        if self.state=='stopping' and self._process is None:self._finish_stage_only()
    def _finish_stage_only(self):
        if self._directory:self._directory.cleanup();self._directory=None
        self._path=None;self._staged_executable=None;self._state('closed');self.closed.emit()
    def _line(self,line):
        try:self._accept_line(line)
        except Exception as error:
            self._protocol_failed=True
            self._reason='Invalid native Play response: '+str(error)
            raise
    def _accept_line(self,line):
        # Native diagnostic lines may accompany the two managed JSONL events.
        if not line.startswith(b'{'):return
        event=json.loads(line.decode('utf-8','strict'))
        if type(event) is not dict or event.get('event') not in ('aibs.play.ready','aibs.play.stopped'):
            return
        if (event.get('play_session'),event.get('world_id'),event.get('content_fingerprint'))!=(
                self.session_id,self.snapshot.scope.world_id,self.snapshot.fingerprint):
            raise ValueError('Native Play event belongs to another snapshot or session')
        if type(event.get('saved')) is not bool or type(event.get('durable_revision')) is not int or event['durable_revision']<0:
            raise ValueError('Invalid native Play durability receipt')
        if event['event']=='aibs.play.ready':
            if self._ready_seen or self._receipt is not None:raise ValueError('Duplicate or out-of-order native Play READY')
            self._ready_seen=True
            if self.state=='starting':self._deadline=None;self._state('ready')
            self.message.emit('Native Play is showing the pinned chapter snapshot.')
        else:
            if self._receipt is not None or (not self._ready_seen and not self._stop_requested):
                raise ValueError('Duplicate or out-of-order native Play STOPPED')
            self._receipt=event
    def _stdout(self,p):
        if p is not self._process:return
        p.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        try:
            while p.bytesAvailable():
                chunk=bytes(p.read(min(65536,p.bytesAvailable())))
                self.stdout_tail=(self.stdout_tail+chunk)[-16384:];self._buffer.extend(chunk)
                if len(self._buffer)>65536:raise ValueError('Native Play output limit')
                while b'\n' in self._buffer:
                    line,_,rest=self._buffer.partition(b'\n');self._buffer=bytearray(rest)
                    if len(line)>8192:raise ValueError('Native Play line limit')
                    self._line(bytes(line).rstrip(b'\r'))
                if len(self._buffer)>8192:raise ValueError('Native Play line limit')
        except Exception as error:
            self._protocol_failed=True
            self._reason='Invalid native Play response: '+str(error);self.message.emit(self._reason);self.stop()
    def _stderr(self,p):
        if p is not self._process:return
        p.setReadChannel(QProcess.ProcessChannel.StandardError)
        while p.bytesAvailable():self.stderr_tail=(self.stderr_tail+bytes(p.read(min(65536,p.bytesAvailable()))))[-16384:]
        p.setReadChannel(QProcess.ProcessChannel.StandardOutput)
    def stop(self):
        self._thread()
        if self.state in ('closed','stopping'):return
        if self.state=='staging':
            self._stop_requested=True;self._state('stopping');self._stager.stop()
            if not self._stager.busy:self._finish_stage_only()
            return
        self._stop_requested=True;self._state('stopping');self._deadline=time.monotonic()+self._stop_seconds
        try:
            with (self._path/'stop.request').open('wb') as stream:
                stream.write(b'stop\n');stream.flush();os.fsync(stream.fileno())
        except OSError as error:
            self._force('Could not request a Play drain: '+str(error))
    def _force(self,reason):
        self._reason=reason;self._forced=True;self._deadline=None
        self.message.emit(reason+' Temporary Play progress is not verified durable.')
        if self._process:self._process.kill()
    def _tick(self):
        if self._deadline and time.monotonic()>=self._deadline:
            self._force('Native Play '+('stop' if self.state=='stopping' else 'startup')+' deadline expired')
    def _error(self,p,error):
        if p is not self._process:return
        if error==QProcess.ProcessError.FailedToStart:
            self._reason=p.errorString();self._finished(p,-1,QProcess.ExitStatus.CrashExit)
    def _finished(self,p,code,status):
        if p is not self._process:return
        self._stdout(p);self._stderr(p)
        graceful=(not self._forced and not self._protocol_failed and code==0 and status==QProcess.ExitStatus.NormalExit and self._receipt is not None)
        saved=graceful and self._receipt['saved']
        reason=self._reason or ('Play stopped. Test gameplay changes have reset; creator edits remain.' if saved
            else 'Play exited without a verified test-session drain. Test changes reset; creator edits remain.')
        self.last_result={'graceful':graceful,'saved':bool(saved),'forced':self._forced,'reason':reason,
            'content_fingerprint':self.snapshot.fingerprint,'play_session':self.session_id,
            'durable_revision':self._receipt['durable_revision'] if self._receipt else None,
            'context':'temporary_play'}
        self._process=None;self._timer.stop();self._deadline=None;self._buffer.clear()
        # Delete scratch files only after QProcess reports NotRunning.
        if self._directory:self._directory.cleanup();self._directory=None
        self._path=None;p.deleteLater();self._state('closed');self.message.emit(reason);self.closed.emit()
    def _shutdown(self):
        self.stop();self._stager.shutdown();p=self._process
        if p and not p.waitForFinished(500):
            self._force('Application exited before the Play save drain completed');p.waitForFinished(1000)
