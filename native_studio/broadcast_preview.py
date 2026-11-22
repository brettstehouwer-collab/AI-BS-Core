"""Read-only native playback of the coordinator's fixed, delayed local HLS.

No game/desktop capture, broadcast commands, credentials or audio-output object.
The UI supplies already-verified coordinator state; file reads stay in one small
worker. Shared source-directory ACLs remain a separate repository finding.
"""
from __future__ import annotations
import re
import math
import threading
import time
from pathlib import Path
from PyQt6.QtCore import QTimer,QUrl,pyqtSignal,Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget
from PyQt6.QtMultimedia import QMediaPlayer,QVideoSink,QVideoFrame
from native_studio.broadcast_ipc import read_shared_bytes

HLS_PATH=Path('C:/AI-BS/saved_data/broadcast_hls/secondary/index.m3u8')
PREVIEW_URL='http://127.0.0.1:9011/hls/native/index.m3u8'


def parse_preview_manifest(raw):
    if type(raw) is not bytes or len(raw)>32768:raise ValueError('HLS_INVALID')
    text=raw.decode('utf-8',errors='strict');lines=[line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0]!='#EXTM3U':raise ValueError('HLS_INVALID')
    sequence=None;segments=0
    tags=('#EXT-X-VERSION:','#EXT-X-TARGETDURATION:','#EXTINF:')
    for line in lines[1:]:
        if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            value=line.partition(':')[2]
            if sequence is not None or re.fullmatch('[0-9]{1,18}',value) is None:raise ValueError('HLS_INVALID')
            sequence=int(value)
        elif line=='#EXT-X-INDEPENDENT-SEGMENTS':pass
        elif line.startswith(tags):
            if re.fullmatch(r'#(?:EXT-X-VERSION|EXT-X-TARGETDURATION):[0-9]{1,4}|#EXTINF:[0-9]+(?:\.[0-9]+)?,',line) is None:raise ValueError('HLS_INVALID')
        elif re.fullmatch(r'segment_[A-Za-z0-9_-]{1,80}\.ts',line):segments+=1
        else:raise ValueError('HLS_INVALID')
    if sequence is None or not 1<=segments<=12:raise ValueError('HLS_INVALID')
    return sequence


class _ManifestMonitor:
    def __init__(self):
        self._lock=threading.Lock();self._stop=threading.Event();self._thread=None
        self._valid=False;self._sampled=0.;self._advanced=0.;self._sequence=None;self._modified=0.;self._error='HLS_UNAVAILABLE'
    def start(self):
        if self._stop.is_set():return False
        if self._thread is not None:return self._thread.is_alive()
        self._thread=threading.Thread(target=self._run,name='AI-BS-Preview-HLS-Metadata',daemon=True);self._thread.start();return True
    def _run(self):
        while not self._stop.is_set():
            started=time.monotonic();valid=False;sequence=None;modified=0.;error='HLS_UNAVAILABLE'
            try:
                if any(p.is_symlink() or p.is_junction() for p in (HLS_PATH,*HLS_PATH.parents)):raise ValueError()
                raw=read_shared_bytes(HLS_PATH,max_bytes=32768)
                sequence=parse_preview_manifest(raw)
                for name in raw.decode('utf-8').splitlines():
                    name=name.strip()
                    if name and not name.startswith('#'):
                        segment=HLS_PATH.parent/name
                        if segment.is_symlink() or segment.is_junction():raise ValueError()
                modified=HLS_PATH.stat().st_mtime
                if not -1<=time.time()-modified<=6:raise ValueError()
                valid=True;error=None
            except (OSError,ValueError,UnicodeError):pass
            with self._lock:
                if self._stop.is_set():break
                if valid and sequence!=self._sequence:self._advanced=started
                self._valid=valid;self._sequence=sequence;self._sampled=started;self._modified=modified;self._error=error
            self._stop.wait(.5)
    def snapshot(self):
        now=time.monotonic()
        with self._lock:
            return {'valid':self._valid,'fresh':0<=now-self._sampled<2,
                    'advancing':0<=now-self._advanced<6,'modified_utc':self._modified,'error_code':self._error}
    def stop(self,timeout=.2):
        self._stop.set();thread=self._thread
        if thread is not None and thread is not threading.current_thread():thread.join(max(0,min(.5,timeout)))
        return thread is None or not thread.is_alive()


class NativeBroadcastPreview(QWidget):
    frame_ready=pyqtSignal(QImage)
    cleared=pyqtSignal()
    state_changed=pyqtSignal(dict)

    def __init__(self,parent=None,*,player_factory=QMediaPlayer,sink_factory=QVideoSink,
                 manifest_factory=_ManifestMonitor,clock=time.monotonic):
        super().__init__(parent);self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
        self._clock=clock;self._player=player_factory(self);self._sink=sink_factory(self)
        self._player.setAudioOutput(None)
        self._manifest=manifest_factory();self._state=None;self._received=0.;self._session=None
        self._generation=0;self._frame_handler=None;self._error_handler=None
        self._enabled=True;self._closed=False;self._decoding=False;self._showing=False
        self._attempts=0;self._retry_at=0.;self._started_at=0.;self._last_frame=0.;self._frames=0
        self._label='waiting';self._error=None
        self._timer=QTimer(self);self._timer.setInterval(250);self._timer.timeout.connect(self._tick);self._timer.start()
        self.destroyed.connect(lambda *_args,monitor=self._manifest:monitor.stop(timeout=0))

    def _eligible(self):
        s=self._state
        if type(s) is not dict or not 0<=self._clock()-self._received<3:return False
        if not(s.get('active') is True and s.get('can_select') is True and type(s.get('protocol_version')) is int
               and s['protocol_version']==2 and s.get('capture_state')=='capturing'
               and type(s.get('session_id')) is str and re.fullmatch('[0-9a-f]{32}',s['session_id'])):return False
        for name in ('controller_pid','encoder_pid','frames_encoded','out_time_us'):
            if type(s.get(name)) is not int or s[name]<=0:return False
        for name in ('controller_create_time','encoder_create_time'):
            if type(s.get(name)) not in (int,float) or not math.isfinite(s[name]) or s[name]<=0:return False
        return s.get('source_mode')=='window' or (s.get('source_mode')=='auto_game' and s.get('game_frame_verified') is True)

    def _manifest_ready(self,manifest):
        if not all(manifest.get(key) is True for key in ('valid','fresh','advancing')):return False
        modified=manifest.get('modified_utc')
        # No timestamp tolerance: never admit a playlist predating this encoder.
        return (type(modified) in (int,float) and math.isfinite(modified)
                and self._eligible() and modified>=self._state['encoder_create_time'])

    def set_coordinator_state(self,state):
        if self._closed:return
        old=self._session;self._state=dict(state) if type(state) is dict else {};self._received=self._clock()
        new=tuple(self._state.get(key) for key in ('session_id','source_mode','controller_pid','controller_create_time','encoder_pid','encoder_create_time')) if self._eligible() else None
        if old!=new:
            self._unload();self._attempts=0;self._retry_at=0.
        self._session=new;self._tick()

    def set_preview_enabled(self,enabled):
        if type(enabled) is not bool:raise ValueError('Preview enable state must be explicit')
        if self._closed:return
        if enabled!=self._enabled:
            self._enabled=enabled;self._unload();self._attempts=0;self._retry_at=0.
        self._tick()

    def _publish(self,label,error=None):
        changed=(label,error)!=(self._label,self._error);self._label=label;self._error=error
        if changed:self.state_changed.emit(self.preview_status())

    def preview_status(self):
        return {'state':'closed' if self._closed else self._label,'error_code':self._error,
                'showing':self._showing and not self._closed,'frames_received':self._frames,
                'audio_enabled':False,'source_kind':'local_hls','delayed':True}

    def _unload(self):
        self._generation+=1;self._showing=False;self._decoding=False
        self.cleared.emit()
        if self._frame_handler is not None:
            try:self._sink.videoFrameChanged.disconnect(self._frame_handler)
            except (TypeError,RuntimeError):pass
        if self._error_handler is not None:
            try:self._player.errorOccurred.disconnect(self._error_handler)
            except (TypeError,RuntimeError):pass
        self._frame_handler=None;self._error_handler=None
        self._player.setVideoSink(None);self._sink.setVideoFrame(QVideoFrame())
        self._player.stop();self._player.setSource(QUrl())

    def _tick(self):
        if self._closed:return
        if not self._enabled:
            if self._decoding or self._showing:self._unload()
            self._publish('disabled');return
        if not self._eligible():
            if self._decoding or self._showing:self._unload()
            self._publish('stale' if self._state and self._clock()-self._received>=3 else 'held');return
        self._manifest.start();manifest=self._manifest.snapshot()
        if not self._manifest_ready(manifest):
            if self._decoding or self._showing:self._unload()
            self._publish('unavailable','HLS_STALE');return
        now=self._clock()
        if self._decoding:
            last=self._last_frame if self._showing else self._started_at
            if now-last>5:self._failed(self._generation)
            return
        if self._attempts>=3:self._publish('unavailable','PREVIEW_RETRY_LIMIT');return
        if now<self._retry_at:return
        self._attempts+=1;self._started_at=now;self._last_frame=0.;self._decoding=True
        generation=self._generation
        self._frame_handler=lambda frame,epoch=generation:self._frame(frame,epoch)
        self._error_handler=lambda *_args,epoch=generation:self._failed(epoch)
        self._sink.videoFrameChanged.connect(self._frame_handler,Qt.ConnectionType.QueuedConnection)
        self._player.errorOccurred.connect(self._error_handler,Qt.ConnectionType.QueuedConnection)
        self._player.setVideoSink(self._sink);self._publish('buffering')
        self._player.setSource(QUrl(PREVIEW_URL));self._player.play()

    def _failed(self,generation):
        if self._closed or generation!=self._generation:return
        self._unload();self._retry_at=self._clock()+min(4,.5*2**max(0,self._attempts-1))
        self._publish('unavailable','MEDIA_DECODE_FAILED')

    def _frame(self,frame,generation):
        if self._closed or generation!=self._generation or not self._decoding:return
        if not self._enabled or not self._eligible():self._tick();return
        manifest=self._manifest.snapshot()
        if not self._manifest_ready(manifest):self._tick();return
        if not frame.isValid():return
        now=self._clock()
        if self._showing and now-self._last_frame<.08:return
        image=frame.toImage()
        if image.isNull() or not 1<=image.width()*image.height()<=1920*1080:return
        if generation!=self._generation or not self._eligible():return
        self._last_frame=now;self._frames+=1;self._showing=True
        self.frame_ready.emit(image.copy());self._publish('showing')

    def shutdown(self):
        if self._closed:return self._manifest.stop(timeout=.2)
        self._closed=True;self._timer.stop();self._unload();self._publish('closed')
        return self._manifest.stop(timeout=.2)
