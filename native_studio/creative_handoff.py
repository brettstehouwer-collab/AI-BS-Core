"""Source-specific creative handoffs; saving a plan never submits a GPU job."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from xml.etree import ElementTree as ET

MAX_BYTES=16*1024*1024

def active_script_snapshot(provider):
    if not callable(provider):raise ValueError('Open a screenplay in the Writing Studio first.')
    value=provider()
    if not isinstance(value,dict) or not isinstance(value.get('content'),str) or not value['content'].strip():
        raise ValueError('The active screenplay has no text. Existing scene plans were retained.')
    raw=value['content'].encode('utf-8',errors='strict')
    if len(raw)>MAX_BYTES:raise ValueError('This screenplay exceeds the16 MiB planning limit.')
    return {**value,'source_kind':'active_editor','content_sha256':hashlib.sha256(raw).hexdigest()}

def read_script_snapshot(file_path):
    path=Path(file_path)
    if path.stat().st_size>MAX_BYTES:raise ValueError('This script exceeds the16 MiB planning limit.')
    raw=path.read_bytes()
    if not raw:raise ValueError('The selected script is empty.')
    if path.suffix.lower()=='.fdx':
        probe=raw.upper().replace(b'\x00',b'')
        if b'<!DOCTYPE' in probe or b'<!ENTITY' in probe:raise ValueError('FDX entity declarations are unsupported.')
        root=ET.fromstring(raw)
        body=root.find('Content')
        if root.tag!='FinalDraft' or body is None or len(root.findall('Content'))!=1:raise ValueError('Expected one Final Draft screenplay body.')
        texts=[]
        def paragraph(node):
            # Only body paragraphs and explicit dual-dialogue children; never note descendants.
            if any(list(t) for t in node.findall('Text')):
                raise ValueError('Nested authored FDX text cannot be completely extracted for planning. Original retained.')
            if any(child.tag not in {'Text','ScriptNote','DualDialogue'} for child in node):
                raise ValueError('Unknown authored FDX paragraph content cannot be completely extracted for planning. Original retained.')
            text=''.join(t.text or '' for t in node.findall('Text'))
            if text.strip():texts.append(text)
            for dual in node.findall('DualDialogue'):
                for child in dual:
                    if child.tag!='Paragraph':raise ValueError('Unknown FDX dual-dialogue content cannot be completely extracted for planning. Original retained.')
                    paragraph(child)
        for node in body:
            if node.tag=='Paragraph':paragraph(node)
            elif node.tag=='DualDialogue':
                for child in node:
                    if child.tag!='Paragraph':raise ValueError('Unknown FDX dual-dialogue content cannot be completely extracted for planning. Original retained.')
                    paragraph(child)
            else:raise ValueError('Unknown FDX body content cannot be completely extracted for planning. Original retained.')
        content='\n\n'.join(texts)
        kind='file_fdx'
    elif path.suffix.lower() in {'.txt','.fountain'}:
        content=raw.decode('utf-8-sig',errors='strict');kind='file_text'
    else:raise ValueError('Choose a UTF-8 text, Fountain or FDX file.')
    if not content.strip():raise ValueError('No screenplay body text was found. Existing scene plans were retained.')
    return dict(content=content,source_kind=kind,source_name=path.name,
                source_sha256=hashlib.sha256(raw).hexdigest(),content_sha256=hashlib.sha256(content.encode('utf-8')).hexdigest())

def save_batch_plan(output_dir,workflow,scenes,source,port):
    if not isinstance(scenes,list) or not scenes or len(scenes)>10000:raise ValueError('Add a scene before saving a batch plan.')
    for scene in scenes:
        if (not isinstance(scene,dict) or not isinstance(scene.get('prompt'),str) or not scene['prompt'].strip()
                or type(scene.get('duration')) is not int or not 2<=scene['duration']<=60):
            raise ValueError('Each scene needs text and an estimated duration of2–60 seconds.')
    value=dict(schema='aibs_creative_batch_plan_v1',timestamp=time.time(),workflow=workflow,
               comfy_port=port,service_reachable=port is not None,scene_count=len(scenes),scenes=scenes,
               source=source,status='PLAN_SAVED',submitted=False,
               duration_basis='130 words/minute planning estimate, clamped2–60s; not measured screen time')
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2).encode('utf-8')
    if len(raw)>MAX_BYTES:raise ValueError('This batch plan exceeds16 MiB.')
    directory=Path(output_dir);directory.mkdir(parents=True,exist_ok=True)
    target=directory/('comfy_batch_plan_'+uuid.uuid4().hex+'.json')
    with target.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    actual=target.read_bytes()
    if actual!=raw:raise OSError('Batch plan readback did not match the captured scenes.')
    return dict(port=port,count=len(scenes),manifest=str(target),sha256=hashlib.sha256(actual).hexdigest(),submitted=False)
