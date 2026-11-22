"""Bounded latest-frame WGC transport to one owned binary FFmpeg stdin."""
from __future__ import annotations
import threading
import time


class WindowCapturePipe:
    def __init__(self,capture,process,*,on_failure=None):
        width,height,fps=capture.width,capture.height,capture.fps
        if (type(width) is not int or type(height) is not int or not 2<=width<=8192
                or not 2<=height<=8192 or width*height>16777216
                or type(fps) is not int or not 1<=fps<=60):
            raise ValueError('Window capture dimensions/frame rate exceed bounds')
        self.capture=capture;self.process=process;self.on_failure=on_failure
        self.frame_bytes=width*height*4;self.fps=fps;self.frames_written=0
        self._stop=threading.Event();self._thread=None;self._closed=False
        self.failure_code=None

    def send_frame(self):
        # The provider retains only its latest owned frame. No frame queue is
        # accumulated here; at most one frame is in flight to the encoder.
        frame=self.capture.read_frame(timeout=0.5)
        if not isinstance(frame,bytes) or len(frame)!=self.frame_bytes:
            raise ValueError('Invalid owned BGRA frame')
        view=memoryview(frame);offset=0
        while offset<len(view):
            if self._stop.is_set():return
            count=self.process.stdin.write(view[offset:])
            if type(count) is not int or count<=0 or count>len(view)-offset:
                raise OSError('Raw video pipe made no progress')
            offset+=count
        self.frames_written+=1

    def run(self):
        deadline=time.monotonic()
        try:
            while not self._stop.is_set() and self.process.poll() is None:
                self.send_frame()
                # Skip missed deadlines instead of replaying a backlog of stale
                # frames. The next read always asks for the newest WGC surface.
                deadline=max(deadline+1/self.fps,time.monotonic())
                self._stop.wait(max(0,deadline-time.monotonic()))
        except Exception:
            if not self._stop.is_set():
                self.failure_code='window_capture_failed'
                if self.on_failure is not None:
                    try:self.on_failure(self.failure_code)
                    except Exception:pass
        finally:
            self.stop(timeout=2)

    def start(self):
        if self._thread is not None or self._closed:
            raise RuntimeError('Window capture pipe already started or closed')
        self._thread=threading.Thread(target=self.run,name='AI-BS-WGC-RawVideo',daemon=True)
        self._thread.start()

    def stop(self,timeout=2):
        if self._closed:return True
        deadline=time.monotonic()+max(0,min(float(timeout),5))
        self._stop.set()
        process=self.process
        # Closing a buffered stdin while its writer owns the pipe lock can
        # deadlock. Terminate the owned encoder first to release a blocked write.
        if process.poll() is None:
            try:
                process.terminate();process.wait(timeout=max(0.01,min(1,deadline-time.monotonic())))
            except Exception:
                try:
                    process.kill();process.wait(timeout=max(0.01,min(1,deadline-time.monotonic())))
                except Exception:pass
        process_stopped=process.poll() is not None
        try:capture_stopped=self.capture.stop(timeout=max(0,min(0.5,deadline-time.monotonic()))) is True
        except Exception:capture_stopped=False
        thread=self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0,deadline-time.monotonic()))
        writer_stopped=thread is None or thread is threading.current_thread() or not thread.is_alive()
        # After process exit and writer completion, stdin close cannot contend
        # with an active write. Failed termination retains the owned handle.
        if process_stopped and writer_stopped:
            try:process.stdin.close()
            except Exception:pass
        self._closed=process_stopped and capture_stopped and writer_stopped
        return self._closed
