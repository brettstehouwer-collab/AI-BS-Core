"""Opt-in secondary WGC sender with fixed C-backed outputs.

Imports perform no I/O, capture or dispatch. Only an explicit controller start
decrypts explicitly requested platform credentials and starts its own window encoder.
Platform acceptance remains unverified until checked on the platform itself.
"""
from __future__ import annotations

import base64
from contextlib import ExitStack, contextmanager
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid
from urllib.parse import urlsplit

from backend.core.broadcast_relay import RelayError, _owned_job, _target_guard, validate_key, youtube_server
from native_studio import broadcast_ipc as _ipc

PROFILE=Path('C:/AI-BS/stream_profiles.json')
_IPC_PATHS=_ipc.ipc_paths()
STATUS=_IPC_PATHS['status'];STOP=_IPC_PATHS['stop'];COMMAND=_IPC_PATHS['command']
ARCHIVE=Path('C:/AI-BS/recordings/secondary')
HLS=Path('C:/AI-BS/saved_data/broadcast_hls/secondary')
LOGS=Path('C:/AI-BS/logs')
TARGETS=('youtube','twitch','kick','facebook')


class SecondaryError(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)


def _identity(hwnd,pid,title):
    if (type(hwnd) is not int or not 0<hwnd<2**64 or type(pid) is not int or not 0<pid<2**32
            or type(title) is not str or not 0<len(title)<=1024 or any(ord(c)<32 for c in title)):
        raise SecondaryError('INVALID_WINDOW_IDENTITY')


def _verify_window(hwnd,pid,title):
    _identity(hwnd,pid,title)
    import win32gui,win32process
    if (not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd)
            or win32gui.GetWindowText(hwnd)!=title or win32process.GetWindowThreadProcessId(hwnd)[1]!=pid):
        raise SecondaryError('WINDOW_IDENTITY_UNAVAILABLE')


def twitch_server(server):
    try:
        if type(server) is not str or len(server)>256:raise ValueError()
        parsed=urlsplit(server)
        if (parsed.scheme not in {'rtmp','rtmps'} or parsed.hostname not in {'live.twitch.tv','ingest.global-contribute.live-video.net'}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path.rstrip('/')!='/app' or parsed.port not in (None,443,1935)):
            raise ValueError()
        return 'rtmps://ingest.global-contribute.live-video.net:443/app'
    except (TypeError,ValueError):raise SecondaryError('INVALID_TWITCH_SERVER') from None


def kick_server(server):
    # The dashboard also supplies a bare RTMPS root. Normalize it in memory
    # to Kick's documented TLS443 /app form without rewriting the profile or
    # permitting another host, protocol, port, path or embedded credential.
    match=re.fullmatch(
        r'rtmps://(?P<host>[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.global-contribute\.live-video\.net)(?::443)?(?:/app|/)?',server) if type(server) is str else None
    if match is None:
        raise SecondaryError('INVALID_KICK_SERVER')
    return 'rtmps://'+match.group('host')+':443/app'


def facebook_server(server):
    if type(server) is not str or server!='rtmps://live-api-s.facebook.com:443/rtmp/':
        raise SecondaryError('INVALID_FACEBOOK_SERVER')
    return server


def _target_server(target,server):
    try:return {'youtube':youtube_server,'twitch':twitch_server,'kick':kick_server,'facebook':facebook_server}[target](server)
    except RelayError as exc:raise SecondaryError(exc.code) from None


def _unique_pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate profile property')
        value[key]=item
    return value


def _not_redirected(path):
    if any(item.is_symlink() or item.is_junction() for item in (path,*path.parents)):
        raise SecondaryError('STORAGE_REDIRECTED')


def _read_profile():
    try:
        _not_redirected(PROFILE)
        with PROFILE.open('rb') as source:raw=source.read(131073)
        if len(raw)>131072:raise ValueError()
        result=json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if type(result) is not dict or type(result.get('destinations')) is not dict:raise ValueError()
        return result
    except Exception:raise SecondaryError('PROFILE_UNAVAILABLE') from None


def _unprotect(blob):
    try:
        if type(blob) is not str or not 1<=len(blob)<=32768:raise ValueError()
        import win32crypt
        value=win32crypt.CryptUnprotectData(base64.b64decode(blob,validate=True),None,None,None,1)[1].decode('utf-8')
        validate_key(value)
        return value
    except Exception:raise SecondaryError('CREDENTIAL_UNAVAILABLE') from None


def _target_names(targets):
    if type(targets) not in (tuple,list) or not 1<=len(targets)<=len(TARGETS) or any(type(t) is not str or t not in TARGETS for t in targets) or len(set(targets))!=len(targets):
        raise SecondaryError('INVALID_TARGETS')
    return tuple(targets)


def _load_targets(targets):
    targets=_target_names(targets)
    saved=_read_profile()['destinations'];endpoints=[]
    for target in targets:
        destination=saved.get(target)
        if type(destination) is not dict or destination.get('enabled') is not True:
            raise SecondaryError('TARGET_DISABLED_OR_MISSING')
        if not destination.get('key_dpapi'):raise SecondaryError('CREDENTIAL_UNAVAILABLE')
        server=_target_server(target,destination.get('url'))
        endpoints.append({'name':target,'url':server,'key':_unprotect(destination['key_dpapi']),'enabled':True})
    return endpoints


def _validate_endpoints(endpoints):
    if type(endpoints) is not list or len(endpoints)>len(TARGETS):raise SecondaryError('INVALID_TARGETS')
    names=[]
    for item in endpoints:
        if type(item) is not dict or item.get('name') not in TARGETS or item.get('name') in names:
            raise SecondaryError('INVALID_TARGETS')
        names.append(item['name'])
        try:
            validate_key(item.get('key'))
            expected=_target_server(item['name'],item.get('url'))
        except RelayError as exc:raise SecondaryError(exc.code) from None
        if item.get('url')!=expected or item.get('enabled') is not True:raise SecondaryError('INVALID_TARGETS')


def _encoding_payload(endpoints,title,sources):
    return {'endpoints':endpoints,'game_name':title,'fps':30,'resolution':'1280x720','video_bitrate':'4500k',
            'audio_bitrate':'128k','encoder_choice':'h264_nvenc','encoder_preset':'p4','enable_6_track':False,
            'overlays':[],'sources':sources}


def secondary_payload(hwnd,pid,title,endpoints):
    _identity(hwnd,pid,title);_validate_endpoints(endpoints)
    return _encoding_payload(endpoints,title,[{'type':'window','enabled':True,'hwnd':hwnd,'pid':pid,'title':title,'name':title}])


def follow_payload(endpoints):
    _validate_endpoints(endpoints)
    return _encoding_payload(endpoints,'Native_Broadcast',[{'type':'game','enabled':True,'capture_policy':'verified_game_follow'}])


def _source_intent(mode,source):
    if mode=='auto_game' and source is None:return None
    if mode=='window' and type(source) is dict and set(source)=={'hwnd','pid','title'}:
        _identity(source['hwnd'],source['pid'],source['title']);return dict(source)
    if mode=='screen' and type(source) is dict and set(source)=={'screen_id'}:
        value=source['screen_id']
        if type(value) is str and 0<len(value)<=256 and all(ord(c)>=32 for c in value):return dict(source)
    raise SecondaryError('INVALID_SOURCE_INTENT')


def validate_control_command(data,session_id):
    if (type(data) is not dict or set(data)!={'version','request_id','session_id','action','source_mode','source'}
            or type(data['version']) is not int or data['version']!=2
            or type(data['request_id']) is not str or re.fullmatch('[a-f0-9]{32}',data['request_id']) is None
            or data['session_id']!=session_id or type(data['session_id']) is not str
            or re.fullmatch('[a-f0-9]{32}',data['session_id']) is None or data['action']!='select_source'):
        raise SecondaryError('INVALID_CONTROL_COMMAND')
    source=_source_intent(data['source_mode'],data['source'])
    return {**data,'source':source}


def _read_small_json(path):
    try:
        return _ipc.read_private_json(path,max_bytes=16384)
    except FileNotFoundError:return None
    except Exception:raise SecondaryError('CONTROL_FILE_UNAVAILABLE') from None


def read_control_command(session_id):
    data=_read_small_json(COMMAND)
    return None if data is None else validate_control_command(data,session_id)


def read_stop_request(session_id):
    try:
        data=_read_small_json(STOP)
        if (type(data) is dict and set(data)=={'version','session_id','request_id'}
                and type(data['version']) is int and data['version']==2 and data['session_id']==session_id
                and type(data['request_id']) is str and re.fullmatch('[a-f0-9]{32}',data['request_id'])):
            return data['request_id']
    except SecondaryError:pass
    return None


class FollowRuntime:
    """Intent and fast cached decisions; discovery is owned by one sampler."""
    def __init__(self,mode,source,*,sampler=None):
        _source_intent(mode,source)
        from backend.core.game_selection_sampler import GameSelectionSampler
        from backend.core.game_follow_capture import FollowingWindowCapture
        self._lock=threading.RLock();self.mode='auto_game';self._pending=None;self._manual=None
        self.sampler=GameSelectionSampler() if sampler is None else sampler
        self.capture=FollowingWindowCapture(None,None,self.select,width=1280,height=720,fps=30)
        try:
            if self.sampler.start() is not True:raise SecondaryError('DISCOVERY_UNAVAILABLE')
            self.apply_source(mode,source)
        except Exception:
            self.stop(timeout=.5)
            error=SecondaryError('FOLLOW_RUNTIME_START_FAILED');error.owner=self
            raise error from None

    def apply_source(self,mode,source):
        from backend.core.game_capture_selection import ManualSource
        source=_source_intent(mode,source)
        with self._lock:
            self.mode=mode;self._pending=None;self._manual=None
            if mode=='window':
                window=self.sampler.resolve_window(**source)
                if window is None:self._pending=source
                else:self._manual=ManualSource(kind='window',window=window)
            elif mode=='screen':self._manual=ManualSource(kind='screen',screen_id=source['screen_id'])
            self.capture.invalidate(manual=mode!='auto_game')
            if self.sampler.set_intent(manual=self._manual) is not True:raise SecondaryError('DISCOVERY_UNAVAILABLE')
            if mode=='screen':return 'held','MANUAL_SCREEN_UNSUPPORTED'
            if self._pending is not None:return 'held','WINDOW_EVIDENCE_PENDING'
            return 'applied',None

    def select(self,*,previous=None):
        from backend.core.game_capture_selection import ManualSource,SelectionDecision
        with self._lock:
            if self.mode=='screen':return SelectionDecision(None,'MANUAL_SCREEN',True,True,manual_source=self._manual)
            if self._pending is not None:
                window=self.sampler.resolve_window(**self._pending)
                if window is None:return SelectionDecision(None,'MANUAL_SOURCE_UNAVAILABLE',True,True)
                self._manual=ManualSource(kind='window',window=window);self._pending=None
                self.sampler.set_intent(manual=self._manual)
            return self.sampler.latest(previous=previous)

    def stop(self,timeout=.5):
        try:capture_stopped=self.capture.stop(timeout=timeout) is True
        except Exception:capture_stopped=False
        try:sampler_stopped=self.sampler.stop(timeout=timeout) is True
        except Exception:sampler_stopped=False
        return capture_stopped and sampler_stopped


def _new_follow(mode,source):return FollowRuntime(mode,source)


def _process_start(pid):
    try:
        import psutil
        value=psutil.Process(pid).create_time()
        return value if type(value) in (int,float) and math.isfinite(value) and value>0 else None
    except Exception:return None


def _prepare_private_ipc():
    try:paths=_ipc.ensure_private_ipc()
    except ValueError as exc:
        code=str(exc)
        known={'IPC_OWNER_MISMATCH','IPC_ACL_UNSAFE','IPC_ACL_NOT_PROTECTED','IPC_STORAGE_REDIRECTED',
               'IPC_PATH_UNEXPECTED','IPC_DIRECTORY_UNAVAILABLE','IPC_LOCATION_UNAVAILABLE'}
        raise SecondaryError(code if code in known else 'IPC_PREPARATION_UNAVAILABLE') from None
    if paths!={'status':STATUS,'command':COMMAND,'stop':STOP}:raise SecondaryError('IPC_LOCATION_CHANGED')


def _prepare_paths(title=None):
    _prepare_private_ipc()
    paths=[ARCHIVE,HLS,LOGS]
    if title is not None:
        slug=''.join(c for c in title if c.isalnum() or c in ' _-').strip(' .') or 'General'
        paths.append(ARCHIVE/slug)
    for path in paths:
        _not_redirected(path);path.mkdir(parents=True,exist_ok=True);_not_redirected(path)
    _not_redirected(STATUS);_not_redirected(STOP);_not_redirected(LOGS/'secondary_ffmpeg.log')


def _new_engine():
    from backend.aibs_broadcast_daemon import BroadcastDaemon
    return BroadcastDaemon(secondary_outputs=True)


@contextmanager
def _secondary_guard(targets):
    import win32api,win32event
    handle=win32event.CreateMutex(None,False,r'Local\AI_BS_Secondary_Broadcast206')
    acquired=False
    try:
        acquired=win32event.WaitForSingleObject(handle,0) in (0,0x80)
        if not acquired:raise SecondaryError('SECONDARY_ALREADY_RUNNING')
        with ExitStack() as stack:
            if 'youtube' in targets:stack.enter_context(_target_guard())
            yield
    finally:
        if acquired:win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


def safe_status(engine,state,error):
    result={'status':state,'error_code':error,'process_running':False,'encoder_pid':None,
            'ingest_verified':False,'archive_verified':False,'hls_verified':False,'audio_mode':'generated_silence'}
    if engine is None:return result
    process=engine.process
    if process is not None:
        result['process_running']=process.poll() is None
        if type(process.pid) is int:result['encoder_pid']=process.pid
    telemetry=engine.telemetry
    for name in ('frames_encoded','out_time_us'):
        value=telemetry.get(name)
        if type(value) is int and value>=0:result[name]=value
    return result


class SecondaryBroadcast:
    def __init__(self,*,publish_status=False):
        if type(publish_status) is not bool:raise SecondaryError('INVALID_STATUS_MODE')
        self._lock=threading.RLock();self._stop=threading.Event();self._ready=threading.Event()
        self._thread=None;self._engine=None;self._state='stopped';self._error=None;self._generation=0
        self._publish_status=publish_status;self._lease_acquired=False
        self._follow=None;self._session_id=uuid.uuid4().hex;self._controller_create_time=None
        self._encoder_create_time=None;self._source_mode='window'
        self._last_command_id=None;self._command_status=None;self._command_error=None;self._seen_commands=[]

    def status(self):
        with self._lock:
            result=safe_status(self._engine,self._state,self._error)
            result.update(protocol_version=2,session_id=self._session_id,controller_pid=os.getpid(),
                          controller_create_time=self._controller_create_time,encoder_create_time=self._encoder_create_time,
                          source_mode=self._source_mode,last_command_id=self._last_command_id,
                          command_status=self._command_status,command_error_code=self._command_error,
                          capture_state='holding',game_frame_verified=False,holding_reason='SOURCE_NOT_READY')
            if self._follow is not None:
                metadata=self._follow.capture.metadata()
                state=metadata.get('capture_state')
                if state in {'holding','capturing','closed'}:result['capture_state']=state
                result['game_frame_verified']=metadata.get('game_frame_verified') is True and state=='capturing'
                reason=metadata.get('holding_reason')
                if type(reason) is str and re.fullmatch('[A-Z_]{1,64}',reason):result['holding_reason']=reason
            return result

    def start(self,hwnd=None,pid=None,title=None,*,targets=('youtube','twitch'),timeout=5,source_mode='window',screen_id=None):
        source={'hwnd':hwnd,'pid':pid,'title':title} if source_mode=='window' else {'screen_id':screen_id} if source_mode=='screen' else None
        _source_intent(source_mode,source);targets=_target_names(targets)
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=8:
            raise SecondaryError('INVALID_TIMEOUT')
        with self._lock:
            if self._thread is not None and self._thread.is_alive():raise SecondaryError('SECONDARY_ALREADY_RUNNING')
            self._generation+=1;generation=self._generation
            self._stop.clear();self._ready.clear();self._engine=None;self._state='starting';self._error=None;self._lease_acquired=False
            self._source_mode=source_mode;self._session_id=uuid.uuid4().hex
            self._follow=None;self._last_command_id=None;self._command_status=None;self._command_error=None;self._seen_commands=[]
            self._thread=threading.Thread(target=self._run,args=(hwnd,pid,title,targets,generation,source_mode,screen_id),name='AI-BS-Secondary207',daemon=True)
            self._thread.start()
        self._ready.wait(timeout)
        return self.status()

    def _handle_control(self):
        try:command=read_control_command(self._session_id)
        except SecondaryError as exc:
            with self._lock:self._command_status='rejected';self._command_error=exc.code
            return
        if command is None or command['request_id'] in self._seen_commands:return
        self._seen_commands.append(command['request_id']);self._seen_commands=self._seen_commands[-256:]
        with self._lock:self._last_command_id=command['request_id']
        try:
            state,error=self._follow.apply_source(command['source_mode'],command['source'])
            with self._lock:
                self._source_mode=command['source_mode'];self._command_status=state;self._command_error=error
        except Exception:
            with self._lock:self._command_status='rejected';self._command_error='SOURCE_INTENT_UNAVAILABLE'

    def _run(self,hwnd,pid,title,targets,generation,source_mode='window',screen_id=None):
        engine=None;follow=None;ownership=ExitStack();job=ExitStack()
        try:
            ownership.enter_context(_secondary_guard(targets))
            self._lease_acquired=True
            self._controller_create_time=_process_start(os.getpid())
            if self._controller_create_time is None:raise SecondaryError('CONTROLLER_IDENTITY_UNAVAILABLE')
            endpoints=_load_targets(targets)
            payload=follow_payload(endpoints)
            _prepare_paths(payload['game_name'])
            if self._publish_status:STOP.unlink(missing_ok=True)
            if self._stop.is_set():return
            source={'hwnd':hwnd,'pid':pid,'title':title} if source_mode=='window' else {'screen_id':screen_id} if source_mode=='screen' else None
            follow=_new_follow(source_mode,source)
            engine=_new_engine()
            engine._capture_provider_override=follow.capture
            with self._lock:
                if generation!=self._generation:return
                self._engine=engine;self._follow=follow
            if engine.start_stream(**payload) is not True:raise SecondaryError('CAPTURE_OR_ENCODER_START_FAILED')
            if engine.process is None or engine.process.poll() is not None:raise SecondaryError('ENCODER_EXITED')
            job.enter_context(_owned_job(engine.process))
            self._encoder_create_time=_process_start(engine.process.pid)
            if self._encoder_create_time is None:raise SecondaryError('ENCODER_IDENTITY_UNAVAILABLE')
            with self._lock:
                if generation!=self._generation:return
                self._state='running_unverified';self._ready.set()
            if self._publish_status:_write_status(self.status())
            # A new heartbeat can repeat frozen counters. Require actual video
            # and media-time advancement and use a clock unaffected by wall
            # clock corrections while a stream is running.
            frame_advanced=media_advanced=time.monotonic()
            last_frame=last_media=0
            while not self._stop.wait(.25):
                if engine.process is None or engine.process.poll() is not None:raise SecondaryError('ENCODER_EXITED')
                if not engine.is_streaming:raise SecondaryError('CAPTURE_OR_ENCODER_STOPPED')
                now=time.monotonic()
                frames=engine.telemetry.get('frames_encoded');media=engine.telemetry.get('out_time_us')
                if type(frames) is int and frames>last_frame:last_frame=frames;frame_advanced=now
                if type(media) is int and media>last_media:last_media=media;media_advanced=now
                if now-frame_advanced>15 or now-media_advanced>15:raise SecondaryError('ENCODER_PROGRESS_STALLED')
                if self._publish_status:
                    request_id=read_stop_request(self._session_id)
                    if request_id is not None:
                        with self._lock:self._last_command_id=request_id;self._command_status='applied'
                        break
                    self._handle_control()
                    _write_status(self.status())
        except (SecondaryError,RelayError) as exc:
            if follow is None:follow=getattr(exc,'owner',None)
            with self._lock:
                if generation==self._generation:self._state='failed';self._error=exc.code
        except Exception:
            with self._lock:
                if generation==self._generation:self._state='failed';self._error='SECONDARY_UNAVAILABLE'
        finally:
            # Stop only the engine created in this controller. Never query or
            # terminate a PID from the primary service or a status file.
            stopped=True
            if engine is not None:
                try:stopped=engine.stop_stream().get('status')=='stopped'
                except Exception:stopped=False
            if follow is not None:
                try:stopped=follow.stop(timeout=.5) is True and stopped
                except Exception:stopped=False
            try:job.close()
            except Exception:stopped=False
            if not stopped:
                with self._lock:
                    if generation==self._generation:
                        self._state='failed';self._error='CLEANUP_UNCONFIRMED';self._ready.set()
                # A caller's stop remains bounded. If Windows cannot confirm
                # owned cleanup, retain the target lease rather than authorize
                # a competing sender. The job has already requested child exit.
                while not stopped:
                    time.sleep(.25)
                    try:
                        engine_stopped=engine is None or engine.stop_stream().get('status')=='stopped'
                        follow_stopped=follow is None or follow.stop(timeout=.5) is True
                        stopped=engine_stopped and follow_stopped
                    except Exception:pass
            with self._lock:
                if generation==self._generation:
                    if not stopped:self._state='failed';self._error='CLEANUP_UNCONFIRMED'
                    elif self._error is None:self._state='stopped'
                    self._ready.set()
            if self._publish_status and self._lease_acquired:
                try:_write_status(self.status())
                except Exception:pass
            ownership.close()

    def stop(self,timeout=5):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=8:
            raise SecondaryError('INVALID_TIMEOUT')
        self._stop.set()
        thread=self._thread
        if thread is not None and thread is not threading.current_thread():thread.join(timeout)
        return thread is None or not thread.is_alive()


def _write_status(status):
    try:
        _ipc.write_private_json(STATUS,status,max_bytes=16384)
    except Exception:raise SecondaryError('STATUS_WRITE_UNAVAILABLE') from None


def _failure_status(status):
    code=status.get('error_code')
    if type(code) is not str or re.fullmatch('[A-Z_]{1,64}',code) is None:code='SECONDARY_UNAVAILABLE'
    return {'status':'failed','error_code':code}


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Explicit secondary window broadcast; credentials are loaded through DPAPI only.')
    parser.add_argument('--hwnd',type=int);parser.add_argument('--pid',type=int)
    parser.add_argument('--title');parser.add_argument('--targets',nargs='+',choices=TARGETS,required=True)
    parser.add_argument('--source-mode',choices=('auto_game','window','screen'),default='window')
    parser.add_argument('--screen-id')
    args=parser.parse_args();controller=SecondaryBroadcast(publish_status=True)
    try:
        status=controller.start(args.hwnd,args.pid,args.title,targets=args.targets,
                                source_mode=args.source_mode,screen_id=args.screen_id)
        if not controller._lease_acquired:
            print(json.dumps(_failure_status(status)));return 1
        while True:
            if status['status'] in {'failed','stopped'}:break
            time.sleep(.5);status=controller.status()
        if status['status']=='failed':print(json.dumps(_failure_status(status)))
    except KeyboardInterrupt:pass
    except SecondaryError as exc:
        print(json.dumps(_failure_status({'error_code':exc.code})));return 1
    except Exception:
        print(json.dumps({'status':'failed','error_code':'CONTROLLER_UNAVAILABLE'}));return 1
    finally:
        controller.stop()
    return 0 if controller.status()['status']=='stopped' else 1


if __name__=='__main__':raise SystemExit(main())
