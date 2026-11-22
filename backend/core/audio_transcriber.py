"""Owned immutable audio transcript versions; indexing is qualified separately."""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid
from fastapi import HTTPException
from core.adaptation_store import mutex
from core.chat_pdf_sources import PDFSourceError, _write_once
from core.fdx_source_documents import FDXSourceError, read_canonical_snapshot
from core.personal_memory_scope import current_memory_principal
SCREENPLAY_ROOT=Path('C:/AI-BS/screenplay_projects')
AUDIO_TRANSCRIBE_TASKS={}
_ACTIVE=set();_TASK_LOCK=threading.RLock()
MAX_AUDIO_BYTES=256*1024*1024;MAX_TEXT_BYTES=8*1024*1024
SCHEMA='aibs_audio_transcript_v1'
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _json(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')
def _error(message,status=409):return HTTPException(status,{'code':'AUDIO_TRANSCRIPT_EVIDENCE','message':message})
def _owner(owner):
    owner=owner if owner is not None else current_memory_principal()
    if not isinstance(owner,str) or not owner or len(owner)>512:raise _error('A verified audio project owner is required.',403)
    return owner
def _key(project,owner):return (_sha(owner.encode('utf8')),project)
def _plain(path):
    for item in (path,*path.parents):
        if item.is_symlink() or getattr(item,'is_junction',lambda:False)() or (item.exists() and getattr(item.stat(),'st_file_attributes',0)&0x400):raise _error('Linked audio storage is unsupported.')
def _directory(project,owner):
    from core.project_rag import _project
    directory=_project(project,owner);_plain(directory)
    if directory.parent.resolve()!=Path(SCREENPLAY_ROOT).resolve():raise _error('Audio project store configuration differs.')
    try:read_canonical_snapshot(directory,owner=owner)
    except FDXSourceError as error:raise _error(str(error),error.status) from None
    return directory
def _read(path,maximum):
    _plain(path)
    try:
        with path.open('rb') as stream:raw=stream.read(maximum+1)
    except OSError:raise _error('Retained audio evidence is unavailable.') from None
    if len(raw)>maximum:raise _error('Audio evidence exceeds its supported size.',413)
    return raw
def _strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON field')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
def read_current_transcript(project_name,owner=None):
    owner=_owner(owner)
    with mutex():
        directory=_directory(project_name,owner);pointer=directory/'transcripts'/'current.json';_plain(pointer)
        if not pointer.exists():return None
        raw=_read(pointer,65536)
        try:
            manifest=_strict_json(raw)
            if not isinstance(manifest,dict) or not isinstance(manifest.get('files'),dict):raise ValueError()
            if manifest['schema']!=SCHEMA or manifest['project']!=project_name:raise ValueError()
            if manifest['owner_hash']!=_key(project_name,owner)[0]:raise _error('Audio transcript belongs to another owner.',403)
            version=manifest['version']
            if not re.fullmatch('[a-f0-9]{64}',version):raise ValueError()
            if set(manifest['files'])!={'audio_transcript.txt','audio_transcript.md','audio_transcript.fountain','audio_transcript.json'}:raise ValueError()
            artifact=directory/'transcripts'/'versions'/version;values={}
            for name,digest in manifest['files'].items():
                data=_read(artifact/name,MAX_TEXT_BYTES)
                if _sha(data)!=digest:raise ValueError()
                values[name]=data.decode('utf8',errors='strict')
            packet=_strict_json(values['audio_transcript.json'])
            if packet['text'].strip()!=values['audio_transcript.txt']:raise ValueError()
            if _sha(_json({'source_audio_sha256':manifest['source_audio_sha256'],'model_size':manifest['model_size'],'files':manifest['files']}))!=version:raise ValueError()
            if not re.fullmatch('[a-f0-9]{64}',manifest['source_audio_sha256']) or manifest['source_audio_suffix'] not in {'.wav','.mp3','.m4a'}:raise ValueError()
            source=directory/'transcripts'/'sources'/(manifest['source_audio_sha256']+manifest['source_audio_suffix'])
            audio=_read(source,MAX_AUDIO_BYTES)
            if _sha(audio)!=manifest['source_audio_sha256'] or len(audio)!=manifest['source_audio_bytes']:raise ValueError()
            return dict(text=values['audio_transcript.txt'],markdown=values['audio_transcript.md'],revision=_sha(raw),source_audio_sha256=manifest['source_audio_sha256'],source_file='transcripts/versions/'+version+'/audio_transcript.txt',version=version,owner_hash=manifest['owner_hash'])
        except HTTPException:raise
        except (KeyError,TypeError,ValueError,UnicodeError):raise _error('Current transcript provenance or hashes do not match; no legacy fallback was used.') from None
def get_transcription_status(project_name,owner=None):
    owner=_owner(owner)
    with mutex():_directory(project_name,owner)
    with _TASK_LOCK:return dict(AUDIO_TRANSCRIBE_TASKS.get(_key(project_name,owner),{'status':'idle'}))
def format_seconds(seconds):
    seconds=int(seconds);hours,rest=divmod(seconds,3600);minutes,seconds=divmod(rest,60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}' if hours else f'{minutes:02d}:{seconds:02d}'
def _load_whisper_model(model_size):
    import whisper
    return whisper.load_model(model_size)
def _outputs(result,project_name,source_name):
    if not isinstance(result,dict) or not isinstance(result.get('text'),str) or not result['text'].strip():raise _error('Whisper returned no nonempty transcript.',502)
    segments=result.get('segments')
    if not isinstance(segments,list) or len(segments)>50000:raise _error('Whisper returned invalid or oversized segment evidence.',502)
    full=result['text'].strip();raw=_json(result)
    if len(raw)>MAX_TEXT_BYTES:raise _error('Transcript output exceeds its retained size bound.',413)
    lines=[f'# Audio Adaptation Transcript: {project_name}',f'**Source Audio:** `{source_name}`','\n## Full Transcript with Timecodes\n']
    fountain=[f'Title: {project_name.upper()} - AUDIO TRANSCRIPT','Credit: Transcribed from project audio',''];heading=-999
    for segment in segments:
        if not isinstance(segment,dict) or not isinstance(segment.get('text'),str):raise _error('Invalid transcript segment.',502)
        start,end=segment.get('start'),segment.get('end')
        if any(type(value) not in (int,float) or not math.isfinite(value) or value<0 for value in (start,end)) or end<start:raise _error('Invalid transcript timecode.',502)
        text=segment['text'].strip();lines.append(f'**[{format_seconds(start)} - {format_seconds(end)}]** {text}\n')
        if start-heading>=180:heading=start;fountain.append(f'\nINT. AUDIO CHAPTER - {format_seconds(start)} - DAY\n')
        fountain.append('NARRATOR\n'+text+'\n')
    if not segments:lines.append(full);fountain.append(full)
    files={'audio_transcript.txt':full.encode('utf8'),'audio_transcript.md':'\n'.join(lines).encode('utf8'),'audio_transcript.fountain':'\n'.join(fountain).encode('utf8'),'audio_transcript.json':raw}
    if any(len(raw)>MAX_TEXT_BYTES for raw in files.values()):raise _error('Derived transcript exceeds its supported size.',413)
    return files
def _message(error):
    if isinstance(error,HTTPException):return error.detail.get('message','Audio workflow failed.') if isinstance(error.detail,dict) else str(error.detail)
    return 'Audio workflow failed ('+type(error).__name__+'); prior evidence was preserved.'
def _prepare_source(project_name,owner):
    with mutex():
        directory=_directory(project_name,owner);read_current_transcript(project_name,owner)
        pointer=directory/'transcripts'/'current.json';expected=_read(pointer,65536) if pointer.exists() else None
        folder=directory/'audio';_plain(folder)
        if not folder.is_dir():raise _error('Audio directory not found.',404)
        candidates=sorted((path for path in folder.iterdir() if path.suffix.lower() in {'.wav','.mp3','.m4a'}),key=lambda path:path.name.casefold())
        if not candidates:raise _error('No audio source was found.',404)
        if len(candidates)!=1:raise _error('Several audio files exist. Select one project audio source before transcribing.')
        source=candidates[0];audio=_read(source,MAX_AUDIO_BYTES)
        if not audio:raise _error('Audio source is empty.',422)
        source_sha=_sha(audio);suffix=source.suffix.lower();retained=directory/'transcripts'/'sources'/(source_sha+suffix);_plain(retained)
        try:_write_once(retained,audio)
        except PDFSourceError as error:raise _error(str(error),error.status) from None
        return directory,expected,source,audio,source_sha,suffix,retained

def run_transcription_sync(project_name,model_size='base',owner=None):
    owner=_owner(owner);key=_key(project_name,owner)
    if model_size not in {'tiny','base','small','medium','large','large-v2','large-v3','turbo'}:raise _error('Select a supported local Whisper model.',422)
    with mutex():_directory(project_name,owner);read_current_transcript(project_name,owner)
    with _TASK_LOCK:
        if key in _ACTIVE:return {'status':'processing','message':'This owner/project transcription is already running.'}
        _ACTIVE.add(key);AUDIO_TRANSCRIBE_TASKS[key]={'status':'processing','transcription_status':'processing','indexing_status':'not_started','progress':5,'step':'Loading the local speech model.'}
    started=time.monotonic()
    try:
        directory,expected,source,audio,source_sha,suffix,retained=_prepare_source(project_name,owner)
        model=_load_whisper_model(model_size)
        with _TASK_LOCK:AUDIO_TRANSCRIBE_TASKS[key].update(progress=35,step='Transcribing the retained source audio.')
        result=model.transcribe(str(retained),language='en',verbose=False);files=_outputs(result,project_name,source.name)
        hashes={name:_sha(raw) for name,raw in files.items()};version=_sha(_json({'source_audio_sha256':source_sha,'model_size':model_size,'files':hashes}))
        manifest=dict(schema=SCHEMA,project=project_name,owner_hash=key[0],version=version,source_audio_sha256=source_sha,source_audio_bytes=len(audio),source_audio_suffix=suffix,model_size=model_size,files=hashes)
        with mutex():
            directory=_directory(project_name,owner);pointer=directory/'transcripts'/'current.json';_plain(pointer)
            if (_read(pointer,65536) if pointer.exists() else None)!=expected:raise _error('Current transcript changed during transcription; prior current version was preserved.')
            for name,raw in files.items():_write_once(directory/'transcripts'/'versions'/version/name,raw)
            if expected is not None:_write_once(directory/'transcripts'/'pointer_versions'/(_sha(expected)+'.json'),expected)
            temporary=pointer.parent/('.audio-current-'+uuid.uuid4().hex+'.tmp');_write_once(temporary,_json(manifest));os.replace(temporary,pointer)
            current=read_current_transcript(project_name,owner)
        with _TASK_LOCK:AUDIO_TRANSCRIBE_TASKS[key].update(status='completed',transcription_status='complete',progress=100,step='Transcription saved. Index qualification is pending.',source_revision=current['revision'],elapsed_seconds=round(time.monotonic()-started,2))
        try:
            from core.project_rag import sync_project_screenplay,assert_project_snapshot_current
            indexed=asyncio.run(sync_project_screenplay(project_name,owner=owner))
            if indexed.get('status')!='success' or indexed.get('receipt',{}).get('complete') is not True:raise _error('Vector indexing has no verified complete receipt.')
            assert_project_snapshot_current(project_name,indexed['receipt'],owner)
            with _TASK_LOCK:AUDIO_TRANSCRIBE_TASKS[key].update(indexing_status='indexed',index_receipt=indexed['receipt'],step='Transcription saved; current project index verified.')
        except Exception as error:
            with _TASK_LOCK:AUDIO_TRANSCRIBE_TASKS[key].update(indexing_status='failed',step='Transcription saved; vector indexing failed.',index_error=_message(error))
    except Exception as error:
        with _TASK_LOCK:AUDIO_TRANSCRIBE_TASKS[key].update(status='error',transcription_status='failed',step='Transcription was not published.',message=_message(error))
    finally:
        with _TASK_LOCK:_ACTIVE.discard(key)
    return get_transcription_status(project_name,owner)
def get_project_transcription(project_name,owner=None):
    owner=_owner(owner)
    with mutex():
        directory=_directory(project_name,owner);current=read_current_transcript(project_name,owner)
        if current:return dict(status='success',has_transcript=True,transcript_markdown=current['markdown'],source={key:current[key] for key in ('revision','source_audio_sha256','source_file','version')},task=get_transcription_status(project_name,owner))
        legacy=directory/'transcripts'/'audio_transcript.md';_plain(legacy)
        if not legacy.exists():return dict(status='not_found',has_transcript=False,task=get_transcription_status(project_name,owner))
        try:content=_read(legacy,MAX_TEXT_BYTES).decode('utf8',errors='strict')
        except UnicodeError:raise _error('Legacy transcript is not valid UTF-8; no characters were discarded.') from None
        return dict(status='success',has_transcript=True,transcript_markdown=content,source={'qualification':'legacy_unversioned_not_index_evidence'},task=get_transcription_status(project_name,owner))
