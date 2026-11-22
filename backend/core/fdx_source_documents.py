"""Owner-scoped immutable FDX documents and bounded rich-text edits.

XML is inert source data. Existing paragraph text/type edits are supported;
unknown structures remain preserved and are never converted to plain text.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from xml.dom import minidom, Node

from core.personal_memory_scope import current_memory_principal

SCHEMA='aibs_rich_fdx_v1'
MAX_BYTES=16*1024*1024
MAX_BLOCKS=50000
FENCE='source_fdx.json'
TYPES={'Action','Scene Heading','Character','Dialogue','Parenthetical','Transition','General','Shot'}

class FDXSourceError(ValueError):
    def __init__(self,message,status=409):
        super().__init__(message);self.status=status

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')
def _plain(path):
    path=Path(path)
    if any(item.is_symlink() or getattr(item,'is_junction',lambda:False)() for item in (path,*path.parents)):
        raise FDXSourceError('Linked FDX storage is unsupported; existing files were retained.')
    return path
def _read(path):
    path=_plain(path)
    if not path.is_file() or path.stat().st_size>MAX_BYTES:raise FDXSourceError('FDX evidence is missing or oversized.')
    return path.read_bytes()
def _once(path,raw):
    _plain(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if _read(path)!=raw:raise FDXSourceError('A retained FDX version conflicts; existing bytes were preserved.')
        return
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
def _atomic(path,raw):
    _plain(path);temporary=path.parent/('.fdx-'+uuid.uuid4().hex+'.tmp')
    _once(temporary,raw);os.replace(temporary,path)
def _children(node,name=None):
    return [child for child in node.childNodes if child.nodeType==Node.ELEMENT_NODE and (name is None or child.tagName==name)]
def _attrs(node):return {name:node.getAttribute(name) for name in node.attributes.keys()}
def _text(node):return ''.join(child.data for child in node.childNodes if child.nodeType in (Node.TEXT_NODE,Node.CDATA_SECTION_NODE))
def _all_text(node):
    return ''.join(_all_text(child) if child.nodeType==Node.ELEMENT_NODE else child.data if child.nodeType in (Node.TEXT_NODE,Node.CDATA_SECTION_NODE) else '' for child in node.childNodes)
def _document(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise FDXSourceError('FDX must contain bounded original XML bytes.',422)
    try:text=raw.decode('utf-8-sig')
    except UnicodeError as error:raise FDXSourceError('FDX must be valid UTF-8; original bytes were not changed.',422) from error
    if re.search(r'<!DOCTYPE|<!ENTITY',text,re.I):raise FDXSourceError('FDX declarations/entities are unsupported.',422)
    try:document=minidom.parseString(raw)
    except Exception as error:raise FDXSourceError('FDX XML is invalid; original bytes were not changed.',422) from error
    if document.documentElement.tagName!='FinalDraft':raise FDXSourceError('Expected a Final Draft document.',422)
    stack=[(document.documentElement,0)];count=0
    while stack:
        node,depth=stack.pop();count+=1
        if depth>64 or count>500000:raise FDXSourceError('FDX XML exceeds the bounded structure profile.',422)
        stack.extend((child,depth+1) for child in _children(node))
    if len(_children(document.documentElement,'Content'))!=1:raise FDXSourceError('Expected exactly one script Content section.',422)
    return document

def _body_nodes(document):
    content=_children(document.documentElement,'Content')[0];result=[];warnings=[]
    for child in _children(content):
        if child.tagName=='Paragraph':result.append((child,None,None))
        elif child.tagName=='DualDialogue':
            group='dual-'+str(len(result));side='left';characters=0
            for paragraph in _children(child):
                if paragraph.tagName!='Paragraph':
                    warnings.append('Unknown dual-dialogue child retained: '+paragraph.tagName);continue
                if paragraph.getAttribute('Type')=='Character':
                    characters+=1
                    if characters>=2:side='right'
                result.append((paragraph,group,side))
            if characters!=2:warnings.append('Dual dialogue does not have exactly two character cues; structure is preserved.')
        else:warnings.append('Unknown body section retained: '+child.tagName)
    if len(result)>MAX_BLOCKS:raise FDXSourceError('Too many FDX paragraphs.',422)
    return result,warnings

def parse_fdx(raw):
    document=_document(raw);nodes,warnings=_body_nodes(document);blocks=[]
    def block(paragraph,identifier,group=None,side=None):
        text_nodes=_children(paragraph,'Text')
        runs=[{'id':identifier+'-r'+str(index),'text':_text(node),'attributes':_attrs(node)} for index,node in enumerate(text_nodes)]
        notes=[{'id':identifier+'-n'+str(index),'text':_all_text(node),'attributes':_attrs(node)} for index,node in enumerate(_children(paragraph,'ScriptNote'))]
        unknown=[node.tagName for node in _children(paragraph) if node.tagName not in {'Text','ScriptNote'}]
        unknown.extend('Text/'+child.tagName for node in text_nodes for child in _children(node))
        if unknown:warnings.append('Unsupported nested paragraph content retained: '+','.join(unknown))
        return {'id':identifier,'type':paragraph.getAttribute('Type') or 'General','text':''.join(run['text'] for run in runs),
                'attributes':_attrs(paragraph),'runs':runs,'notes':notes,'startsNewPage':paragraph.getAttribute('StartsNewPage')=='Yes',
                'dualGroup':group,'dualSide':side,'dual':side=='right' and paragraph.getAttribute('Type')=='Character',
                'editable':not unknown,'edit_operations':[]}
    for index,(paragraph,group,side) in enumerate(nodes):blocks.append(block(paragraph,'fdx-'+str(index),group,side))
    title=[]
    for page in _children(document.documentElement,'TitlePage'):
        for content in _children(page,'Content'):
            title.extend(block(paragraph,'title-'+str(index)) for index,paragraph in enumerate(_children(content,'Paragraph')))
    metadata=[node.tagName for node in _children(document.documentElement) if node.tagName not in {'Content','TitlePage'}]
    return {'schema':SCHEMA,'source_sha256':digest(raw),'document_sha256':digest(raw),'blocks':blocks,'title_page':title,
            'preserved_sections':metadata,'warnings':sorted(set(warnings)),
            'editing_subset':'existing-paragraph-text-and-type','structural_editing_supported':False}

def projection_with_spans(document):
    title=document.get('title_page',[]);header=[]
    if title:
        header.append('Title: '+title[0]['text'].replace('\n','\n    '))
        authors=[item['text'] for item in title[1:] if item['type']=='Author']
        other=[item['text'] for item in title[1:] if item['type']!='Author']
        if authors:header.append('Author: '+'\n'.join(authors).replace('\n','\n    '))
        if other:header.append('Notes: '+'\n'.join(other).replace('\n','\n    '))
    text='\n'.join(header)+'\n\n' if header else ''
    spans=[]
    for block in document['blocks']:
        if block.get('startsNewPage') and text:text+='\n\n===\n\n'
        separator='\n' if block['type'] in {'Dialogue','Parenthetical'} else '\n\n' if text and not text.endswith('\n\n') else ''
        text+=separator
        start=len(text);text+=block['text']
        spans.append({'id':block['id'],'type':block['type'],'start':start,'end':len(text),'text':block['text']})
    return text,spans

def projection(document):return projection_with_spans(document)[0]

def _edit_runs(runs,start,end,replacement):
    length=sum(len(run['text']) for run in runs)
    if type(start)is not int or type(end)is not int or not 0<=start<=end<=length or not isinstance(replacement,str):raise FDXSourceError('Invalid Unicode FDX edit range.',422)
    result=[];position=0;inserted=False
    anchor=runs[-1] if runs else {'id':'new','attributes':{}}
    boundary=0
    for candidate in runs:
        boundary+=len(candidate['text'])
        if start<boundary:anchor=candidate;break
    def insert():
        nonlocal inserted
        if replacement:
            attributes={key:value for key,value in anchor['attributes'].items() if key!='RevisionID'}
            result.append({'id':anchor['id'],'text':replacement,'attributes':attributes})
        inserted=True
    for run in runs:
        finish=position+len(run['text'])
        if position<start:
            prefix=run['text'][:max(0,min(start,finish)-position)]
            if prefix:result.append({**run,'text':prefix})
        if not inserted and start<=finish:insert()
        if finish>end:
            suffix=run['text'][max(end-position,0):]
            if suffix:result.append({**run,'text':suffix})
        position=finish
    if not inserted:insert()
    return result

def apply_snapshot(raw,snapshot,applied=None):
    current=parse_fdx(raw);applied=dict(applied or {})
    if not isinstance(snapshot,dict) or snapshot.get('schema')!=SCHEMA or not isinstance(snapshot.get('blocks'),list):raise FDXSourceError('Rich FDX edits require the typed document snapshot. Preserve the draft or create a working copy.',428)
    if set(snapshot)-set(current)-{'applied_operation_ids'}:raise FDXSourceError('Unsupported rich document fields cannot be silently acknowledged.',422)
    blocks=snapshot['blocks']
    if snapshot.get('document_sha256',digest(raw))!=digest(raw):raise FDXSourceError('The rich document snapshot belongs to a different current revision.')
    for key in ('title_page','preserved_sections','warnings','editing_subset','structural_editing_supported'):
        if key in snapshot and snapshot[key]!=current[key]:raise FDXSourceError('Unsupported readonly FDX metadata change: '+key,422)
    if 'applied_operation_ids' in snapshot and snapshot['applied_operation_ids']!=list(applied):raise FDXSourceError('Rich edit acknowledgment changed; rebase only from a confirmed response.')
    if len(encoded(snapshot))>MAX_BYTES or any(not isinstance(item,dict) for item in blocks):raise FDXSourceError('Invalid or oversized rich document snapshot.',422)
    if len(blocks)!=len(current['blocks']) or [item.get('id') for item in blocks]!=[item['id'] for item in current['blocks']]:raise FDXSourceError('Structural FDX edits are not qualified. Your draft can be preserved as a separate working copy.',422)
    document=_document(raw);nodes,_=_body_nodes(document);changed=False
    for old,new,(paragraph,_,_) in zip(current['blocks'],blocks,nodes):
        if set(new)-set(old):raise FDXSourceError('Unsupported paragraph fields cannot be silently acknowledged.',422)
        if not isinstance(new.get('text'),str) or len(new['text'].encode('utf8'))>MAX_BYTES:raise FDXSourceError('Invalid FDX paragraph text.',422)
        runs=old['runs'];text=old['text'];operations=new.get('edit_operations',[])
        if not isinstance(operations,list) or len(operations)>4096:raise FDXSourceError('FDX edit history exceeds the bounded profile; save/reopen a confirmed version.',422)
        for operation in operations:
            if not isinstance(operation,dict) or not re.fullmatch('[a-f0-9]{32}',operation.get('id','')):raise FDXSourceError('FDX edit operation needs a unique identifier.',422)
            token=operation['id'];fingerprint=digest(encoded(operation))
            if token in applied:
                if applied[token]!=fingerprint:raise FDXSourceError('FDX edit identifier conflicts; original versions were retained.')
                continue
            if operation.get('before_text')!=text:raise FDXSourceError('FDX edit range belongs to a different paragraph revision.')
            if not old['editable']:raise FDXSourceError('This paragraph contains unsupported nested content; use a retained working copy.',422)
            runs=_edit_runs(runs,operation.get('start'),operation.get('end'),operation.get('text'))
            text=''.join(run['text'] for run in runs);applied[token]=fingerprint
        if text!=new['text']:raise FDXSourceError('Plain text changes lack qualified rich edit ranges. Preserve the draft or create a working copy.',422)
        def normalized_runs(values):
            normalized=[]
            for run in values:
                if not isinstance(run,dict) or not isinstance(run.get('text'),str) or not isinstance(run.get('attributes'),dict):raise FDXSourceError('Invalid readonly FDX text runs.',422)
                item={'text':run['text'],'attributes':run['attributes']}
                if normalized and normalized[-1]['attributes']==item['attributes']:normalized[-1]['text']+=item['text']
                elif item['text']:normalized.append(item)
            return normalized
        if 'runs' in new and normalized_runs(new['runs']) not in (normalized_runs(old['runs']),normalized_runs(runs)):
            raise FDXSourceError('Unsupported readonly FDX style/revision change; no version was published.',422)
        for key in ('notes','startsNewPage','dualGroup','dualSide','dual','editable'):
            if key in new and new[key]!=old[key]:raise FDXSourceError('Unsupported readonly FDX metadata change: '+key,422)
        if 'attributes' in new:
            candidate=dict(new['attributes']);baseline=dict(old['attributes'])
            candidate.pop('Type',None);baseline.pop('Type',None)
            if candidate!=baseline:raise FDXSourceError('Unsupported readonly paragraph attribute change.',422)
        if new.get('type')!=old['type'] and new.get('type') not in TYPES:raise FDXSourceError('Unsupported FDX paragraph type; original type was retained.',422)
        if text!=old['text'] or new.get('type')!=old['type']:
            if not old['editable']:raise FDXSourceError('Unsupported paragraph structure cannot be changed silently.',422)
            changed=True;paragraph.setAttribute('Type',new['type'])
            original_nodes=_children(paragraph,'Text');by_id={old['id']+'-r'+str(index):node for index,node in enumerate(original_nodes)}
            for identifier,node in by_id.items():
                for run in [run for run in runs if run['id']==identifier]:
                    replacement=document.createElement('Text')
                    for name,value in run['attributes'].items():replacement.setAttribute(name,value)
                    replacement.appendChild(document.createTextNode(run['text']));paragraph.insertBefore(replacement,node)
                paragraph.removeChild(node)
            if not original_nodes and runs:
                for run in runs:
                    replacement=document.createElement('Text');replacement.appendChild(document.createTextNode(run['text']));paragraph.appendChild(replacement)
    output=document.toxml(encoding='utf-8') if changed else raw
    result=parse_fdx(output)
    if [block['text'] for block in result['blocks']]!=[block['text'] for block in blocks]:raise FDXSourceError('Rich edit serialization did not preserve paragraph text; no version was published.',422)
    return output,result,applied

def fence(directory,owner=None):
    path=Path(directory)/FENCE
    if not path.exists() and not path.is_symlink():return None
    try:value=json.loads(_read(path))
    except (ValueError,UnicodeError) as error:raise FDXSourceError('FDX ownership/version evidence is invalid.') from error
    if value.get('schema')!=SCHEMA or value.get('owner')!=(owner or current_memory_principal()):raise FDXSourceError('This FDX project is not available for the signed-in account.',403)
    return value

def _version(directory,value):
    revision=value.get('revision','')
    if not re.fullmatch('[a-f0-9]{64}',revision):raise FDXSourceError('FDX version pointer is invalid.')
    base=Path(directory)/'fdx_versions'/revision
    raw=_read(base/'document.fdx');state=json.loads(_read(base/'state.json'))
    if digest(raw)!=revision or state.get('revision')!=revision:raise FDXSourceError('Retained FDX version changed; reads/exports were stopped.')
    original=_read(Path(directory)/'original.fdx')
    if digest(original)!=value.get('original_sha256'):raise FDXSourceError('Original FDX bytes changed; source qualification was stopped.')
    return raw,state

def read_project(directory,owner=None):
    value=fence(directory,owner)
    if value is None:return None
    if value.get('mode')=='working_copy':return None
    raw,state=_version(directory,value);document=parse_fdx(raw);document['source_sha256']=value['original_sha256']
    document['applied_operation_ids']=list(value.get('applied_operations',state.get('applied_operations',{})))
    content,spans=projection_with_spans(document)
    return {'content':content,'projection_spans':spans,'revision':value['revision'],'screenplay_exists':True,'source':'rich_fdx',
            'fdx_document':document,'body_ast':document['blocks'],
            'metadata':{'source_fdx':{'sha256':value['original_sha256'],'revision':value['revision'],
                        'warnings':document['warnings'],'preserved_sections':document['preserved_sections'],
                        'editing_subset':document['editing_subset'],'title_page':document['title_page']}}}

def read_canonical_snapshot(directory,owner=None):
    """Shared tool reader. Never mistake a legacy on-disk projection for rich canonical data.

    Callers hold their existing project-store lock. Explicit verified owner is
    preferred; request-bound current_memory_principal is the fallback.
    """
    result=read_project(directory,owner)
    if result is None:return None
    return {'project':Path(directory).name,'content':result['content'],
            'body_text':'\n\n'.join(block['text'] for block in result['body_ast']),
            'body_blocks':[{'id':block['id'],'type':block['type'],'text':block['text']} for block in result['body_ast']],
            'body_extraction_complete':not bool(result['fdx_document']['warnings']),
            'body_extraction_warnings':list(result['fdx_document']['warnings']),
            'projection_spans':result['projection_spans'],
            'revision':result['revision'],'source':'rich_fdx',
            'origin_sha256':result['metadata']['source_fdx']['sha256'],'owner_checked':True}

def _retain_version(directory,raw,applied):
    revision=digest(raw);base=Path(directory)/'fdx_versions'/revision
    _once(base/'document.fdx',raw)
    # Applied operations are a bounded deduplication ledger, not production revision history.
    state={'schema':SCHEMA,'revision':revision,'applied_operations':applied}
    path=base/'state.json'
    if path.exists():
        previous=json.loads(_read(path))
        if previous.get('revision')!=revision:raise FDXSourceError('Retained document state conflicts.')
    else:_once(path,encoded(state))
    return revision

def import_project(directory,raw,owner,request_id):
    if not isinstance(owner,str) or not owner or not re.fullmatch('[a-f0-9]{32}',request_id or ''):raise FDXSourceError('Authenticated FDX import needs a unique request identifier.',422)
    parsed=parse_fdx(raw);directory=_plain(Path(directory));revision=digest(raw)
    if directory.exists():
        value=fence(directory,owner)
        if value and value.get('original_sha256')==revision and value.get('request_id')==request_id:return read_project(directory,owner)
        raise FDXSourceError('A project with that name already exists; it was not overwritten.')
    staging=directory.parent.parent/'saved_data/fdx_import_recovery'/request_id/directory.name
    _plain(staging);staging.mkdir(parents=True,exist_ok=True)
    _once(staging/'original.fdx',raw);_retain_version(staging,raw,{})
    value={'schema':SCHEMA,'owner':owner,'original_sha256':revision,'revision':revision,'request_id':request_id,'applied_operations':{}}
    _once(staging/FENCE,encoded(value));os.rename(staging,directory)
    return read_project(directory,owner)

def write_project(directory,content,expected_revision,snapshot=None,owner=None):
    value=fence(directory,owner)
    if value is None:return None
    if not expected_revision:raise FDXSourceError('FDX saving requires the loaded revision.',428)
    if value['revision']!=expected_revision:raise FDXSourceError('The rich FDX document changed; preserve your draft before reloading.')
    raw,state=_version(directory,value);old=parse_fdx(raw)
    if snapshot is None:
        if content==projection(old):return {'revision':value['revision'],'unchanged':True}
        raise FDXSourceError('Changed plain text cannot replace a rich FDX document. Preserve it as a separate working copy.',428)
    if not isinstance(snapshot,dict) or snapshot.get('source_sha256')!=value['original_sha256']:raise FDXSourceError('The typed snapshot belongs to another FDX source.')
    output,document,applied=apply_snapshot(raw,snapshot,value.get('applied_operations',state.get('applied_operations',{})))
    if content!=projection(document):raise FDXSourceError('Typed FDX document and text projection disagree; draft retained.',422)
    if output==raw:
        if applied!=value.get('applied_operations',{}):_atomic(Path(directory)/FENCE,encoded({**value,'applied_operations':applied}))
        return {'revision':value['revision'],'unchanged':True}
    revision=_retain_version(directory,output,applied)
    _atomic(Path(directory)/FENCE,encoded({**value,'revision':revision,'applied_operations':applied}))
    return {'revision':revision,'unchanged':False}

def export_project(directory,expected_revision,owner=None,original=False):
    value=fence(directory,owner)
    if value is None:return None
    if not expected_revision:raise FDXSourceError('FDX export requires the loaded revision.',428)
    if value['revision']!=expected_revision:raise FDXSourceError('The rich FDX document changed before export.')
    raw,state=_version(directory,value)
    return _read(Path(directory)/'original.fdx') if original else raw

def create_working_copy(directory,destination,content,expected_revision,owner,request_id):
    """Explicit plain working copy retains its rich origin; never replaces the rich project."""
    value=fence(directory,owner)
    if value is None or value.get('mode')=='working_copy':raise FDXSourceError('A rich source project is required.',422)
    if not expected_revision or value['revision']!=expected_revision:raise FDXSourceError('Reload the confirmed rich revision before making a working copy.')
    _version(directory,value)
    if not isinstance(content,str) or len(content.encode('utf8'))>MAX_BYTES or not re.fullmatch('[a-f0-9]{32}',request_id or ''):raise FDXSourceError('A bounded working draft and unique request identifier are required.',422)
    destination=_plain(Path(destination))
    if destination.exists():raise FDXSourceError('The working-copy name already exists. No file was overwritten.')
    staging=destination.parent.parent/'saved_data/fdx_import_recovery'/request_id/destination.name
    _plain(staging);staging.mkdir(parents=True,exist_ok=True)
    _once(staging/'screenplay.fountain',content.encode('utf8'))
    _once(staging/FENCE,encoded({'schema':SCHEMA,'owner':owner,'mode':'working_copy',
        'origin_sha256':value['original_sha256'],'origin_revision':expected_revision,
        'warning':'Explicit plain-text working copy; rich runs, notes and metadata remain in the original source project.'}))
    os.rename(staging,destination)
    return {'project':destination.name,'revision':digest(content.encode('utf8')),
        'warning':'Plain working copy created separately. The original rich FDX and all prior versions remain unchanged.'}
