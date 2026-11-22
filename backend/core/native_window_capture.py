"""Bounded Windows Graphics Capture for one explicit window surface.

No capture starts on import. GDI, desktop duplication, title substring matching,
OBS, and full-desktop fallback are deliberately absent. The consumer owns its
encoder; this module only supplies owned BGRA frame bytes from WGC callbacks.
"""
from __future__ import annotations

import importlib.metadata
import inspect
import math
import sys
import threading
import time


class CaptureUnavailable(RuntimeError):
    def __init__(self,code: str):
        self.code=code
        super().__init__(code)


def _capture_class():
    if sys.platform!='win32':
        raise CaptureUnavailable('WINDOWS_CAPTURE_UNAVAILABLE')
    from windows_capture import WindowsCapture
    if 'window_hwnd' not in inspect.signature(WindowsCapture).parameters:
        raise CaptureUnavailable('HWND_CAPTURE_API_UNAVAILABLE')
    return WindowsCapture


def availability() -> dict:
    """Metadata/API availability only; no surface or device is opened."""
    try:
        version=importlib.metadata.version('windows-capture')
        _capture_class()
        return {'available':True,'package_version':version,'window_hwnd_supported':True,
                'provider':'windows_graphics_capture_hwnd','surface_verified':False}
    except Exception:
        return {'available':False,'window_hwnd_supported':False,
                'provider':'windows_graphics_capture_hwnd','surface_verified':False}


def _read_window_identity(hwnd: int) -> dict:
    import win32gui
    import win32process
    exists=bool(win32gui.IsWindow(hwnd))
    if not exists:
        return {'exists':False}
    return {'exists':True,'visible':bool(win32gui.IsWindowVisible(hwnd)),
            'minimized':bool(win32gui.IsIconic(hwnd)),
            'pid':win32process.GetWindowThreadProcessId(hwnd)[1],
            'title':win32gui.GetWindowText(hwnd)}


class NativeWindowCapture:
    """One latest frame, fixed output dimensions, and explicit bounded lifecycle.

    WGC emits updates when the surface changes. Reading an unchanged latest
    frame is intentional for a constant-rate encoder; metadata reports its age
    and unique callback count. Closed or changed window identities never reuse it.
    """
    def __init__(self,hwnd: int,pid: int | None,title: str,*,fps: int=30,
                 width: int | None=None,height: int | None=None):
        if type(hwnd) is not int or not 0<hwnd<2**64:
            raise ValueError('A valid window handle is required')
        if pid is not None and (type(pid) is not int or pid<=0):
            raise ValueError('A valid process identity is required')
        if type(title) is not str or not title or len(title)>4096:
            raise ValueError('The exact window title is required')
        if type(fps) is not int or not 1<=fps<=60:
            raise ValueError('Capture frame rate must be between 1 and 60')
        if (width is None)!=(height is None):
            raise ValueError('Both output dimensions are required')
        if width is not None:
            self._check_size(width,height)
        self.hwnd=hwnd;self.pid=pid;self.title=title;self.fps=fps
        self.width=width;self.height=height
        self._lock=threading.RLock();self._stop=threading.Event()
        self._first=threading.Event();self._started=threading.Event()
        self._control_stopped=threading.Event()
        self._state='new';self._error=None;self._latest=None;self._last_frame_at=None
        self._frames=0;self._native_timespan=None;self._control=None;self._capture=None
        self._starter=None;self._stopper=None;self._stop_started=False;self._cleanup_error=False

    @staticmethod
    def _check_size(width,height):
        if (type(width) is not int or type(height) is not int
                or not 2<=width<=8192 or not 2<=height<=8192 or width*height>16777216):
            raise ValueError('Capture dimensions exceed bounds')

    def _identity(self):
        try:
            observed=_read_window_identity(self.hwnd)
            if (observed.get('exists') is not True or observed.get('visible') is not True
                    or observed.get('minimized') is not False or observed.get('title')!=self.title
                    or type(observed.get('pid')) is not int or observed['pid']<=0):
                raise ValueError('Selected window is unavailable')
            with self._lock:
                if self.pid is None:
                    self.pid=observed['pid']
                if observed['pid']!=self.pid:
                    raise ValueError('Selected process changed')
        except Exception as exc:
            self._fail('WINDOW_IDENTITY_CHANGED')
            raise CaptureUnavailable('WINDOW_IDENTITY_CHANGED') from exc

    def _fail(self,code):
        with self._lock:
            self._error=code;self._state='error';self._latest=None;self._stop.set()
        self._first.set();self._started.set()
        self._begin_control_stop()

    def _on_closed(self):
        with self._lock:
            self._state='closed';self._latest=None;self._stop.set()
        self._first.set();self._started.set()

    def _frame_bytes(self,frame):
        import numpy as np
        width=frame.width;height=frame.height
        self._check_size(width,height)
        array=frame.frame_buffer
        if (not isinstance(array,np.ndarray) or array.dtype!=np.uint8
                or array.shape!=(height,width,4)):
            raise ValueError('Invalid BGRA surface frame')
        with self._lock:
            if self.width is None:
                self.width=width;self.height=height
            output_size=(self.width,self.height)
        if output_size!=(width,height):
            import cv2
            array=cv2.resize(array,output_size,interpolation=cv2.INTER_AREA if self.width<width else cv2.INTER_LINEAR)
        # The mapped GPU view belongs to the callback. Retain only an owned copy.
        data=np.ascontiguousarray(array).tobytes()
        if len(data)!=self.width*self.height*4:
            raise ValueError('Invalid frame byte length')
        return data

    def _on_frame(self,frame,internal_control):
        if self._stop.is_set():
            internal_control.stop();return
        try:
            self._identity()
            data=self._frame_bytes(frame)
            with self._lock:
                if self._stop.is_set():
                    internal_control.stop();return
                self._latest=data;self._last_frame_at=time.monotonic();self._frames+=1
                self._native_timespan=frame.timespan if type(getattr(frame,'timespan',None)) is int else None
            self._first.set()
        except Exception:
            self._fail(self._error or 'INVALID_CAPTURE_FRAME')
            internal_control.stop()

    def _begin_control_stop(self):
        with self._lock:
            if self._control is None or self._stop_started:
                return
            self._stop_started=True
            control=self._control
            def stop_control():
                try:control.stop()
                except Exception:self._cleanup_error=True
                finally:self._control_stopped.set()
            self._stopper=threading.Thread(target=stop_control,name='AI-BS-WGC-Stop',daemon=True)
            self._stopper.start()

    def _launch(self):
        try:
            capture_type=_capture_class()
            capture=capture_type(window_hwnd=self.hwnd,window_name=None,monitor_index=None,
                                 cursor_capture=True,draw_border=None,secondary_window=False,
                                 minimum_update_interval=max(1,round(1000/self.fps)),dirty_region=False)
            self._capture=capture
            @capture.event
            def on_frame_arrived(frame,internal_control):
                self._on_frame(frame,internal_control)
            @capture.event
            def on_closed():
                self._on_closed()
            control=capture.start_free_threaded()
            with self._lock:self._control=control
            self._started.set()
            if self._stop.is_set():self._begin_control_stop()
        except Exception:
            self._fail(self._error or 'CAPTURE_PROVIDER_UNAVAILABLE')

    def start(self,timeout: float=3.0) -> dict:
        timeout=float(timeout)
        if not math.isfinite(timeout) or not 0<timeout<=3:
            raise ValueError('Capture readiness deadline must be at most three seconds')
        with self._lock:
            if self._state=='running':return self.metadata()
            if self._state not in {'new','starting'}:raise CaptureUnavailable(self._error or 'CAPTURE_CLOSED')
            if self._state=='new':
                self._identity();self._state='starting'
                self._starter=threading.Thread(target=self._launch,name='AI-BS-WGC-Start',daemon=True)
                self._starter.start()
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self._error or self._stop.is_set():
                self.stop(timeout=0.2);raise CaptureUnavailable(self._error or 'CAPTURE_CLOSED')
            if self._started.is_set() and self._first.is_set():
                with self._lock:
                    if self._latest is not None:
                        self._state='running';return self.metadata()
            self._first.wait(min(0.02,max(0,deadline-time.monotonic())))
        self._fail('CAPTURE_FIRST_FRAME_TIMEOUT');self.stop(timeout=0.2)
        raise CaptureUnavailable('CAPTURE_FIRST_FRAME_TIMEOUT')

    def read_frame(self,timeout: float=0.5) -> bytes:
        timeout=float(timeout)
        if not math.isfinite(timeout) or not 0<=timeout<=3:
            raise ValueError('Frame wait exceeds bounds')
        self._identity()
        if not self._first.wait(timeout):raise CaptureUnavailable('CAPTURE_FRAME_UNAVAILABLE')
        with self._lock:
            if self._stop.is_set() or self._error or self._latest is None:
                raise CaptureUnavailable(self._error or 'CAPTURE_CLOSED')
            control=self._control
            if control is not None and control.is_finished():
                self._on_closed();raise CaptureUnavailable('CAPTURE_CLOSED')
            return self._latest

    def snapshot(self) -> bytes:
        return self.read_frame()

    def snapshot_jpeg(self,*,quality: int=70,max_side: int=1280,max_bytes: int=2097152) -> bytes:
        """Encode only the currently validated frame, in memory and within bounds."""
        if (type(quality) is not int or not 40<=quality<=90
                or type(max_side) is not int or not 16<=max_side<=1920
                or type(max_bytes) is not int or not 256<=max_bytes<=2097152):
            raise ValueError('Preview limits are invalid')
        data=self.read_frame()
        import cv2
        import numpy as np
        image=np.frombuffer(data,dtype=np.uint8).reshape(self.height,self.width,4)[:,:,:3]
        if max(self.width,self.height)>max_side:
            ratio=max_side/max(self.width,self.height)
            size=(max(1,round(self.width*ratio)),max(1,round(self.height*ratio)))
            image=cv2.resize(image,size,interpolation=cv2.INTER_AREA)
        success,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,quality])
        if not success or encoded.nbytes>max_bytes:
            raise CaptureUnavailable('PREVIEW_SIZE_LIMIT')
        # Revalidate after encoding; a closed or changed window cannot publish
        # a cached preview after its capture identity was invalidated.
        self._identity()
        with self._lock:
            if self._stop.is_set() or self._error:
                raise CaptureUnavailable(self._error or 'CAPTURE_CLOSED')
        return encoded.tobytes()

    def metadata(self) -> dict:
        with self._lock:
            return {'provider':'windows_graphics_capture_hwnd','pixel_format':'bgra',
                    'hwnd':self.hwnd,'pid':self.pid,'width':self.width,'height':self.height,'fps':self.fps,
                    'state':self._state,'error_code':self._error,'frames_received':self._frames,
                    'frame_available':self._latest is not None,'buffered_frames':int(self._latest is not None),
                    'frame_age_seconds':None if self._last_frame_at is None else round(time.monotonic()-self._last_frame_at,4),
                    'native_timespan':self._native_timespan,'fallback_used':False}

    def stop(self,timeout: float=2.0) -> bool:
        timeout=float(timeout)
        if not math.isfinite(timeout) or not 0<=timeout<=5:
            raise ValueError('Capture shutdown deadline exceeds bounds')
        deadline=time.monotonic()+timeout
        with self._lock:
            self._stop.set();self._state='closed';self._latest=None
        self._first.set();self._started.set();self._begin_control_stop()
        for thread in (self._starter,self._stopper):
            if thread is not None and thread is not threading.current_thread():
                thread.join(max(0,deadline-time.monotonic()))
        # A late startup can publish its control while stop waits for startup.
        self._begin_control_stop()
        if self._stopper is not None and self._stopper is not threading.current_thread():
            self._stopper.join(max(0,deadline-time.monotonic()))
        return (not self._cleanup_error and all(thread is None or not thread.is_alive()
                for thread in (self._starter,self._stopper)))
