"""An owned, copy-only YouTube relay from the existing local fMP4 archive.

Importing this module starts nothing and reads no credentials. The caller supplies
the already-authorized key in memory. Neither primary encoder nor archive is
modified. Status proves local packet progress only, never platform acceptance.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit

RECORDING_ROOT=Path('E:/Recordings/Fortnite')
FFMPEG=Path(r'C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\ffmpeg.EXE')
FFPROBE=FFMPEG.with_name('ffprobe.EXE')
_SOURCE_NAME=re.compile(r'stream_[0-9]{10,16}\.mp4\Z')
_KEY=re.compile(r'[A-Za-z0-9_-]{8,256}\Z')


class RelayError(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)


def youtube_server(server: str) -> str:
    try:
        if type(server) is not str or len(server)>256:raise ValueError()
        parsed=urlsplit(server)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/')!='/live2':raise ValueError()
        valid=(parsed.scheme=='rtmps' and parsed.hostname=='a.rtmps.youtube.com' and parsed.port in (None,443))
        upgrade=(parsed.scheme=='rtmp' and parsed.hostname=='a.rtmp.youtube.com' and parsed.port in (None,1935))
        if not valid and not upgrade:raise ValueError()
        return 'rtmps://a.rtmps.youtube.com:443/live2'
    except (TypeError,ValueError):raise RelayError('INVALID_YOUTUBE_SERVER') from None


def validate_key(key: str) -> None:
    if type(key) is not str or _KEY.fullmatch(key) is None:raise RelayError('INVALID_STREAM_KEY')


def validate_source(value) -> Path:
    try:
        path=Path(value)
        if not path.is_absolute() or path.parent!=RECORDING_ROOT or _SOURCE_NAME.fullmatch(path.name) is None:raise ValueError()
        if any(item.is_symlink() or item.is_junction() for item in (path,*path.parents)):raise ValueError()
        metadata=path.lstat()
        if metadata.st_file_attributes & 0x400 or not path.is_file() or metadata.st_size<16:raise ValueError()
        with path.open('rb') as source:header=source.read(12)
        if header[4:8]!=b'ftyp':raise ValueError()
        return path.resolve(strict=True)
    except (OSError,TypeError,ValueError):raise RelayError('INVALID_ARCHIVE') from None


def _environment() -> dict:
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA'}
    env={name:value for name,value in os.environ.items() if name.upper() in allowed}
    env.update(DRY_RUN='true',HOLD_DISPATCH='true',LIVE_TRADING_ENABLED='false',AIBS_PAYMENT_MODE='disabled',
               AI_BS_BACKEND_MANAGE_DAEMONS='false',AI_BS_BACKEND_BACKGROUND_ENABLED='false',RECDEBUT_SENDING_ENABLED='false')
    return env


def probe_source(source: Path) -> dict:
    command=[str(FFPROBE),'-v','error','-protocol_whitelist','file','-show_entries',
             'stream=codec_type,codec_name,extradata_size:format=duration','-of','json',str(source)]
    try:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=3,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=_environment())
        if result.returncode!=0 or len(result.stdout)>65536:raise ValueError()
        data=json.loads(result.stdout);streams=data['streams']
        video=next(item for item in streams if item.get('codec_type')=='video')
        audio=next(item for item in streams if item.get('codec_type')=='audio')
        duration=float(data['format']['duration'])
        if not math.isfinite(duration) or not 0<duration<=604800:raise ValueError()
        if video.get('codec_name')!='h264' or audio.get('codec_name')!='aac' or video.get('extradata_size',0)<=0:raise ValueError()
        return {'duration':duration,'video_codec':'h264','audio_codec':'aac'}
    except Exception:raise RelayError('ARCHIVE_NOT_COPY_COMPATIBLE') from None


def _relay_command(source: Path,server: str,key: str,start_seconds: float) -> list[str]:
    validate_key(key);server=youtube_server(server)
    if not math.isfinite(start_seconds) or not 0<=start_seconds<=604800:raise RelayError('INVALID_LIVE_EDGE')
    return [str(FFMPEG),'-hide_banner','-loglevel','error','-nostdin','-nostats',
            '-progress','pipe:1','-stats_period','0.5','-rw_timeout','15000000','-follow','1',
            '-analyzeduration','100000','-probesize','65536','-i',str(source),
            '-ss',f'{start_seconds:.3f}','-map','0:v:0','-map','0:a:0','-c','copy',
            '-avoid_negative_ts','make_zero','-rw_timeout','8000000','-tls_verify','1','-flush_packets','1',
            '-flvflags','no_duration_filesize','-f','flv',server+'/'+key]


def _spawn_relay(command):
    return subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            bufsize=0,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=_environment(),close_fds=True)


@contextmanager
def _target_guard():
    """Hold one YouTube target across processes; acquire/release on worker thread."""
    import win32api,win32event
    handle=win32event.CreateMutex(None,False,r'Local\AI_BS_YouTube_Relay206')
    acquired=False
    try:
        acquired=win32event.WaitForSingleObject(handle,0) in (0,0x80)
        if not acquired:raise RelayError('TARGET_ALREADY_RUNNING')
        yield
    finally:
        if acquired:win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


@contextmanager
def _owned_job(process):
    """The relay dies if its controller crashes; this job never owns the primary."""
    import win32api,win32job
    job=win32job.CreateJobObject(None,'')
    try:
        info=win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
        info['BasicLimitInformation']['LimitFlags']|=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,info)
        win32job.AssignProcessToJobObject(job,int(process._handle))
        yield
    finally:win32api.CloseHandle(job)


class BroadcastRelay:
    def __init__(self):
        self._lock=threading.RLock();self._stop=threading.Event();self._ready=threading.Event()
        self._thread=None;self._reader=None;self._process=None;self._state='stopped';self._error=None
        self._frames=0;self._out_time=0;self._last_advance=0;self._source=None;self._started_at=None
        self._session=0

    def _fail(self,code,*,session=None,process=None):
        with self._lock:
            if session is not None and session!=self._session:return
            if process is not None and process is not self._process:return
            self._error=code;self._state='error';self._stop.set()
        self._ready.set()

    def _reject(self,code):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return {'status':'rejected','error_code':code,'current':self.status(),'primary_modified':False}
        self._fail(code);return self.status()

    def start(self,source,server,key,*,target='youtube',timeout=5.0) -> dict:
        try:
            timeout=float(timeout)
            if not math.isfinite(timeout) or not 0<timeout<=10 or target!='youtube':raise RelayError('INVALID_RELAY_REQUEST')
            server=youtube_server(server);validate_key(key)
            with self._lock:
                if self._thread is not None and self._thread.is_alive():return self.status()
                path=validate_source(source);probe=probe_source(path)
                if probe.get('video_codec')!='h264' or probe.get('audio_codec')!='aac':raise RelayError('ARCHIVE_NOT_COPY_COMPATIBLE')
                duration=float(probe['duration'])
                if not math.isfinite(duration) or not 0<duration<=604800:raise RelayError('INVALID_LIVE_EDGE')
                self._source=path;self._error=None;self._state='starting';self._frames=0;self._out_time=0
                self._session+=1
                self._stop.clear();self._ready.clear();self._process=None;self._started_at=time.monotonic()
                identity=self._file_identity(path)
                command=_relay_command(path,server,key,max(0,duration-4))
                self._thread=threading.Thread(target=self._run,args=(command,identity,self._session),name='AI-BS-YouTube-Relay',daemon=True)
                self._thread.start()
            self._ready.wait(timeout)
            return self.status()
        except RelayError as exc:return self._reject(exc.code)
        except Exception:return self._reject('RELAY_START_FAILED')

    @staticmethod
    def _file_identity(path):
        metadata=path.stat()
        return (metadata.st_dev,metadata.st_ino,getattr(metadata,'st_birthtime_ns',None))

    def _read_progress(self,process,session):
        try:
            while True:
                with self._lock:
                    if (session!=self._session or process is not self._process
                            or self._stop.is_set() or self._error is not None):break
                raw=process.stdout.readline(4097)
                if not raw:break
                if len(raw)>4096:continue
                line=raw.decode('ascii',errors='replace').strip() if isinstance(raw,bytes) else raw.strip()
                match=re.fullmatch(r'(frame|out_time_us)=(\d{1,16})',line)
                if match:
                    value=int(match.group(2))
                    with self._lock:
                        if (session!=self._session or process is not self._process
                                or self._stop.is_set() or self._error is not None):break
                        old=self._frames if match.group(1)=='frame' else self._out_time
                        if match.group(1)=='frame':self._frames=max(self._frames,value)
                        else:self._out_time=max(self._out_time,value)
                        if value>old:self._last_advance=time.monotonic()
                        if self._frames>0:
                            self._state='relaying_unverified';self._ready.set()
                # Discard every other line, including all key-bearing FFmpeg errors.
        except Exception:
            if not self._stop.is_set():self._fail('RELAY_PROGRESS_FAILED',session=session,process=process)

    def _run(self,command,identity,session):
        process=None
        try:
            with _target_guard():
                try:
                    process=_spawn_relay(command)
                    with self._lock:self._process=process;self._last_advance=time.monotonic()
                    with _owned_job(process):
                        self._reader=threading.Thread(target=self._read_progress,args=(process,session),name='AI-BS-Relay-Progress',daemon=True)
                        self._reader.start();last_size=self._source.stat().st_size;last_growth=time.monotonic()
                        while not self._stop.wait(.1):
                            if process.poll() is not None:raise RelayError('RELAY_EXITED')
                            try:
                                if self._file_identity(self._source)!=identity:raise RelayError('SOURCE_CHANGED')
                                size=self._source.stat().st_size
                            except OSError:raise RelayError('SOURCE_CHANGED') from None
                            if size<last_size:raise RelayError('SOURCE_CHANGED')
                            if size>last_size:last_size=size;last_growth=time.monotonic()
                            if time.monotonic()-last_growth>15:raise RelayError('SOURCE_NOT_GROWING')
                            with self._lock:last_advance=self._last_advance
                            if time.monotonic()-last_advance>15:raise RelayError('RELAY_PROGRESS_TIMEOUT')
                finally:
                    if process is not None:
                        try:
                            if process.poll() is None:process.terminate()
                            process.wait(timeout=1)
                        except Exception:
                            try:process.kill();process.wait(timeout=1)
                            except Exception:pass
                        while process.poll() is None:
                            self._fail('CLEANUP_UNCONFIRMED',session=session,process=process);time.sleep(.2)
        except RelayError as exc:self._fail(exc.code,session=session,process=process)
        except Exception:self._fail('RELAY_START_FAILED',session=session,process=process)
        finally:
            if self._reader is not None:self._reader.join(timeout=1)
            with self._lock:
                if session==self._session and self._error is None:self._state='stopped'
            self._ready.set()

    def status(self) -> dict:
        with self._lock:
            process=self._process
            return {'status':self._state,'error_code':self._error,'target':'youtube',
                    'pid':None if process is None else process.pid,'frames':self._frames,'out_time_us':self._out_time,
                    'source_name':None if self._source is None else self._source.name,
                    'process_running':process is not None and process.poll() is None,
                    'platform_ingest_verified':False,'primary_modified':False,'mode':'archive_packet_copy'}

    def stop(self,*,timeout=3.0) -> bool:
        timeout=float(timeout)
        if not math.isfinite(timeout) or not 0<=timeout<=5:raise ValueError('Relay stop timeout exceeds bounds')
        self._stop.set();thread=self._thread
        if thread is not None and thread is not threading.current_thread():thread.join(timeout)
        return (thread is None or not thread.is_alive()) and (self._process is None or self._process.poll() is not None)
