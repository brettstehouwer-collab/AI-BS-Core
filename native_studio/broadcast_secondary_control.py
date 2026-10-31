"""Pure native client for the one explicit broadcast coordinator.

Importing this module starts nothing. IPC contains source intent and target names,
never publish credentials. The installed native build does not import backend code.
"""
from __future__ import annotations
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid
import psutil

from native_studio.broadcast_service import PYTHON, service_environment, _declared_base_python
from native_studio.broadcast_ipc import ipc_paths, read_private_json, write_private_json

ROOT = Path('C:/AI-BS')
STATUS = ROOT/'saved_data/broadcast_secondary_status.json'
STOP = ROOT/'saved_data/broadcast_secondary.stop'
COMMAND = ROOT/'saved_data/broadcast_secondary_command.json'
FFMPEG = Path('C:/Users/footb/AppData/Local/Microsoft/WinGet/Links/ffmpeg.EXE')
LOG = ROOT/'logs/native_secondary_controller207.log'
QUALITY = '1280×720 · 30 FPS · H.264 · 4500 kb/s'
TARGETS = {'youtube', 'twitch', 'facebook', 'kick'}


def validate_source(mode, source):
    if mode == 'auto_game' and source is None:
        return None
    if mode == 'window' and type(source) is dict and set(source) == {'hwnd','pid','title'}:
        if (type(source['hwnd']) is int and 0 < source['hwnd'] < 2**64
                and type(source['pid']) is int and 0 < source['pid'] < 2**32
                and type(source['title']) is str and 0 < len(source['title']) <= 1024
                and not any(ord(c) < 32 for c in source['title'])):
            return dict(source)
    if mode == 'screen' and type(source) is dict and set(source) == {'screen_id'}:
        screen = source['screen_id']
        if type(screen) is str and 0 < len(screen) <= 256 and not any(ord(c) < 32 for c in screen):
            return dict(source)
    raise ValueError('Choose Automatic game, an exact selected window, or an explicit screen.')


def coordinator_command(payload):
    if type(payload) is not dict or set(payload) != {'source_mode','source','targets'}:
        raise ValueError('Invalid broadcast request. Save destination settings separately.')
    mode = payload['source_mode']; source = validate_source(mode, payload['source'])
    targets = payload['targets']
    if (type(targets) not in (list,tuple) or not 1 <= len(targets) <= 4
            or any(type(name) is not str or name not in TARGETS for name in targets)
            or len(set(targets)) != len(targets)):
        raise ValueError('Enable a supported broadcast destination in Setup & Keys.')
    command = [str(PYTHON), '-B', '-m', 'backend.core.broadcast_secondary', '--source-mode', mode]
    if mode == 'window':
        command += ['--hwnd', str(source['hwnd']), '--pid', str(source['pid']), '--title', source['title']]
    elif mode == 'screen':
        command += ['--screen-id', source['screen_id']]
    return command + ['--targets', *targets]


def _not_redirected(path):
    if any(item.is_symlink() or item.is_junction() for item in (path,*path.parents)):
        raise ValueError('Broadcast storage redirected.')


def _unique_pairs(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate broadcast property.')
        result[key] = value
    return result


def _read_status():
    modern=ipc_paths()['status']
    if modern.exists():
        value=read_private_json(modern)
        if type(value.get('protocol_version')) is not int or value['protocol_version']!=2:
            raise ValueError('IPC_PROTOCOL_INVALID')
        age=time.time()-modern.stat().st_mtime
        return value,-1<=age<=3
    return _read_legacy_status()


def _read_legacy_status():
    # Old206 state is observable only after independent process/child identity
    # checks. A shared file cannot promote itself to the modern command protocol.
    _not_redirected(STATUS)
    if not STATUS.exists(): return {}, False
    with STATUS.open('rb') as stream: raw = stream.read(16385)
    if len(raw) > 16384: raise ValueError('Broadcast status oversized.')
    value = json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    if type(value) is not dict: raise ValueError('Invalid broadcast status.')
    if 'protocol_version' in value: raise ValueError('Legacy status cannot authorize modern commands.')
    age = time.time() - STATUS.stat().st_mtime
    return value, -1 <= age <= 3


def _normal(path):
    return os.path.normcase(str(Path(path).resolve()))


def _valid_controller_args(command):
    args = list(command[1:])
    if args and args[0] == '-B': args.pop(0)
    if args[:2] != ['-m','backend.core.broadcast_secondary']: return False
    args = args[2:]; fields = {}; index = 0
    try:
        while index < len(args):
            name = args[index]
            if name in fields or name not in {'--source-mode','--hwnd','--pid','--title','--screen-id','--targets'}: return False
            index += 1
            if name == '--targets':
                values = []
                while index < len(args) and not args[index].startswith('--'):
                    values.append(args[index]); index += 1
                fields[name] = values
            else:
                fields[name] = args[index]; index += 1
        mode = fields.get('--source-mode','window')
        allowed = {'--source-mode','--targets'}
        if mode == 'window':
            source = {'hwnd':int(fields['--hwnd']), 'pid':int(fields['--pid']), 'title':fields['--title']}
            allowed |= {'--hwnd','--pid','--title'}
        elif mode == 'screen': source = {'screen_id':fields['--screen-id']}; allowed.add('--screen-id')
        else: source = None
        if set(fields) - allowed: return False
        coordinator_command({'source_mode':mode,'source':source,'targets':fields['--targets']})
        return True
    except (ValueError,TypeError,KeyError,IndexError): return False


def _controller_owned(process):
    if (not process.is_running() or _normal(process.cwd()) != _normal(ROOT)
            or not _valid_controller_args(process.cmdline())): return False
    executable = _normal(process.exe())
    fixed = _normal(PYTHON)
    if executable == fixed: return True
    base = _declared_base_python()
    if base is None or executable != _normal(base): return False
    parent = process.parent()
    return (parent is not None and parent.is_running() and _normal(parent.exe()) == fixed
            and _valid_controller_args(parent.cmdline()) and parent.cmdline()[1:] == process.cmdline()[1:])


def _verified_owner(raw):
    """Validate the fixed coordinator and its child, never read FFmpeg argv."""
    try:
        encoder_pid = raw.get('encoder_pid')
        controller_pid = raw.get('controller_pid')
        modern = raw.get('protocol_version') == 2
        encoder = None
        if type(encoder_pid) is int and encoder_pid > 0:
            encoder = psutil.Process(encoder_pid)
            if not encoder.is_running() or _normal(encoder.exe()) != _normal(FFMPEG): return None
            if modern:
                expected = raw.get('encoder_create_time')
                if type(expected) not in (int,float) or not math.isfinite(expected) or abs(encoder.create_time()-expected) > .001: return None
            if not modern: controller_pid = encoder.ppid()
        if type(controller_pid) is not int or controller_pid <= 0: return None
        controller = psutil.Process(controller_pid)
        if not _controller_owned(controller): return None
        if modern:
            expected = raw.get('controller_create_time')
            if type(expected) not in (int,float) or not math.isfinite(expected) or abs(controller.create_time()-expected) > .001: return None
        if encoder is not None and encoder.ppid() != controller.pid: return None
        return {'controller_pid':controller.pid,'encoder_pid':encoder_pid if encoder is not None else None}
    except (OSError,ValueError,TypeError,psutil.Error): return None


def _empty(status='stopped'):
    return {'status':status,'active':False,'can_start':status in {'stopped','failed'},'can_stop':False,'can_select':False,
            'capture_state':'unavailable','game_frame_verified':False,'audio_mode':'generated_silence',
            'ingest_verified':False,'archive_verified':False,'quality':QUALITY}


def read_broadcast_status():
    try:
        raw,fresh = _read_status()
        if not raw: return _empty()
        owner = _verified_owner(raw)
        if owner is None and type(raw.get('protocol_version')) is int and raw['protocol_version']==2:
            try:
                legacy,legacy_fresh=_read_legacy_status()
                legacy_owner=_verified_owner(legacy)
                if legacy_owner is not None: raw,fresh,owner=legacy,legacy_fresh,legacy_owner
            except (OSError,ValueError,TypeError): pass
        if owner is None:
            if raw.get('status') in {'stopped','failed'} and raw.get('process_running') is False: return _empty(raw['status'])
            return _empty('owner_unverified')
        modern = type(raw.get('protocol_version')) is int and raw['protocol_version'] == 2 and re.fullmatch('[0-9a-f]{32}',str(raw.get('session_id','')))
        result = {**_empty(), **owner, 'active':True,'can_start':False,'can_stop':True,
                  'status':'status_stale' if not fresh else 'running_unverified' if modern else 'legacy_upgrade_required',
                  'can_select':bool(modern and fresh)}
        if modern:
            result.update(protocol_version=2,session_id=raw['session_id'])
            result['source_mode'] = raw.get('source_mode') if raw.get('source_mode') in {'auto_game','window','screen'} else 'unknown'
            state = raw.get('capture_state')
            result['capture_state'] = state if fresh and state in {'holding','capturing'} else 'unavailable'
            result['game_frame_verified'] = bool(fresh and state == 'capturing' and raw.get('game_frame_verified') is True)
            for name in ('holding_reason','last_command_id','command_status','command_error_code'):
                value = raw.get(name)
                if type(value) is str and re.fullmatch('[A-Za-z0-9_]{1,64}',value): result[name] = value
        for name in ('frames_encoded','out_time_us'):
            value = raw.get(name)
            if type(value) is int and 0 <= value < 2**63: result[name] = value
        return result
    except (OSError,ValueError,TypeError): return _empty('status_unavailable')


def _atomic_json(target, value):
    if not (target==STOP and value.get('version')==1):
        paths=ipc_paths()
        if target not in (paths.get('command'),paths.get('stop')):
            raise ValueError('IPC_PATH_UNEXPECTED')
        write_private_json(target,value)
        return
    # Compatibility stop for an independently verified old206 controller only.
    _not_redirected(target); _not_redirected(target.parent)
    data = json.dumps(value,allow_nan=False,separators=(',',':')).encode('utf-8')
    if len(data) > 16384: raise ValueError('Broadcast command oversized.')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.native-broadcast-',suffix='.tmp',delete=False) as stream:
            temporary = Path(stream.name); stream.write(data); stream.flush(); os.fsync(stream.fileno())
        _not_redirected(target); os.replace(temporary,target)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def select_broadcast_source(source_mode, source):
    source = validate_source(source_mode,source)
    state = read_broadcast_status()
    if not state.get('can_select'): return state
    request_id = uuid.uuid4().hex
    _atomic_json(ipc_paths()['command'],{'version':2,'request_id':request_id,'session_id':state['session_id'],
                          'action':'select_source','source_mode':source_mode,'source':source})
    return {'status':'pending','request_id':request_id,'active':True}


def stop_broadcast():
    state = read_broadcast_status()
    if not state.get('can_stop'): return state
    command = {'version':2 if state.get('protocol_version') == 2 else 1,'request_id':uuid.uuid4().hex}
    if command['version'] == 2: command['session_id'] = state['session_id']
    _atomic_json(ipc_paths()['stop'] if command['version']==2 else STOP,command)
    return {'status':'stopping','active':True}


def _existing_controller():
    fixed = _normal(PYTHON); base = _declared_base_python()
    allowed = {fixed} | ({_normal(base)} if base else set())
    for process in psutil.process_iter(['pid','exe']):
        try:
            if process.info.get('exe') and _normal(process.info['exe']) in allowed and _controller_owned(process): return True
        except (OSError,ValueError,psutil.Error): continue
    return False


@contextmanager
def _start_lock():
    import win32api,win32event
    handle = win32event.CreateMutex(None,False,r'Local\AI_BS_NativeSecondary207_Start')
    acquired = False
    try:
        acquired = win32event.WaitForSingleObject(handle,2000) in (0,0x80)
        if not acquired: raise OSError('Another native client is starting the coordinator.')
        yield
    finally:
        if acquired: win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


def _spawn(command):
    _not_redirected(LOG); LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('ab') as log:
        return subprocess.Popen(command,cwd=str(ROOT),env=service_environment(),stdin=subprocess.DEVNULL,
                                stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)


def start_broadcast(payload):
    command = coordinator_command(payload)
    state = read_broadcast_status()
    if state.get('active') or not state.get('can_start'): return state
    try:
        with _start_lock():
            state = read_broadcast_status()
            if state.get('active') or not state.get('can_start'): return state
            if _existing_controller(): return {**_empty('controller_present'),'active':True,'can_start':False}
            if not PYTHON.is_file() or not (ROOT/'backend/core/broadcast_secondary.py').is_file(): return _empty('runtime_unavailable')
            _spawn(command)
            return {'status':'starting','active':True,'can_start':False,'can_stop':False,'can_select':False}
    except (OSError,ValueError,psutil.Error): return _empty('start_unavailable')
