"""Follow policy-admitted WGC windows; no desktop or capture starts on import.

The fixed black buffer is an intentional holding slate, never verified gameplay.
Only an owned WGC frame from the currently admitted exact identity is reported
as a game frame. The consumer retains its existing fixed-format encoder.
"""
from __future__ import annotations

import math
import ntpath
import threading
import time

from backend.core.native_window_capture import CaptureUnavailable,NativeWindowCapture


def _process_matches(identity):
    try:
        import psutil
        process=psutil.Process(identity.pid)
        return (process.create_time()==identity.create_time
                and ntpath.normcase(ntpath.normpath(process.exe()))==ntpath.normcase(ntpath.normpath(identity.exe))
                and process.is_running())
    except Exception:return False


class FollowingWindowCapture:
    def __init__(self,initial_capture,initial_decision,selector,*,width=1280,height=720,fps=30,capture_factory=NativeWindowCapture,poll_interval=.5,identity_checker=_process_matches):
        if initial_capture is not None:
            source=getattr(initial_decision,'source',None)
            if (source is None or getattr(initial_capture,'hwnd',None)!=source.hwnd
                    or getattr(initial_capture,'pid',None)!=source.process.pid
                    or getattr(initial_capture,'title',None)!=source.title):
                raise ValueError('Initial capture must match the exact pinned selection')
            width,height,fps=initial_capture.width,initial_capture.height,initial_capture.fps
        NativeWindowCapture._check_size(width,height)
        if type(fps) is not int or not 1<=fps<=60 or not callable(selector):raise ValueError('Invalid follow configuration')
        if type(poll_interval) not in (int,float) or not math.isfinite(poll_interval) or not 0<=poll_interval<=5:
            raise ValueError('Selection interval exceeds bounds')
        self.width=width;self.height=height;self.fps=fps
        self._holding=b'\x00\x00\x00\xff'*(width*height)
        self._lock=threading.RLock();self._reader=threading.Lock()
        self._selector=selector;self._factory=capture_factory;self._interval=poll_interval
        self._identity_checker=identity_checker;self._intent_generation=0
        self._current=initial_capture;self._decision=initial_decision
        self._key=getattr(initial_decision,'source_key',None)
        self._pending=None;self._retired=[];self._closed=False;self._next_poll=0.
        self._switcher=None
        self._state='capturing' if initial_capture is not None else 'holding'
        self._reason='SELECTED_GAME' if initial_capture is not None else 'NO_VERIFIED_GAME';self._available=False
        self._manual=bool(getattr(initial_decision,'manual',False));self._verified=False
        self._attempt_key=None;self._retry_at=0.;self._retry_delay=1.

    def start(self,timeout=3):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=3:
            raise ValueError('Capture readiness deadline exceeds bounds')
        self._closed_check()
        return self.metadata()

    def _closed_check(self):
        with self._lock:
            if self._closed:raise CaptureUnavailable('FOLLOW_CAPTURE_CLOSED')

    def _retire(self,capture):
        if capture is None:return
        with self._lock:
            if not any(item is capture for item in self._retired):self._retired.append(capture)

    def _clear(self,reason):
        # Clear publication state before asking the previous provider to stop.
        # NativeWindowCapture.stop itself immediately discards its owned pixels.
        with self._lock:
            current=self._current;self._current=None;self._key=None
            self._available=False;self._verified=False;self._state='holding';self._reason=reason
        self._retire(current)

    def invalidate(self,reason='SOURCE_INTENT_CHANGED',*,manual=False):
        with self._lock:
            self._intent_generation+=1;self._next_poll=0.;self._manual=manual
            pending=self._pending;self._pending=None
        self._clear('SOURCE_INTENT_CHANGED');self._retire(pending);self._cleanup(.15)

    def _cleanup(self,timeout):
        deadline=time.monotonic()+max(0,timeout)
        with self._lock:captures=tuple(self._retired)
        for capture in captures:
            try:stopped=capture.stop(timeout=max(0,min(.5,deadline-time.monotonic()))) is True
            except Exception:stopped=False
            if stopped:
                with self._lock:self._retired=[item for item in self._retired if item is not capture]
        with self._lock:return not self._retired

    def _hold(self,reason):
        self._clear(reason);self._cleanup(.15);self._closed_check()
        return self._holding

    def _choose(self):
        try:
            result=self._selector(previous=self._decision)
            if type(result.manual) is not bool or type(result.must_clear) is not bool:raise ValueError()
            source=result.source;key=result.source_key
            if source is not None:
                process=source.process
                if (type(key) is not tuple or len(key)!=7 or key[0]!='window'
                        or type(source.hwnd) is not int or source.hwnd<=0
                        or type(process.pid) is not int or process.pid<=0
                        or type(source.title) is not str or not source.title):raise ValueError()
            return result
        except Exception:raise CaptureUnavailable('SELECTION_UNAVAILABLE') from None

    def _frame(self,capture,timeout,source):
        if self._identity_checker(source.process) is not True:raise CaptureUnavailable('PINNED_PROCESS_CHANGED')
        frame=capture.read_frame(timeout=min(.5,timeout))
        if (capture.width!=self.width or capture.height!=self.height or capture.fps!=self.fps
                or type(frame) is not bytes or len(frame)!=self.width*self.height*4):
            raise CaptureUnavailable('FOLLOW_FRAME_INVALID')
        if self._identity_checker(source.process) is not True:raise CaptureUnavailable('PINNED_PROCESS_CHANGED')
        return frame

    def read_frame(self,timeout=.5):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<=timeout<=3:
            raise ValueError('Frame wait exceeds bounds')
        with self._reader:
            self._closed_check();now=time.monotonic()
            with self._lock:
                current=self._current;due=now>=self._next_poll;generation=self._intent_generation
                current_source=getattr(self._decision,'source',None)
                if current is None and self._switcher is not None and self._switcher.is_alive():return self._holding
            if not due:
                if current is None:return self._holding
                try:
                    frame=self._frame(current,timeout,current_source);self._closed_check()
                    with self._lock:
                        if generation!=self._intent_generation or self._current is not current:return self._holding
                        self._available=True;self._verified=not self._manual
                        return frame
                except Exception:return self._hold('WINDOW_UNAVAILABLE')
            with self._lock:self._next_poll=now+self._interval
            try:chosen=self._choose()
            except CaptureUnavailable:return self._hold('SELECTION_UNAVAILABLE')
            self._closed_check()
            with self._lock:
                self._manual=chosen.manual
                current=self._current;same=current is not None and chosen.source_key==self._key
                self._decision=chosen
            if chosen.source is None:
                screen=getattr(getattr(chosen,'manual_source',None),'kind',None)=='screen'
                return self._hold('MANUAL_SCREEN_UNSUPPORTED' if screen else 'MANUAL_SOURCE_HELD' if chosen.manual else 'NO_VERIFIED_GAME')
            if same:
                try:
                    frame=self._frame(current,timeout,chosen.source);self._closed_check()
                    with self._lock:
                        if generation!=self._intent_generation or self._current is not current:return self._holding
                        self._available=True;self._verified=not chosen.manual
                        return frame
                except Exception:return self._hold('WINDOW_UNAVAILABLE')
            self._clear('SWITCHING_VERIFIED_SOURCE')
            if not self._cleanup(.25):return self._hold('CAPTURE_CLEANUP_UNCONFIRMED')
            self._closed_check()
            key=chosen.source_key
            if key!=self._attempt_key:self._attempt_key=key;self._retry_at=0.;self._retry_delay=1.
            if now<self._retry_at:return self._holding
            with self._lock:
                if self._closed:raise CaptureUnavailable('FOLLOW_CAPTURE_CLOSED')
                if self._switcher is not None and self._switcher.is_alive():return self._holding
                self._switcher=threading.Thread(target=self._start_candidate,args=(chosen,generation,timeout),
                                                name='AI-BS-WGC-Handover',daemon=True)
                self._switcher.start()
            return self._holding

    def _start_candidate(self,chosen,generation,timeout):
        capture=None;key=chosen.source_key
        try:
            self._closed_check();source=chosen.source
            if self._identity_checker(source.process) is not True:raise CaptureUnavailable('PINNED_PROCESS_CHANGED')
            capture=self._factory(source.hwnd,source.process.pid,source.title,
                                  fps=self.fps,width=self.width,height=self.height)
            with self._lock:
                if self._closed or generation!=self._intent_generation:raise CaptureUnavailable('SELECTION_CHANGED')
                self._pending=capture
            capture.start(timeout=3)
            self._frame(capture,timeout,chosen.source)
            self._closed_check();latest=self._choose()
            if latest.source is None or latest.source_key!=key:raise CaptureUnavailable('SELECTION_CHANGED')
            with self._lock:
                if self._closed or generation!=self._intent_generation:raise CaptureUnavailable('SELECTION_CHANGED')
                self._pending=None;self._current=capture;self._key=key;self._decision=latest
                self._state='capturing';self._reason='MANUAL_WINDOW' if latest.manual else 'VERIFIED_GAME'
                self._manual=latest.manual;self._available=True;self._verified=not latest.manual
                self._retry_at=0.;self._retry_delay=1.
        except Exception:
            with self._lock:
                if self._pending is capture:self._pending=None
                self._available=False;self._verified=False
                self._state='closed' if self._closed else 'holding';self._reason='SOURCE_READINESS_UNAVAILABLE'
                self._retry_at=time.monotonic()+self._retry_delay;self._retry_delay=min(30,self._retry_delay*2)
            self._retire(capture);self._cleanup(.25)

    def metadata(self):
        with self._lock:
            source=getattr(self._decision,'source',None) if self._current is not None else None
            return {'provider':'windows_graphics_capture_follow','pixel_format':'bgra',
                    'width':self.width,'height':self.height,'fps':self.fps,
                    'capture_state':'closed' if self._closed else self._state,'holding_reason':self._reason,
                    'game_frame_verified':self._verified and not self._closed,
                    'game_frame_available':self._available and not self._closed,
                    'manual':self._manual,'intentional_holding_frame':self._current is None and not self._closed,
                    'target_hwnd':None if source is None else source.hwnd,
                    'cleanup_pending':len(self._retired)+int(self._pending is not None),
                    'startup_pending':self._switcher is not None and self._switcher.is_alive(),'fallback_used':False}

    def snapshot(self):return self.read_frame()

    def stop(self,timeout=2):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<=timeout<=5:
            raise ValueError('Capture stop deadline exceeds bounds')
        deadline=time.monotonic()+timeout
        with self._lock:
            self._closed=True;self._state='closed';self._verified=False;self._available=False
            current=self._current;pending=self._pending;self._current=None;self._pending=None;self._key=None
            worker=self._switcher
        self._retire(current);self._retire(pending)
        self._cleanup(max(0,deadline-time.monotonic()))
        if worker is not None and worker is not threading.current_thread():worker.join(max(0,deadline-time.monotonic()))
        # A factory can finish after the first cleanup snapshot and retire its
        # just-created provider while stop is joining the handover worker.
        self._cleanup(max(0,deadline-time.monotonic()))
        with self._lock:
            return not self._retired and self._pending is None and (worker is None or not worker.is_alive())
