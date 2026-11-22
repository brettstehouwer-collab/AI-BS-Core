"""Immutable native content export and its owned DX12 projection.

Python transports canonical AIBD bytes. Geometry stays in the native scene builder.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib,os,time,uuid
from .creator_payload import _Writer,_uuid
from .creator_viewport import ViewportClient,_replace_snapshot,new_viewport_workspace
from .project_assets import ProjectAssetClient,validate_asset_profile
from .content_commands import ContentExportDependency,validate_content_export_dependencies
from .opening_fields import require_inspection_reader

@dataclass(frozen=True)
class ContentSnapshot:
    scope:object
    generation:int
    revision:int
    checkpoint_id:str
    definition_id:str
    content_revision:int
    fingerprint:str
    payload:bytes
    entity_ids:frozenset
    asset_refs:tuple=()
    asset_store:Path|None=None
    asset_profile:str='legacy_v1'
    export_version:int=1
    dependency_kinds:tuple=()
    authored_inspections:bool=False
    initial_view_authored:bool=False
    opening_workshop_authored:bool=False
    def __post_init__(self):
        validate_asset_profile(self.asset_profile)
        if type(self.opening_workshop_authored)is not bool:raise ValueError('Invalid Opening Workshop snapshot requirement')
        if self.opening_workshop_authored and self.asset_profile!='warm-beginning':raise ValueError('Opening Workshop requires a Warm Beginning snapshot')
        if type(self.initial_view_authored)is not bool:raise ValueError('Invalid authored initial view snapshot requirement')
        if self.initial_view_authored and self.asset_profile!='warm-beginning':raise ValueError('Authored initial view requires a Warm Beginning snapshot')
        if type(self.authored_inspections)is not bool:raise ValueError('Invalid authored inspection snapshot requirement')
        if self.authored_inspections and self.asset_profile!='warm-beginning':raise ValueError('Authored inspections require a Warm Beginning snapshot')
        if type(self.export_version) is not int or self.export_version not in (1,2):raise ValueError('Invalid content snapshot export version')
        if type(self.dependency_kinds) is not tuple:raise ValueError('Content dependency kinds must be owned')
        if self.export_version==1:
            if self.dependency_kinds:raise ValueError('Legacy content export has no complete dependency kinds')
        else:
            if type(self.asset_refs) is not tuple or len(self.asset_refs)!=len(self.dependency_kinds):raise ValueError('Complete content dependency metadata mismatch')
            owned=validate_content_export_dependencies(tuple(ContentExportDependency(kind,ref) for kind,ref in zip(self.dependency_kinds,self.asset_refs)))
            object.__setattr__(self,'asset_refs',tuple(item.reference for item in owned))

class ContentExportAssembly:
    def __init__(self,scope,generation,revision,checkpoint_id,description,entity_ids,*,asset_refs=(),asset_store=None,asset_profile='legacy_v1',require_complete_dependencies=False,authored_inspections=False,initial_view_authored=False,opening_workshop_authored=False):
        self.scope=scope;self.generation=generation;self.revision=revision;self.checkpoint_id=checkpoint_id
        self.description=description;self.entity_ids=frozenset(entity_ids)
        self._description_tag=(description.definition_id,description.fingerprint,description.content_revision)
        self._payload=bytearray();self._total=None;self._version=None;self._dependencies=None
        if type(require_complete_dependencies) is not bool:raise ValueError('Invalid complete content export requirement')
        self.require_complete_dependencies=require_complete_dependencies
        self.asset_refs=tuple(asset_refs);self.asset_store=Path(asset_store) if asset_store is not None else None
        self.asset_profile=validate_asset_profile(asset_profile)
        if type(authored_inspections)is not bool:raise ValueError('Invalid authored inspection export requirement')
        if authored_inspections and self.asset_profile!='warm-beginning':raise ValueError('Authored inspections require a Warm Beginning export')
        self.authored_inspections=authored_inspections
        if type(initial_view_authored)is not bool:raise ValueError('Invalid authored initial view export requirement')
        if initial_view_authored and self.asset_profile!='warm-beginning':raise ValueError('Authored initial view requires a Warm Beginning export')
        self.initial_view_authored=initial_view_authored
        if type(opening_workshop_authored)is not bool:raise ValueError('Invalid Opening Workshop export requirement')
        if opening_workshop_authored and self.asset_profile!='warm-beginning':raise ValueError('Opening Workshop requires a Warm Beginning export')
        self.opening_workshop_authored=opening_workshop_authored
    @property
    def offset(self):return len(self._payload)
    def accept(self,chunk,scope,generation,revision,checkpoint_id):
        if (scope,generation,revision,checkpoint_id)!=(self.scope,self.generation,self.revision,self.checkpoint_id):
            raise ValueError('Content export context changed; refresh and try again')
        if (chunk.definition_id,chunk.fingerprint,chunk.content_revision)!=self._description_tag:
            raise ValueError('Content export definition changed')
        if type(chunk.version) is not int or chunk.version not in (1,2):raise ValueError('Invalid content export version')
        if self.require_complete_dependencies and chunk.version!=2:raise ValueError('Complete dependency export requires native version2; upgrade the owner')
        dependencies=validate_content_export_dependencies(chunk.dependencies)
        if chunk.version==1 and dependencies:raise ValueError('Legacy export cannot carry complete dependency records')
        if self._version is not None and (chunk.version!=self._version or dependencies!=self._dependencies):raise ValueError('Content export version/dependency closure changed')
        if type(chunk.total) is not int or type(chunk.offset) is not int or type(chunk.payload) is not bytes:raise ValueError('Invalid content export range/payload ownership')
        if chunk.offset!=self.offset or not 1<=len(chunk.payload)<=256*1024 or not 1<=chunk.total<=1024*1024 or chunk.offset+len(chunk.payload)>chunk.total:
            raise ValueError('Invalid content export chunk sequence')
        if self._total is not None and self._total!=chunk.total:raise ValueError('Content export size changed')
        if chunk.offset+len(chunk.payload)==chunk.total:
            digest=hashlib.sha256(self._payload);digest.update(chunk.payload)
            if digest.hexdigest()!=self._description_tag[1]:raise ValueError('Content export hash mismatch')
        self._total=chunk.total;self._version=chunk.version;self._dependencies=dependencies;self._payload.extend(chunk.payload)
        if self.offset!=self._total:return None
        payload=bytes(self._payload)
        definition,fingerprint,content_revision=self._description_tag
        references=tuple(item.reference for item in dependencies) if chunk.version==2 else self.asset_refs
        kinds=tuple(item.kind for item in dependencies) if chunk.version==2 else ()
        return ContentSnapshot(scope,generation,revision,checkpoint_id,definition,
            content_revision,fingerprint,payload,self.entity_ids,references,self.asset_store,self.asset_profile,chunk.version,kinds,self.authored_inspections,self.initial_view_authored,self.opening_workshop_authored)

def encode_content_snapshot(snapshot_id,scope,revision,checkpoint_id,payload,selected_id=None):
    _uuid(snapshot_id);_uuid(scope.world_id);_uuid(checkpoint_id,optional=True)
    if type(payload) is not bytes or not payload or len(payload)>1024*1024:raise ValueError('Invalid native content snapshot bytes')
    if type(revision) is not int or not 0<=revision<2**64:raise ValueError('Invalid viewport revision')
    w=_Writer();w.append(b'AIBV');w.number(1,'H');w.number(2,'B')
    for value in (snapshot_id,scope.project,scope.branch,scope.world_id):w.text(value,True)
    w.text(checkpoint_id);w.number(revision,'Q');w.text(_uuid(selected_id or '',optional=True))
    w.number(len(payload),'I')
    data=bytes(w.data)+payload
    if len(data)>1024*1024+64*1024:raise ValueError('Typed viewport envelope exceeds limit')
    return data

class ContentViewportClient(ViewportClient):
    def __init__(self,parent=None,*,asset_cooker=None):
        super().__init__(parent)
        self.asset_cooker=asset_cooker;self.context_valid=None
        self._stager=ProjectAssetClient(asset_cooker,self)
        self._stager.receipt.connect(self._stage_ready);self._stager.failed.connect(self._stage_failed)
        self._stager.closed.connect(self._stage_closed)
        self._stage_pending=self._stage_active=self._deferred_finish=None
        self._stage_bypass=False
        self._stage_initial_start=None
        self._initial_selection=None
        self._content_executable=None
    @property
    def dependency_process_id(self):return self._stager.process_id
    def start_content(self,executable,snapshot,probe_directory=None,*,selected_id=None):
        self._thread()
        if self.state!='closed':raise RuntimeError('Close the current viewport first')
        require_inspection_reader(executable,snapshot)
        self._content_executable=Path(executable).resolve()
        if selected_id is not None:
            _uuid(selected_id)
            if selected_id not in snapshot.entity_ids:raise ValueError('Selected content UUID is absent')
        if snapshot.asset_refs:
            self._directory=new_viewport_workspace();self._path=Path(self._directory.name)
            self.state='staging'
            self._stage_initial_start=(executable,probe_directory)
            self._stage_pending=(snapshot,selected_id,(executable,probe_directory));self._kick_stage()
            return
        if self.asset_cooker is not None:
            self._directory=new_viewport_workspace();self._path=Path(self._directory.name)
            (self._path/'assets').mkdir()
            return self._start_owned_content(executable,snapshot,probe_directory,selected_id,
                asset_root=self._path/'assets/packs',prepared_directory=self._directory)
        return self._start_owned_content(executable,snapshot,probe_directory,selected_id)
    def _start_owned_content(self,executable,snapshot,probe_directory,selected_id,**kwargs):
        require_inspection_reader(executable,snapshot)
        # The base start publishes synchronously before QProcess launch. Scope
        # the requested selection to that publication, including staged starts.
        self._initial_selection=selected_id
        try:return super().start(executable,snapshot.scope,snapshot.revision,snapshot.checkpoint_id,
            snapshot,False,probe_directory,**kwargs)
        finally:self._initial_selection=None
    def publish(self,scope,revision,checkpoint_id,snapshot,first_boot=False,selected_id=None):
        self._thread()
        if selected_id is None:selected_id=self._initial_selection
        if self._directory is None:raise RuntimeError('No viewport workspace')
        if self.state=='stopping':raise RuntimeError('Viewport is closing')
        require_inspection_reader(self._content_executable,snapshot)
        if (scope,revision,checkpoint_id)!=(snapshot.scope,snapshot.revision,snapshot.checkpoint_id):raise ValueError('Typed viewport context mismatch')
        if self._tag and self.state!='closed' and (scope!=self._tag[1] or revision<self._tag[2]):raise ValueError('Viewport document changed')
        if selected_id and selected_id not in snapshot.entity_ids:raise ValueError('Selected content UUID is absent')
        if not self._stage_bypass and (snapshot.asset_refs or self._stager.busy):
            start=self._stage_initial_start if self._process is None and self.state=='staging' else None
            self._stage_pending=(snapshot,selected_id,start);self._kick_stage();return
        self._publish_raw(snapshot,selected_id)
    def _publish_raw(self,snapshot,selected_id=None):
        require_inspection_reader(self._content_executable,snapshot)
        scope,revision,checkpoint_id=snapshot.scope,snapshot.revision,snapshot.checkpoint_id
        snapshot_id=str(uuid.uuid4())
        data=encode_content_snapshot(snapshot_id,scope,revision,checkpoint_id,snapshot.payload,selected_id)
        temporary=self._path/'scene.tmp'
        try:
            with temporary.open('wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            _replace_snapshot(temporary,self._path/'scene.aibv')
        finally:temporary.unlink(missing_ok=True)
        self._tag=(snapshot_id,scope,revision,checkpoint_id);self._ids=set(snapshot.entity_ids)
        self._deadline=time.monotonic()+10
    def _kick_stage(self):
        if self._stager.busy or self._stage_pending is None or self.state=='stopping':return
        request,self._stage_pending=self._stage_pending,None;self._stage_active=request
        snapshot,_,_=request
        try:
            parent=self._path/'assets';parent.mkdir(exist_ok=True)
            output=parent/'packs'
            if snapshot.asset_refs:
                if snapshot.asset_store is None:raise ValueError('Chapter dependency store is unavailable')
                kwargs={'profile':snapshot.asset_profile} if snapshot.asset_profile!='legacy_v1' else {}
                self._stager.stage_store(snapshot.asset_store,output,snapshot.asset_refs,merge=output.exists(),**kwargs)
            else:self._stage_ready('stage',{'status':'passed'})
        except Exception as error:self._stage_failed(str(error))
    def _stage_ready(self,mode,receipt):
        if mode!='stage' or self._stage_active is None:return
        request,self._stage_active=self._stage_active,None
        if self.state=='stopping':self._stage_closed();return
        if self._stage_pending is not None:self._kick_stage();return
        snapshot,selected,start=request
        if self.context_valid is not None and not self.context_valid(snapshot):
            self._stage_failed('Chapter changed during dependency staging; refresh the preview');return
        try:
            if start is not None:
                executable,probe=start;directory=self._directory;self.state='closed';self._stage_bypass=True
                try:self._start_owned_content(executable,snapshot,probe,selected,
                    asset_root=self._path/'assets/packs',prepared_directory=directory)
                finally:self._stage_bypass=False
                self._stage_initial_start=None
            else:self._publish_raw(snapshot,selected)
        except Exception as error:self._stage_failed(str(error))
    def _stage_failed(self,error):
        self.message.emit('Asset dependency staging failed: '+error)
        self._stage_active=self._stage_pending=None
        if self._process is None and not self._stager.busy:self._finish_stage_only()
    def _finish_stage_only(self):
        if self._directory:self._directory.cleanup();self._directory=None
        self._stage_initial_start=None
        self._content_executable=None
        self._path=None;self._tag=None;self._ids.clear();self.state='closed';self.closed.emit()
    def _stage_closed(self):
        if self._deferred_finish is not None and not self._stager.busy:
            process,self._deferred_finish=self._deferred_finish,None;super()._finished(process)
        elif self.state=='stopping' and self._process is None and not self._stager.busy:self._finish_stage_only()
    def stop(self):
        self._stager.stop();self._stage_pending=None
        if self.state=='staging':
            self.state='stopping'
            if not self._stager.busy:self._finish_stage_only()
            return
        super().stop()
    def _finished(self,process):
        if self._stager.busy:
            self._stager.stop();self._deferred_finish=process;return
        super()._finished(process)
        if self.state=='closed':self._content_executable=None
    def _shutdown(self):
        self.stop();self._stager.shutdown();super()._shutdown()
