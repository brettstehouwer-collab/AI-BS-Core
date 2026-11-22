"""Strict model-output admission for chapter field proposals; no model/code execution."""
from dataclasses import dataclass
import json,math,re,struct
from .creator_payload import _Writer,_uuid,MAX_BYTES
from .opening_fields import INSPECTION_FIELDS,inspection_value
from .workshop_fields import WORKSHOP_BINDING_FIELD,WORKSHOP_ROLE_FIELD

COMPANION_MODEL_REFERENCE_FIELDS=frozenset(('model_bound','model_asset_id','model_asset_sha256','model_pack_sha256'))
MEMORY_AUDIO_REFERENCE_FIELDS=frozenset(('audio_asset_id','audio_asset_sha256','audio_pack_sha256'))

def _text(value,limit=4096,required=True):
    if type(value) is not str or '\0' in value or (required and not value):raise ValueError('Invalid proposal text')
    if len(value.encode('utf-8',errors='strict'))>limit:raise ValueError('Proposal text limit')
    return value

@dataclass(frozen=True)
class ProposalContext:
    project:str
    branch:str
    world_id:str
    definition_id:str
    revision:int
    fingerprint:str
    fields:tuple

    @classmethod
    def from_dict(cls,data):
        if type(data) is not dict or set(data)!={'project','branch','world_id','definition_id','revision','fingerprint','fields'}:raise ValueError('Invalid proposal context')
        if type(data['revision']) is not int or not 0<=data['revision']<2**64:raise ValueError('Invalid context revision')
        if type(data['fingerprint']) is not str or not re.fullmatch('[0-9a-f]{64}',data['fingerprint']):raise ValueError('Invalid context fingerprint')
        if type(data['fields']) is not list or not 1<=len(data['fields'])<=10000:raise ValueError('Context field limit')
        fields=[];seen=set()
        for item in data['fields']:
            if type(item) is not list or len(item)!=3 or item[2] not in ('number','text','boolean'):raise ValueError('Invalid field capability')
            uid,key,kind=item;_uuid(uid);_text(key,256)
            if (uid,key) in seen:raise ValueError('Duplicate field capability')
            seen.add((uid,key));fields.append((uid,key,kind))
        return cls(_text(data['project']),_text(data['branch']),_uuid(data['world_id']),_uuid(data['definition_id']),data['revision'],data['fingerprint'],tuple(fields))

def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('Duplicate proposal JSON key')
        result[key]=value
    return result

def encode_proposal(source,context,operation_id):
    """Pin controller-owned context/id; the model supplies only label and field edits."""
    if type(source) is not str or len(source.encode('utf-8'))>MAX_BYTES:raise ValueError('Proposal byte limit')
    def invalid_constant(value):raise ValueError('Nonfinite proposal number')
    proposal=json.loads(source,object_pairs_hook=_pairs,parse_constant=invalid_constant)
    if type(proposal) is not dict or set(proposal)!={'version','label','edits'} or type(proposal['version']) is not int or proposal['version']!=1:raise ValueError('Unsupported proposal shape/version')
    edits=proposal['edits']
    if type(edits) is not list or not 1<=len(edits)<=256:raise ValueError('Proposal edit limit')
    allowed={(uid,key):kind for uid,key,kind in context.fields}
    w=_Writer();w.number(1,'H');w.text(_text(operation_id),True);w.number(context.revision,'Q');w.text(context.fingerprint,True);w.text('[AI proposal] '+_text(proposal['label']))
    w.number(len(edits),'I')
    for edit in edits:
        if type(edit) is not dict or set(edit)!={'entity_id','field','value'}:raise ValueError('Unsupported proposal edit')
        uid,key,value=edit['entity_id'],edit['field'],edit['value'];_uuid(uid);_text(key,256);kind=allowed.get((uid,key))
        if key in (WORKSHOP_BINDING_FIELD,WORKSHOP_ROLE_FIELD):raise ValueError('Workshop role and bindings require the verified grouped Workshop panel')
        if key in INSPECTION_FIELDS:inspection_value(key,value)
        if key in ('asset_id','asset_sha256','pack_sha256'):raise ValueError('Asset dependency references are immutable')
        if key in COMPANION_MODEL_REFERENCE_FIELDS:raise ValueError('Companion model references are immutable; assign a verified model through native Preview')
        if key in MEMORY_AUDIO_REFERENCE_FIELDS:raise ValueError('Memory audio references require a verified pack and grouped native Preview')
        component=_Writer();component.text(uid,True);component.text('authoring.Field',True);component.number(1,'I');component.number(1,'I');component.text(key,True)
        if kind=='number':
            if type(value) not in (int,float):raise ValueError('Proposal field requires a number')
            try:value=float(value)
            except (ValueError,OverflowError) as error:raise ValueError('Invalid proposal number') from error
            if not math.isfinite(value):raise ValueError('Nonfinite proposal number')
            component.number(2,'B');component.number(value,'d')
        elif kind=='text':component.number(3,'B');component.text(_text(value,required=False))
        elif kind=='boolean':
            if type(value) is not bool:raise ValueError('Proposal field requires a boolean')
            component.number(0,'B');component.number(value,'B')
        else:raise ValueError('Proposal target/field is outside the controller capability set')
        body=bytes(component.data);encoded=b'AIBGCMP1'+struct.pack('<II',1,len(body))+body
        w.number(0,'B');w.number(len(encoded),'I');w.append(encoded)
    packet=_Writer();packet.append(b'AIBP');packet.number(1,'H')
    for value in (context.project,context.branch,context.world_id,context.definition_id):packet.text(value,True)
    packet.number(len(w.data),'I');packet.append(bytes(w.data))
    return bytes(packet.data)
