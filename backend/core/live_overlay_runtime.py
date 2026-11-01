"""Owned game-frame reactions. OCR/chat run off the encoder's capture thread."""
import ntpath
import re
import threading
import time
import uuid
from backend.core.live_event_overlay import EventBroker,render_overlay
from native_studio import live_overlay_control as control


class TwitchReader:
    """Public, read-only guest IRC. Never posts chat messages or opens credentials."""
    def __init__(self,channel,broker):
        self.channel=channel;self.broker=broker;self.state='connecting'
        self.error_type=None
        self._stop=threading.Event();self._socket=None
        self._thread=threading.Thread(target=self._run,name='AI-BS-overlay-chat',daemon=True)

    def start(self): self._thread.start()

    def _run(self):
        import websocket
        for attempt in range(5):
            if self._stop.is_set():break
            try:
                self._socket=websocket.create_connection('wss://irc-ws.chat.twitch.tv:443',timeout=3,http_no_proxy=['irc-ws.chat.twitch.tv'])
                nick='justinfan'+str(int(uuid.uuid4().hex[:8],16)%100000000)
                self._socket.send('PASS SCHMOOPIIE\r\nNICK '+nick+'\r\nJOIN #'+self.channel+'\r\n')
                while not self._stop.is_set():
                    try: message=self._socket.recv()
                    except websocket.WebSocketTimeoutException:continue
                    if not isinstance(message,str) or not message:raise ConnectionError()
                    if len(message)>16384:raise ValueError('Chat frame too large')
                    for line in message.split('\r\n'):
                        if line.startswith('PING '):self._socket.send('PONG '+line[5:]+'\r\n');continue
                        if ' 366 ' in line and '#'+self.channel in line:self.state='connected'
                        if 'authentication failed' in line.lower() or 'login authentication failed' in line.lower():
                            self.state='authentication_required';return
                        match=re.match(r'^:([A-Za-z0-9_]{1,32})![^ ]+ PRIVMSG #'+re.escape(self.channel)+r' :(.*)$',line)
                        if match:self.broker.chat(match[1],match[2])
            except Exception as error:
                self.error_type=type(error).__name__
                if not self._stop.is_set():self.state='reconnecting'
            finally:
                if self._socket:
                    try:self._socket.close()
                    except Exception:pass
                    self._socket=None
            if self._stop.wait(min(30,2**attempt)):break
        if not self._stop.is_set():self.state='unavailable_retry_limit'

    def stop(self):
        self._stop.set()
        if self._socket:
            try:self._socket.close()
            except Exception:pass
        if self._thread is not threading.current_thread():self._thread.join(1)
        self.state='disabled'


class OverlayService:
    def __init__(self):
        self.broker=EventBroker()
        self._lock=threading.RLock();self._stop=threading.Event();self._thread=None
        self._enabled=False;self._eligible=False;self._source=None;self._latest=None
        self._next_frame=0.;self._ocr=None;self._ocr_failures=0;self._ocr_state='waiting_for_game'
        self._chat=None;self._channel=None;self._last_command=None;self._error=None
        self._next_config=0.;self._next_status=0.;self._config=control.defaults()

    def start(self):
        if self._thread is None:
            self._thread=threading.Thread(target=self._run,name='AI-BS-game-events',daemon=True)
            self._thread.start()

    def process_frame(self,frame,width,height,source,eligible):
        with self._lock:
            self._eligible=bool(eligible)
            if not self._enabled or not eligible:
                self._source=None;self._latest=None;self.broker.set_source(None)
                return frame
            key=source if eligible else None
            if key!=self._source:
                self._source=key;self._latest=None;self.broker.set_source(key)
            now=time.monotonic()
            if self._config['screen_events'] and now>=self._next_frame:
                self._latest=(frame,width,height,key)
                self._next_frame=now+.8
            snapshot=self.broker.snapshot()
        try:return render_overlay(frame,width,height,snapshot)
        except Exception:
            self._error='OVERLAY_RENDER_UNAVAILABLE'
            return frame  # a reaction failure must not stop the underlying video

    def _commands(self):
        from native_studio.broadcast_ipc import read_private_json
        root=control.path('config').parent
        paths=sorted(root.glob('overlay_event_*.json'),key=lambda path:path.stat().st_mtime)[:16]
        for path in paths:
            if not re.fullmatch('overlay_event_[a-f0-9]{32}\\.json',path.name):continue
            try:
                command=read_private_json(path,max_bytes=1024)
                if control.valid_command(command) and -1<=time.time()-path.stat().st_mtime<=10:
                    if command['kind']=='hype':self.broker.hype()
                    else:self.broker.start_poll()
                    self._last_command=command['id']
            finally:path.unlink(missing_ok=True)

    def _observe(self,sample):
        if self._ocr_failures>=2 or not self._config['screen_events']:return
        try:
            if self._ocr is None:
                from rapidocr_onnxruntime import RapidOCR
                self._ocr=RapidOCR(det_use_cuda=False,cls_use_cuda=False,rec_use_cuda=False,
                                   intra_op_num_threads=2,inter_op_num_threads=1,det_limit_side_len=640)
            import cv2
            import numpy as np
            frame,width,height,key=sample
            image=np.frombuffer(frame,dtype=np.uint8).reshape(height,width,4)
            texts=[]
            # The game chat and minimap edges are excluded. Input is the raw
            # captured frame, so the overlay cannot read its own reactions.
            for top,bottom in ((.03,.43),(.43,.85)):
                roi=image[int(height*top):int(height*bottom),int(width*.15):int(width*.85),:3].copy()
                if roi.shape[1]>960:roi=cv2.resize(roi,(960,max(1,int(roi.shape[0]*960/roi.shape[1]))))
                results,_=self._ocr(roi)
                texts.extend((str(row[1]),float(row[2])) for row in (results or []) if len(row)>=3)
            with self._lock:
                if self._enabled and self._eligible and key==self._source:self.broker.observe(texts,key)
            self._ocr_state='local_ai_ready';self._ocr_failures=0
        except Exception as error:
            self._ocr_failures+=1
            self._ocr_state='unavailable' if self._ocr_failures>=2 else 'retrying'
            self._error='OCR_'+type(error).__name__[:40]

    def _configure(self):
        try:
            config=control.load()
            with self._lock:
                self._config=config;self._enabled=config['enabled']
                if not self._enabled:
                    self._latest=None;self.broker.set_source(None)
            want_chat=config['enabled'] and config['chat_enabled']
            if self._chat and (not want_chat or config['channel']!=self._channel):
                self._chat.stop();self._chat=None
            if want_chat and self._chat is None:
                self._channel=config['channel'];self._chat=TwitchReader(self._channel,self.broker);self._chat.start()
            self._error=None
        except Exception:
            with self._lock:self._enabled=False;self._latest=None
            self._error='OVERLAY_SETTINGS_UNAVAILABLE'

    def _publish(self):
        from native_studio.broadcast_ipc import write_private_json
        snapshot=self.broker.snapshot()
        write_private_json(control.path('status'),{
            'state':'active' if self._enabled and self._eligible else 'waiting_for_game' if self._enabled else 'disabled',
            'enabled':self._enabled,'game_eligible':self._eligible,'screen_detector':self._ocr_state,
            'chat':self._chat.state if self._chat else 'disabled','caption_source':'curated_event_reactions',
            'hype_count':snapshot['hype_count'],'poll':snapshot['poll'],
            'last_command_id':self._last_command,'error_code':self._error},max_bytes=8192)

    def _run(self):
        while not self._stop.wait(.2):
            now=time.monotonic()
            try:
                if now>=self._next_config:self._configure();self._next_config=now+.5
                if self._enabled:
                    self._commands()
                    with self._lock:sample=self._latest;self._latest=None
                    if sample:self._observe(sample)
                if now>=self._next_status:self._publish();self._next_status=now+1
            except Exception:self._error='OVERLAY_STATUS_UNAVAILABLE'
        if self._chat:self._chat.stop()

    def stop(self,timeout=1):
        self._stop.set()
        if self._chat:self._chat.stop()
        if self._thread and self._thread is not threading.current_thread():self._thread.join(timeout)
        with self._lock:self._enabled=False;self._latest=None;self.broker.set_source(None)
        return self._thread is None or not self._thread.is_alive()


class OverlayCapture:
    def __init__(self,base,*,service=None):
        self.base=base;self.runtime=service if service is not None else OverlayService()
        self.width=base.width;self.height=base.height;self.fps=base.fps

    def __getattr__(self,name):return getattr(self.base,name)

    def start(self,timeout=3):
        result=self.base.start(timeout=timeout);self.runtime.start();return result

    def read_frame(self,timeout=.5):
        frame=self.base.read_frame(timeout=timeout);metadata=self.base.metadata()
        decision=getattr(self.base,'_decision',None);source=getattr(decision,'source',None)
        identity=getattr(source,'process',None)
        exe=ntpath.basename(str(getattr(identity,'exe',''))).casefold()
        manual_game=(getattr(source,'hwnd',None)==metadata.get('target_hwnd') and
                     ('fortnite' in exe or exe in {'cod.exe','cod23.exe','cod24.exe','cs2.exe','r5apex.exe','overwatch.exe'}))
        eligible=(metadata.get('capture_state')=='capturing' and metadata.get('game_frame_available') is True
                  and (metadata.get('game_frame_verified') is True or manual_game))
        key=(metadata.get('target_hwnd'),metadata.get('manual'),getattr(identity,'pid',None),getattr(identity,'create_time',None))
        return self.runtime.process_frame(frame,self.width,self.height,key,eligible)

    def stop(self,timeout=2):
        started=time.monotonic();analysis_stopped=self.runtime.stop(timeout=min(.5,timeout))
        capture_stopped=self.base.stop(timeout=max(0,timeout-(time.monotonic()-started)))
        return bool(analysis_stopped and capture_stopped)
