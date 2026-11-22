"""Typed chapter authoring wire bodies; existing numeric protocol stays separate."""
from dataclasses import dataclass
import math,re,struct
from typing import TYPE_CHECKING
from .creator_payload import _Writer,_Reader,_uuid,PayloadError,Scope,MAX_BYTES
from .creator_commands import _scope_writer
from .opening_fields import fixture_inspection_fields
if TYPE_CHECKING:
    from .project_assets import AssetDependency

@dataclass(frozen=True)
class SetField:
    uuid:str
    field:str
    value:object
@dataclass(frozen=True)
class CreateFixture:
    uuid:str
    name:str
    center:tuple=(0.,.4,0.)
    half_extent:tuple=(.4,.4,.4)
    color:tuple=(.3,.2,.1)
    emission:float=0.
    selectable:bool=True
    rotation:tuple=(0.,0.,0.,1.)
    sheltered_emission:float=-1.
@dataclass(frozen=True)
class EraseFixture:
    uuid:str
@dataclass(frozen=True)
class CreateHardware:
    uuid:str
    alias:str
    name:str
    fields:tuple
@dataclass(frozen=True)
class EraseHardware:
    uuid:str
@dataclass(frozen=True)
class CreateAssetPlacement:
    uuid:str
    name:str
    asset_id:str
    asset_sha256:str
    pack_sha256:str
    center:tuple=(-35.,.4,10.)
    scale:tuple=(1.,1.,1.)
    rotation:tuple=(0.,0.,0.,1.)
    selectable:bool=True
@dataclass(frozen=True)
class EraseAssetPlacement:
    uuid:str
@dataclass(frozen=True)
class CreateMemoryBinding:
    uuid:str
    name:str
    asset_id:str
    asset_sha256:str
    pack_sha256:str
    position:tuple=(-35.,1.,10.)
@dataclass(frozen=True)
class EraseMemoryBinding:
    uuid:str
@dataclass(frozen=True)
class TypedRow:
    uuid:str
    type_id:str
    name:str
    fields:tuple
@dataclass(frozen=True)
class ContentDescription:
    definition_id:str
    content_revision:int
    fingerprint:str
    dirty:bool
    known_count:int
@dataclass(frozen=True)
class ContentDependencies:
    gameplay_save_compatible:bool
    render_rebuild:bool
    collision_rebuild:bool
    power_dependencies:bool
    quest_dependencies:bool
    affected_ids:tuple
    dependencies:tuple
    navigation:str
@dataclass(frozen=True)
class ContentExportDependency:
    kind:int
    reference:'AssetDependency'
@dataclass(frozen=True)
class ContentExportChunk:
    definition_id:str
    fingerprint:str
    content_revision:int
    total:int
    offset:int
    payload:bytes
    version:int=1
    dependencies:tuple=()
@dataclass(frozen=True)
class ScopedEdit:
    project:str
    branch:str
    world_id:str
    definition_id:str
    operation_id:str
    revision:int
    fingerprint:str
    label:str
    edits:tuple

def _end(r):
    if r.offset!=len(r.data):raise PayloadError('Trailing typed command bytes')
def _fingerprint(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise PayloadError('Invalid content fingerprint')
    return value
def _identifier(value):
    w=_Writer();w.text(value,True)
    if len(value.encode('utf-8'))>256:raise PayloadError('Typed identifier byte limit')
    return value
def _boolean(r):
    value=r.number('B')
    if value not in (0,1):raise PayloadError('Invalid typed boolean')
    return bool(value)
def _value_writer(w,value):
    if type(value) is bool:w.number(0,'B');w.number(value,'B')
    elif type(value) is int:w.number(1,'B');w.number(value,'q')
    elif type(value) is float:
        if not math.isfinite(value):raise PayloadError('Nonfinite typed number')
        w.number(2,'B');w.number(value,'d')
    elif type(value) is str:w.number(3,'B');w.text(value)
    else:raise PayloadError('Unsupported typed value')
def _value_reader(r):
    kind=r.number('B')
    if kind==0:return _boolean(r)
    if kind==1:return r.number('q')
    if kind==2:
        number=r.number('d')
        if not math.isfinite(number):raise PayloadError('Nonfinite typed number')
        return number
    if kind==3:return r.text()
    raise PayloadError('Unknown typed value tag')
def _component(uuid,type_id,fields):
    fields=tuple(fields)
    if len(fields)>64 or len({k for k,_ in fields})!=len(fields):raise PayloadError('Typed component field limit/duplicate')
    w=_Writer();w.text(_uuid(uuid),True);w.text(_identifier(type_id),True);w.number(1,'I');w.number(len(fields),'I')
    for key,value in sorted(fields):w.text(_identifier(key),True);_value_writer(w,value)
    return b'AIBGCMP1'+struct.pack('<II',1,len(w.data))+bytes(w.data)
def _decode_component(data):
    r=_Reader(data)
    if r.read(8)!=b'AIBGCMP1' or r.number('I')!=1 or r.number('I')!=len(data)-16:raise PayloadError('Invalid typed component envelope')
    uuid=_uuid(r.text(True));type_id=_identifier(r.text(True));version=r.number('I');count=r.number('I')
    if version!=1 or count>64:raise PayloadError('Typed component version/field limit')
    fields=[];prior=None
    for _ in range(count):
        key=_identifier(r.text(True))
        if prior is not None and key<=prior:raise PayloadError('Duplicate/unordered typed component field')
        fields.append((key,_value_reader(r)));prior=key
    _end(r);return uuid,type_id,tuple(fields)
def _raw(w,data):w.number(len(data),'I');w.append(data)
def _read_raw(r):return r.read(r.number('I'))
def _float32(value):
    if type(value) not in (float,int):raise PayloadError('Fixture values require numbers')
    try:result=struct.unpack('<f',struct.pack('<f',value))[0]
    except (OverflowError,struct.error) as error:raise PayloadError('Fixture number exceeds float32 range') from error
    if not math.isfinite(result):raise PayloadError('Nonfinite fixture number')
    return result
def _fixture_fields(edit):
    if len(edit.center)!=3 or len(edit.half_extent)!=3 or len(edit.color)!=3 or len(edit.rotation)!=4 or type(edit.selectable) is not bool or type(edit.name) is not str:raise PayloadError('Invalid fixture vectors/name/selection flag')
    fields={'name':edit.name,'selectable':edit.selectable,'emission':_float32(edit.emission),'sheltered_emission':_float32(edit.sheltered_emission)}
    for prefix,values,axes in (('',edit.center,'xyz'),('half_',edit.half_extent,'xyz'),('color_',edit.color,'xyz'),('rotation_',edit.rotation,'xyzw')):
        for axis,value in zip(axes,values):fields[prefix+axis]=_float32(value)
    return tuple(sorted(fields.items()))

def _placement_fields(edit):
    from .project_assets import AssetDependency
    AssetDependency(edit.asset_id,edit.asset_sha256,edit.pack_sha256)
    if len(edit.center)!=3 or len(edit.scale)!=3 or len(edit.rotation)!=4 or type(edit.selectable) is not bool or type(edit.name) is not str:
        raise PayloadError('Invalid asset placement vectors/name')
    fields={'name':edit.name,'asset_id':edit.asset_id,'asset_sha256':edit.asset_sha256,
            'pack_sha256':edit.pack_sha256,'selectable':edit.selectable}
    for prefix,values,axes in (('',edit.center,'xyz'),('scale_',edit.scale,'xyz'),('rotation_',edit.rotation,'xyzw')):
        for axis,value in zip(axes,values):fields[prefix+axis]=_float32(value)
    if any(fields['scale_'+axis]<=0 for axis in 'xyz') or abs(sum(fields['rotation_'+axis]**2 for axis in 'xyzw')-1)>1e-4:
        raise PayloadError('Asset placement requires positive scale and a unit quaternion')
    return tuple(sorted(fields.items()))
def _memory_fields(edit):
    from .project_assets import AssetDependency
    AssetDependency(edit.asset_id,edit.asset_sha256,edit.pack_sha256)
    if type(edit.name) is not str or not edit.name or '\0' in edit.name or len(edit.name.encode('utf-8'))>4096 or len(edit.position)!=3:
        raise PayloadError('Invalid memory station name or position')
    fields={'name':edit.name,'audio_asset_id':edit.asset_id,'audio_asset_sha256':edit.asset_sha256,'audio_pack_sha256':edit.pack_sha256}
    for axis,value in zip('xyz',edit.position):
        fields[axis]=_float32(value)
        if abs(fields[axis])>1000000:raise PayloadError('Memory position exceeds native world bounds')
    return tuple(sorted(fields.items()))
def encode_scoped_edit(scope,definition_id,operation_id,revision,fingerprint,label,edits):
    if type(revision) is not int or not 0<=revision<2**64:raise PayloadError('Invalid authoring revision')
    edits=tuple(edits)
    if not 1<=len(edits)<=256:raise PayloadError('Typed edit count limit')
    version=(3 if any(isinstance(edit,(CreateMemoryBinding,EraseMemoryBinding)) for edit in edits)
        else 2 if any(isinstance(edit,(CreateAssetPlacement,EraseAssetPlacement)) for edit in edits) else 1)
    body=_Writer();body.number(version,'H');body.text(operation_id,True);body.number(revision,'Q');body.text(_fingerprint(fingerprint),True);body.text(label);body.number(len(edits),'I')
    for edit in edits:
        if isinstance(edit,SetField):body.number(0,'B');_raw(body,_component(edit.uuid,'authoring.Field',((edit.field,edit.value),)))
        elif isinstance(edit,CreateFixture):body.number(1,'B');_raw(body,_component(edit.uuid,'authoring.Fixture',_fixture_fields(edit)))
        elif isinstance(edit,EraseFixture):body.number(2,'B');body.text(_uuid(edit.uuid),True)
        elif isinstance(edit,CreateHardware):
            fields=tuple(edit.fields)
            if any(type(v) is not float for _,v in fields):raise PayloadError('Hardware fields require numeric doubles')
            body.number(3,'B');_raw(body,_component(edit.uuid,'firstboot.Node',(('alias',edit.alias),('name',edit.name),('alive',True))+fields))
        elif isinstance(edit,EraseHardware):body.number(4,'B');body.text(_uuid(edit.uuid),True)
        elif isinstance(edit,CreateAssetPlacement):body.number(5,'B');_raw(body,_component(edit.uuid,'authoring.AssetPlacement',_placement_fields(edit)))
        elif isinstance(edit,EraseAssetPlacement):body.number(6,'B');body.text(_uuid(edit.uuid),True)
        elif isinstance(edit,CreateMemoryBinding):body.number(7,'B');_raw(body,_component(edit.uuid,'authoring.MemoryBinding',_memory_fields(edit)))
        elif isinstance(edit,EraseMemoryBinding):body.number(8,'B');body.text(_uuid(edit.uuid),True)
        else:raise PayloadError('Unknown typed edit')
    packet=_Writer();packet.append(b'AIBP');packet.number(1,'H')
    for text in (scope.project,scope.branch,_uuid(scope.world_id),_uuid(definition_id)):packet.text(text,True)
    _raw(packet,bytes(body.data));return bytes(packet.data)
def decode_scoped_edit(data):
    r=_Reader(data)
    if r.read(4)!=b'AIBP' or r.number('H')!=1:raise PayloadError('Unsupported scoped content request')
    project,branch,world,definition=r.text(True),r.text(True),_uuid(r.text(True)),_uuid(r.text(True));body=_Reader(_read_raw(r));_end(r)
    version=body.number('H')
    if version not in (1,2,3):raise PayloadError('Unsupported typed edit version')
    identity,revision,fp,label=body.text(True),body.number('Q'),_fingerprint(body.text(True)),body.text();count=body.number('I')
    if not 1<=count<=256:raise PayloadError('Typed edit count limit')
    edits=[]
    for _ in range(count):
        tag=body.number('B')
        if tag in (0,1,3,5,7):
            if tag==5 and version<2:raise PayloadError('Asset placement requires typed edit version 2')
            if tag==7 and version!=3:raise PayloadError('Memory creation requires typed edit version 3')
            uid,kind,fields=_decode_component(_read_raw(body));values=dict(fields)
            if tag==0:
                if kind!='authoring.Field' or len(fields)!=1:raise PayloadError('Invalid typed field edit')
                edits.append(SetField(uid,fields[0][0],fields[0][1]))
            elif tag==1:
                if kind!='authoring.Fixture' or len(fields)!=17:raise PayloadError('Invalid fixture edit')
                try:
                    edit=CreateFixture(uid,values['name'],tuple(values[k] for k in ('x','y','z')),tuple(values['half_'+k] for k in 'xyz'),tuple(values['color_'+k] for k in 'xyz'),values['emission'],values['selectable'],tuple(values['rotation_'+k] for k in 'xyzw'),values['sheltered_emission'])
                    if _fixture_fields(edit)!=fields:raise PayloadError('Noncanonical fixture field types')
                except (KeyError,TypeError,ValueError) as error:raise PayloadError('Invalid fixture fields') from error
                edits.append(edit)
            elif tag==3:
                if kind!='firstboot.Node' or values.pop('alive',None) is not True:raise PayloadError('Invalid hardware edit')
                try:alias,name=values.pop('alias'),values.pop('name')
                except KeyError as error:raise PayloadError('Missing hardware names') from error
                if type(alias) is not str or type(name) is not str or any(type(v) is not float for v in values.values()):raise PayloadError('Invalid hardware field types')
                edits.append(CreateHardware(uid,alias,name,tuple(sorted(values.items()))))
            elif tag==5:
                if kind!='authoring.AssetPlacement' or len(fields)!=15:raise PayloadError('Invalid asset placement component')
                try:
                    edit=CreateAssetPlacement(uid,values['name'],values['asset_id'],values['asset_sha256'],values['pack_sha256'],
                        tuple(values[k] for k in 'xyz'),tuple(values['scale_'+k] for k in 'xyz'),
                        tuple(values['rotation_'+k] for k in 'xyzw'),values['selectable'])
                    if _placement_fields(edit)!=fields:raise PayloadError('Noncanonical asset placement fields')
                except (KeyError,TypeError,ValueError) as error:raise PayloadError('Invalid asset placement fields') from error
                edits.append(edit)
            else:
                if kind!='authoring.MemoryBinding' or len(fields)!=7:raise PayloadError('Invalid memory binding component')
                try:
                    edit=CreateMemoryBinding(uid,values['name'],values['audio_asset_id'],values['audio_asset_sha256'],values['audio_pack_sha256'],tuple(values[k] for k in 'xyz'))
                    if _memory_fields(edit)!=fields:raise PayloadError('Noncanonical memory field types')
                except (KeyError,TypeError,ValueError) as error:raise PayloadError('Invalid memory binding fields') from error
                edits.append(edit)
        elif tag==2:edits.append(EraseFixture(_uuid(body.text(True))))
        elif tag==4:edits.append(EraseHardware(_uuid(body.text(True))))
        elif tag==6:
            if version<2:raise PayloadError('Asset placement requires typed edit version 2')
            edits.append(EraseAssetPlacement(_uuid(body.text(True))))
        elif tag==8:
            if version!=3:raise PayloadError('Memory erasure requires typed edit version 3')
            edits.append(EraseMemoryBinding(_uuid(body.text(True))))
        else:raise PayloadError('Unknown typed edit kind')
    _end(body)
    result=ScopedEdit(project,branch,world,definition,identity,revision,fp,label,tuple(edits))
    scope=Scope(project,branch,world,'')
    if encode_scoped_edit(scope,definition,identity,revision,fp,label,result.edits)!=data:raise PayloadError('Noncanonical scoped content edit')
    return result
def edit_command(scope,packet):
    parsed=decode_scoped_edit(packet)
    if (scope.project,scope.branch,scope.world_id)!=(parsed.project,parsed.branch,parsed.world_id):raise PayloadError('Typed wrapper scope differs from proposal')
    w=_scope_writer(scope);_raw(w,packet);return bytes(w.data)
def command_revision(payload):
    r=_Reader(payload)
    if r.number('H')!=1:raise PayloadError('Unsupported typed command version')
    scope=Scope(r.text(True),r.text(True),_uuid(r.text(True)),_uuid(r.text(True)));packet=_read_raw(r);_end(r);parsed=decode_scoped_edit(packet)
    if (scope.project,scope.branch,scope.world_id)!=(parsed.project,parsed.branch,parsed.world_id):raise PayloadError('Typed command scope mismatch')
    return parsed.revision
def open_document(project,branch,create=False):
    if type(create) is not bool:raise PayloadError('Invalid chapter open mode')
    w=_Writer();w.number(1,'H');w.text(project,True);w.text(branch,True);w.number(create,'B');return bytes(w.data)
def snapshot_page(scope,checkpoint,after='',limit=32):
    if type(limit) is not int or not 1<=limit<=32:raise PayloadError('Invalid typed page limit')
    _uuid(after,True);w=_scope_writer(scope);w.text(_uuid(checkpoint,True));w.text(after);w.number(limit,'I');return bytes(w.data)
def history(scope,operation_id,redo,fingerprint):
    if type(redo) is not bool:raise PayloadError('Invalid history direction')
    w=_scope_writer(scope);w.text(operation_id,True);w.number(redo,'B');w.text(_fingerprint(fingerprint),True);return bytes(w.data)
def decode_description(data):
    r=_Reader(data);result=ContentDescription(_uuid(r.text(True)),r.number('Q'),_fingerprint(r.text(True)),_boolean(r),r.number('I'));_end(r)
    if not 1<=result.known_count<=10000:raise PayloadError('Invalid known identity count')
    return result
def decode_page(data):
    r=_Reader(data);cursor=_uuid(r.text(),True);more=_boolean(r);count=r.number('I')
    if count>32:raise PayloadError('Typed page row limit')
    rows=[];prior=None
    for _ in range(count):
        uid=_uuid(r.text(True));kind=r.text(True);name=r.text();fields_count=r.number('I')
        if fields_count>1024 or (prior is not None and uid<=prior):raise PayloadError('Typed page fields/order limit')
        fields=[];key_before=None
        for _ in range(fields_count):
            key=_identifier(r.text(True))
            if key_before is not None and key<=key_before:raise PayloadError('Duplicate/unordered typed field')
            fields.append((key,_value_reader(r)));key_before=key
        rows.append(TypedRow(uid,kind,name,tuple(fields)));prior=uid
    _end(r)
    if rows and cursor!=rows[-1].uuid:raise PayloadError('Typed page cursor disagrees with last row')
    if more and not rows:raise PayloadError('Typed page failed to advance')
    return tuple(rows),cursor,more
def decode_preview(data):
    r=_Reader(data);flags=tuple(_boolean(r) for _ in range(5));count=r.number('I')
    if count>10000:raise PayloadError('Typed affected identity limit')
    affected=tuple(_uuid(r.text(True)) for _ in range(count));count=r.number('I')
    if count>128 or len(set(affected))!=len(affected):raise PayloadError('Typed preview dependencies/identity limit')
    dependencies=tuple(r.text() for _ in range(count));navigation=r.text();_end(r)
    return ContentDependencies(*flags,affected,dependencies,navigation)

def export_content(scope,offset,limit,fingerprint,*,complete_dependencies=False):
    if type(offset) is not int or not 0<=offset<=1024*1024:raise PayloadError('Invalid export offset')
    if type(limit) is not int or not 1<=limit<=256*1024:raise PayloadError('Invalid export chunk limit')
    if type(complete_dependencies) is not bool:raise PayloadError('Invalid complete dependency export mode')
    w=_scope_writer(scope);w.number(2 if complete_dependencies else 1,'B');w.number(offset,'I');w.number(limit,'I');w.text(_fingerprint(fingerprint),True)
    return bytes(w.data)

def validate_content_export_dependencies(dependencies):
    """Copy the complete canonical native closure; never infer it from UI rows."""
    from .project_assets import AssetDependency
    if type(dependencies) is not tuple or len(dependencies)>32:raise PayloadError('Complete dependency count/ownership limit')
    result=[];previous=None
    for dependency in dependencies:
        if (type(dependency) is not ContentExportDependency or type(dependency.kind) is not int
                or dependency.kind not in (0,1,2) or type(dependency.reference) is not AssetDependency):
            raise PayloadError('Invalid complete dependency kind/reference')
        reference=dependency.reference
        try:owned=AssetDependency(reference.asset_id,reference.asset_sha256,reference.pack_sha256)
        except (ValueError,TypeError,AttributeError) as error:raise PayloadError('Invalid immutable export dependency') from error
        if previous is not None and owned.pack_sha256<=previous:raise PayloadError('Duplicate/unordered complete dependency pack')
        result.append(ContentExportDependency(dependency.kind,owned));previous=owned.pack_sha256
    return tuple(result)

def decode_content_export(data):
    r=_Reader(data)
    version=r.number('H')
    if version not in (1,2):raise PayloadError('Unsupported content export version')
    definition=_uuid(r.text(True));fingerprint=_fingerprint(r.text(True));revision=r.number('Q')
    total,offset,count=(r.number('I') for _ in range(3))
    if not 1<=total<=1024*1024 or offset>=total or not 1<=count<=256*1024 or count>total-offset:
        raise PayloadError('Invalid content export range')
    dependencies=()
    if version==2:
        from .project_assets import AssetDependency
        reference_count=r.number('I')
        if reference_count>32:raise PayloadError('Complete dependency count limit')
        records=[]
        for _ in range(reference_count):
            kind=r.number('B')
            try:reference=AssetDependency(r.text(True),r.text(True),r.text(True))
            except (ValueError,TypeError) as error:raise PayloadError('Invalid immutable export dependency') from error
            records.append(ContentExportDependency(kind,reference))
        dependencies=validate_content_export_dependencies(tuple(records))
    result=ContentExportChunk(definition,fingerprint,revision,total,offset,r.read(count),version,dependencies);_end(r)
    return result
