"""One asynchronous, owned curated-opening creation job; never starts Play."""
from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import tempfile
from PyQt6.QtCore import QObject,QProcess,QThread,QTimer,pyqtSignal

from .opening_assets import OPENING_ROLES,OpeningAssetsBundle,read_opening_assets,plain_path,bounded_json
from .asset_view import AssetView
from native_studio.game_build_monitor import read_native_player_capabilities

_FEATURES=frozenset(('chapter-workshop-commissioning-v1','chapter-initial-view-v1',
    'chapter-authored-inspections-v1','chapter_content_v3','chapter_content_export_v2',
    'chapter_asset_surfaces','character_asset_v2'))
_LIMIT=65536


def _json_file(path,limit=_LIMIT):
    with path.open('rb')as stream:raw=stream.read(limit+1)
    return bounded_json(raw,limit)


@dataclass(frozen=True)
class OpeningProjectResult:
    directory:Path
    manifest_sha256:str
    generation:int


def _tool(executable):
    executable=plain_path(executable,file=True)
    declaration=read_native_player_capabilities(executable)
    version=declaration.get('sdk_version','')
    if (declaration.get('status')!='available' or tuple(map(int,version.split('.')))<(0,15,0)
            or any(declaration.get('features',{}).get(key)is not True for key in _FEATURES)):
        raise ValueError('Curated First Boot creation requires a complete SDK0.15+ factory, cooker and chapter Host')
    return executable


class OpeningProjectClient(QObject):
    completed=pyqtSignal(object)
    failed=pyqtSignal(str)
    closed=pyqtSignal()
    state_changed=pyqtSignal()
    message=pyqtSignal(str)

    def __init__(self,factory=None,assets_root=None,owner_executable=None,parent=None,timeout_ms=60000):
        super().__init__(parent)
        self.factory=Path(factory)if factory is not None else None
        self.assets_root=Path(assets_root)if assets_root is not None else None
        self.owner_executable=Path(owner_executable)if owner_executable is not None else None
        self.context_valid=None
        self.state='idle';self.generation=0;self._process=None
        self._out=bytearray();self._err=bytearray();self._failure='';self._cancelled=False
        self._bundle=None;self._output=None;self._scratch=None;self._index=0;self._mode=None
        self._adopted={};self._timer=QTimer(self);self._timer.setSingleShot(True)
        self._timer.setInterval(timeout_ms);self._timer.timeout.connect(self._timeout)
        self._watchdog=QTimer(self);self._watchdog.setInterval(100);self._watchdog.timeout.connect(self._watch_context)
        self.availability_error=self._configuration_error()

    @property
    def busy(self):return self.state!='idle'
    @property
    def process_id(self):return int(self._process.processId())if self._process is not None else 0

    def _configuration_error(self):
        try:
            if self.factory is None or self.assets_root is None or self.owner_executable is None:
                return 'Curated First Boot resources are not included in this installation.'
            _tool(self.factory);_tool(self.factory.with_name('aibs_assetc.exe'));_tool(self.owner_executable)
            read_opening_assets(self.assets_root)
            return ''
        except (OSError,ValueError,UnicodeError)as error:return str(error)

    def _state(self,value):self.state=value;self.state_changed.emit()
    def _check_context(self):
        if self._cancelled or self.context_valid is not None and not self.context_valid():
            raise ValueError('Opening creation cancelled because the workspace changed or is closing')

    def start(self,output):
        if QThread.currentThread()!=self.thread():raise RuntimeError('Use opening creation on its owning Qt thread')
        if self.busy:raise ValueError('Wait for the current opening creation job')
        self.availability_error=self._configuration_error()
        if self.availability_error:raise ValueError(self.availability_error)
        self._cancelled=False
        self._check_context()
        output=plain_path(output,fresh=True)
        bundle=read_opening_assets(self.assets_root)
        if shutil.disk_usage(output.parent).free<bundle.total_bytes*2+1024*1024:
            raise ValueError('Insufficient free space for the bounded opening dependency copy')
        self.generation+=1;self._bundle=bundle;self._output=output;self._cancelled=False
        self._failure='';self._index=0;self._adopted={}
        self._scratch=Path(tempfile.mkdtemp(prefix='.aibs-opening-',dir=output.parent))
        (self._scratch/'packs').mkdir()
        self._state('adopting')
        self._watchdog.start()
        try:self._adopt_next()
        except Exception as error:self._finish(str(error))

    def _schedule(self,callback):
        generation=self.generation
        def current():
            if self.generation!=generation or not self.busy:return
            try:self._check_context();callback()
            except Exception as error:self._finish(str(error))
        QTimer.singleShot(0,current)

    def _adopt_next(self):
        self._check_context()
        if self._index==len(OPENING_ROLES):
            self._launch_factory();return
        asset=self._bundle.roles[self._index]
        self.message.emit('Verifying curated '+asset.role+' pack…')
        self._launch(self.factory.with_name('aibs_assetc.exe'),
            ['--adopt',str(asset.directory),'--store',str(self._scratch/'packs')],'adopt')

    def _launch(self,executable,args,mode):
        self._check_context()
        if self._process is not None:raise ValueError('An opening subprocess is still active')
        self._mode=mode;self._out.clear();self._err.clear();self._failure=''
        p=QProcess(self);self._process=p;generation=self.generation
        p.setWorkingDirectory(str(self._output.parent));p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        p.readyReadStandardOutput.connect(lambda:self._drain(p,False))
        p.readyReadStandardError.connect(lambda:self._drain(p,True))
        p.finished.connect(lambda code,status:self._finished(p,generation,code,status))
        p.errorOccurred.connect(lambda error:self._error(p,generation,error))
        self._timer.start();p.start(str(executable),args)

    def _drain(self,p,stderr):
        if p is not self._process:return
        p.setReadChannel(QProcess.ProcessChannel.StandardError if stderr else QProcess.ProcessChannel.StandardOutput)
        target=self._err if stderr else self._out
        while p.bytesAvailable():
            chunk=bytes(p.read(min(4096,p.bytesAvailable())));remaining=_LIMIT-len(target);target.extend(chunk[:remaining])
            if len(chunk)>remaining:self._failure='Opening subprocess output exceeds64KiB';p.kill();return

    def _error(self,p,generation,error):
        if p is self._process and error==QProcess.ProcessError.FailedToStart:
            self._failure=p.errorString();self._finished(p,generation,-1,QProcess.ExitStatus.CrashExit)

    def _timeout(self):
        if self._process is not None:self._failure='Opening subprocess timed out';self._process.kill()

    def _watch_context(self):
        if self.busy and not self._cancelled and self.context_valid is not None and not self.context_valid():self.stop()

    def _finished(self,p,generation,code,status):
        if p is not self._process or generation!=self.generation:return
        self._drain(p,False);self._drain(p,True);self._timer.stop()
        self._process=None;p.deleteLater()
        try:
            self._check_context()
            if self._failure or code!=0 or status!=QProcess.ExitStatus.NormalExit:
                error=bytes(self._err[-2048:]).decode('utf-8',errors='replace')
                raise ValueError(self._failure or error or 'Native opening operation failed')
            asset=self._bundle.roles[self._index]if self._index<len(OPENING_ROLES)else None
            if self._mode=='adopt':
                value=bounded_json(bytes(self._out),_LIMIT)
                if type(value)is not dict or set(value)!={'status','asset_id','asset_sha256','pack_sha256'}or value['status']!='passed':
                    raise ValueError('Native opening pack adoption returned an invalid receipt')
                actual=tuple(value[key]for key in ('asset_id','asset_sha256','pack_sha256'))
                if actual!=asset.reference:raise ValueError('Curated '+asset.role+' pack changed or differs from its immutable manifest')
                adopted=self._scratch/'packs'/asset.pack_sha256;self._adopted[asset.role]=adopted
                self._state('inspecting')
                self._schedule(lambda:self._launch(self.factory.with_name('aibs_assetc.exe'),['--inspect',str(adopted)],'inspect'))
            elif self._mode=='inspect':
                value=bounded_json(bytes(self._out),_LIMIT)
                if type(value)is not dict or value.get('status')!='passed':raise ValueError('Native opening pack inspection failed')
                rows=AssetView._rows(value)
                if len(rows)!=1 or (rows[0]['asset_id'],rows[0]['sha256'])!=(asset.asset_id,asset.asset_sha256):
                    raise ValueError('Native opening inspection changed the expected asset identity')
                kind=rows[0].get('kind','mesh')
                if kind!=asset.kind or (asset.role=='adam'and kind!='character')or(asset.role!='adam'and kind not in('mesh','surface')):
                    raise ValueError('Curated '+asset.role+' pack has the wrong native type')
                self._index+=1;self._state('adopting');self._schedule(self._adopt_next)
            elif self._mode=='factory':
                result=self._validate_publication()
                self._finish(result=result)
            else:raise ValueError('Unknown opening job phase')
        except Exception as error:self._finish(str(error))

    def _launch_factory(self):
        self._check_context()
        current=read_opening_assets(self.assets_root)
        if current.manifest_sha256!=self._bundle.manifest_sha256:raise ValueError('Curated opening manifest changed during verification')
        plain_path(self._output,fresh=True)
        args=['--workshop','--output',str(self._output)]
        for role in OPENING_ROLES:args+=['--'+role+'-pack',str(self._adopted[role])]
        self.message.emit('Creating the native First Boot opening…');self._state('creating')
        self._launch(self.factory,args,'factory')

    def _validate_publication(self):
        self._check_context();output=plain_path(self._output,directory=True)
        metadata=plain_path(output/'.aibs-chapter-project.json',boundary=output,file=True)
        value=_json_file(metadata,16384)
        if (type(value)is not dict or set(value)!={'version','project','branch','asset_profile','opening_workshop'}
                or type(value['version'])is not int or value['version']!=3 or value['opening_workshop']is not True
                or value['asset_profile']!='warm-beginning'
                or any(type(value[key])is not str or not value[key]or len(value[key].encode())>4096 or '\0'in value[key]for key in('project','branch'))):
            raise ValueError('Published opening has invalid or incompatible project metadata')
        for name in ('chapter.aiba','opening.aibd'):
            path=plain_path(output/name,boundary=output,file=True)
            if not 1<=path.stat().st_size<=1024*1024:raise ValueError('Published opening document exceeds its byte budget')
        path=plain_path(output/'opening-manifest.json',boundary=output,file=True)
        value=_json_file(path)
        if (type(value)is not dict or type(value.get('version'))is not int or value['version']!=1
                or value.get('opening_workshop')is not True or value.get('recording_bound')is not False):
            raise ValueError('Published opening does not preserve the curated no-audio Workshop contract')
        dependencies=value.get('dependencies')
        if type(dependencies)is not list or len(dependencies)>6:raise ValueError('Published opening dependency closure is invalid')
        actual=set()
        for entry in dependencies:
            if type(entry)is not dict or set(entry)!={'kind','asset_id','asset_sha256','pack_sha256'}or type(entry['kind'])is not int or entry['kind']not in(0,1):
                raise ValueError('Published opening contains an unsupported or audio dependency')
            actual.add(tuple(entry[key]for key in('asset_id','asset_sha256','pack_sha256')))
        if actual!={asset.reference for asset in self._bundle.roles}:raise ValueError('Published opening dependencies differ from the verified curated manifest')
        return OpeningProjectResult(output,self._bundle.manifest_sha256,self.generation)

    def stop(self):
        if QThread.currentThread()!=self.thread():raise RuntimeError('Cancel opening creation on its owning Qt thread')
        if not self.busy:return
        self._cancelled=True;self._state('cancelling')
        if self._process is not None:self._process.kill()
        else:self._finish('Opening creation cancelled; any published output is preserved')

    def _cleanup(self):
        if self._scratch is None:return
        scratch=self._scratch;self._scratch=None
        # Remove only this job's resolved scratch child after every child joined.
        if scratch.parent.resolve()!=self._output.parent.resolve()or not scratch.name.startswith('.aibs-opening-'):
            raise ValueError('Opening scratch boundary changed; files retained')
        plain_path(scratch,directory=True)
        if any(path.is_symlink()or path.is_junction()for path in scratch.rglob('*')):
            raise ValueError('Opening scratch redirection detected; files retained')
        shutil.rmtree(scratch)

    def _finish(self,error='',*,result=None):
        if self._process is not None:
            self._failure=error or 'Opening creation cancelled';self._process.kill();return
        try:self._cleanup()
        except Exception as cleanup_error:error=error or str(cleanup_error)
        self._timer.stop();self._watchdog.stop();self._state('idle')
        self._bundle=None;self._adopted={}
        if error:self.failed.emit(error)
        elif result is not None:self.completed.emit(result)
        self.closed.emit()
