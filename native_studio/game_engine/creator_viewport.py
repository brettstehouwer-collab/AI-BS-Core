"""Owned read-only native DX12 projection; authoring stays in CreatorHost."""
import math,os,tempfile,time,uuid
from pathlib import Path
from PyQt6.QtCore import QCoreApplication,QObject,QProcess,QThread,QTimer,pyqtSignal
from .creator_payload import _Writer,_uuid,MAX_BYTES

def new_viewport_workspace():
    """Keep stdlib-owned cleanup usable for deeply nested staged asset packs."""
    parent=os.path.abspath(tempfile.gettempdir())
    if os.name=='nt' and not parent.startswith('\\\\?\\'):
        parent=('\\\\?\\UNC\\'+parent[2:]) if parent.startswith('\\\\') else ('\\\\?\\'+parent)
    return tempfile.TemporaryDirectory(prefix='aibs-viewport-',dir=parent)

def _replace_snapshot(temporary,target):
    """Publish a complete file while the native renderer holds a shared read.

    ReplaceFileW supports the shared-delete handle used by the Windows reader;
    MoveFileExW (Python os.replace) can still fail against that same handle.
    Sharing/lock errors and 1175 preserve both original names; retry them within
    a bounded 45ms backoff budget and return observations for verification logs.
    Do not retry 1176/1177, whose documented failure states may move file names.
    """
    if os.name=='nt' and Path(target).exists():
        import ctypes
        from ctypes import wintypes
        replace=ctypes.WinDLL('kernel32',use_last_error=True).ReplaceFileW
        replace.argtypes=(wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,
                          wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p)
        replace.restype=wintypes.BOOL
        observations=[]
        for attempt in range(10):
            if replace(str(target),str(temporary),None,0,None,None):
                return {'attempts':attempt+1,'transient_errors':observations}
            code=ctypes.get_last_error()
            observations.append(code)
            if code not in (32,33,1175) or attempt==9:
                error=ctypes.WinError(code)
                error.publication_attempts=attempt+1
                error.publication_errors=observations
                raise error
            time.sleep(.005)
    else:
        os.replace(temporary,target)
        return {'attempts':1,'transient_errors':[]}

def encode_snapshot(snapshot_id,scope,revision,checkpoint_id,rows,first_boot=False,selected_id=None):
    _uuid(snapshot_id);_uuid(scope.world_id);_uuid(checkpoint_id,optional=True)
    if type(revision) is not int or not 0<=revision<2**64:raise ValueError('Invalid viewport revision')
    rows=tuple(rows)
    if len(rows)>10000:raise ValueError('Viewport entity limit')
    w=_Writer();w.append(b'AIBV');w.number(1,'H');w.number(int(first_boot),'B')
    for value in (snapshot_id,scope.project,scope.branch,scope.world_id):w.text(value,True)
    w.text(checkpoint_id);w.number(revision,'Q');w.text(_uuid(selected_id or '',optional=True));w.number(len(rows),'I');ids=set();aliases=set()
    for row in rows:
        _uuid(row.uuid)
        if row.uuid in ids or row.alias in aliases:raise ValueError('Duplicate viewport entity')
        ids.add(row.uuid);aliases.add(row.alias)
        w.text(row.alias,True);w.text(row.name);w.text(row.uuid,True)
        fields=tuple(row.fields)
        if len(fields)>64:raise ValueError('Viewport field limit')
        w.number(len(fields),'I');keys=set()
        for name,value in fields:
            if name in keys or not math.isfinite(value):raise ValueError('Invalid viewport field')
            keys.add(name);w.text(name,True);w.number(value,'d')
    if selected_id and selected_id not in ids:raise ValueError('Selected viewport UUID is absent')
    return bytes(w.data)

class ViewportClient(QObject):
    selection=pyqtSignal(object,object)
    message=pyqtSignal(str)
    closed=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent);self.state='closed';self._process=None;self._directory=None
        self._tag=None;self._ids=set();self._buffer=bytearray();self.stderr_tail=b'';self._deadline=None
        self.displayed_tag=None
        self._timer=QTimer(self);self._timer.setInterval(100);self._timer.timeout.connect(self._tick)
        app=QCoreApplication.instance()
        if app:app.aboutToQuit.connect(self._shutdown)
    def _thread(self):
        if QThread.currentThread()!=self.thread():raise RuntimeError('Viewport must be used on its Qt thread')
    @property
    def process_id(self):return int(self._process.processId()) if self._process else 0
    def start(self,executable,scope,revision,checkpoint_id,rows,first_boot=False,probe_directory=None,*,asset_root=None,prepared_directory=None):
        self._thread()
        if self.state!='closed':raise RuntimeError('Close the current viewport first')
        executable=Path(executable).resolve()
        if not executable.is_file():raise ValueError('Native creator viewport is not built')
        self._directory=prepared_directory or new_viewport_workspace();self._path=Path(self._directory.name)
        try:self.publish(scope,revision,checkpoint_id,rows,first_boot)
        except Exception:self._directory.cleanup();self._directory=None;raise
        p=QProcess(self);self._process=p;self.state='starting';self._buffer.clear();self.stderr_tail=b''
        p.readyReadStandardOutput.connect(lambda:self._stdout(p));p.readyReadStandardError.connect(lambda:self._stderr(p))
        p.finished.connect(lambda *_:self._finished(p));p.errorOccurred.connect(lambda error:self._error(p,error))
        args=['--snapshot',str(self._path/'scene.aibv'),'--stop-file',str(self._path/'stop')]
        if asset_root is not None:args+=['--asset-root',str(asset_root)]
        if probe_directory is not None:
            target=Path(probe_directory);args+=['--self-test','--capture',str(target/'viewport.bmp'),'--report',str(target/'viewport.json')]
        p.start(str(executable),args);self._timer.start();self._deadline=time.monotonic()+10
    def publish(self,scope,revision,checkpoint_id,rows,first_boot=False,selected_id=None):
        self._thread()
        if self._directory is None:raise RuntimeError('No viewport workspace')
        if self.state=='stopping':raise RuntimeError('Viewport is closing')
        if self._tag and self.state!='closed' and (scope!=self._tag[1] or revision<self._tag[2]):raise ValueError('Viewport document changed')
        rows=tuple(rows);snapshot_id=str(uuid.uuid4());data=encode_snapshot(snapshot_id,scope,revision,checkpoint_id,rows,first_boot,selected_id)
        temporary=self._path/'scene.tmp'
        try:
            with temporary.open('wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            _replace_snapshot(temporary,self._path/'scene.aibv')
        finally:
            if temporary.exists():temporary.unlink()
        self._tag=(snapshot_id,scope,revision,checkpoint_id);self._ids={row.uuid for row in rows}
        self._deadline=time.monotonic()+10
    def _line(self,line):
        parts=line.decode('ascii','strict').split(' ')
        if len(parts) not in (5,6) or parts[0]!='AIBV1' or parts[1] not in ('READY','PICK'):raise ValueError('Invalid viewport response')
        if (parts[1]=='READY')!=(len(parts)==5):raise ValueError('Invalid viewport response fields')
        if not self._tag:return
        identity,scope,revision,_=self._tag
        if parts[2]!=identity or parts[3]!=scope.world_id or parts[4]!=str(revision):return
        if parts[1]=='READY':
            self.displayed_tag=self._tag
            if self.state!='stopping':self.state='ready';self._deadline=None
            self.message.emit('Native preview updated; click an object to select it in the creator.')
        else:
            uid=None if parts[5]=='-' else _uuid(parts[5])
            if uid is not None and uid not in self._ids:raise ValueError('Viewport selected an unknown UUID')
            if self.state!='stopping':self.selection.emit(uid,scope)
    def _stdout(self,p):
        if p is not self._process:return
        try:
            while p.bytesAvailable():
                self._buffer.extend(bytes(p.read(65536)))
                if len(self._buffer)>65536:raise ValueError('Viewport output limit')
                while b'\n' in self._buffer:
                    line,_,rest=self._buffer.partition(b'\n');self._buffer=bytearray(rest)
                    if len(line)>256:raise ValueError('Viewport response line limit')
                    self._line(bytes(line).rstrip(b'\r'))
                if len(self._buffer)>256:raise ValueError('Viewport response line limit')
        except Exception as error:self.message.emit(str(error));self.stop()
    def _stderr(self,p):
        if p is not self._process:return
        p.setReadChannel(QProcess.ProcessChannel.StandardError)
        while p.bytesAvailable():self.stderr_tail=(self.stderr_tail+bytes(p.read(65536)))[-16384:]
        p.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        if self.stderr_tail:self.message.emit(self.stderr_tail.decode('utf-8','replace'))
    def stop(self):
        self._thread()
        if self.state in ('closed','stopping'):return
        self.state='stopping';self._deadline=time.monotonic()+2
        (self._path/'stop').write_bytes(b'stop')
    def _tick(self):
        if self._deadline and time.monotonic()>self._deadline:
            self.message.emit('Native preview did not finish before its deadline; stopping it.')
            self._deadline=None
            if self._process:self._process.kill()
    def _error(self,p,error):
        if p is self._process and error==QProcess.ProcessError.FailedToStart:
            self.message.emit(p.errorString());self._finished(p)
    def _shutdown(self):
        self.stop();p=self._process
        if p and not p.waitForFinished(500):p.kill();p.waitForFinished(1000)
    def _finished(self,p):
        if p is not self._process:return
        self._stdout(p);self._stderr(p);self._process=None;self._timer.stop();self._deadline=None
        self.state='closed';self._tag=None;self.displayed_tag=None;self._ids.clear();self._buffer.clear()
        if self._directory:self._directory.cleanup();self._directory=None
        p.deleteLater();self.closed.emit()
