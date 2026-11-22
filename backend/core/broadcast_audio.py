"""Explicit WASAPI input capture over current-user-only, bounded PCM pipes.

Import and construction open no devices. Speech samples are never logged.
PyAudioWPatch API: https://github.com/s0d3s/PyAudioWPatch
"""
from collections import deque
import json
import math
import threading
import time
import uuid


class PcmQueue:
    def __init__(self, channels, capacity_frames):
        if type(channels) is not int or not 1 <= channels <= 8 or capacity_frames < 1:
            raise ValueError('Invalid PCM capacity')
        self.frame_bytes = channels * 4
        self.capacity = capacity_frames * self.frame_bytes
        self._chunks = deque()
        self._bytes = 0
        self._lock = threading.Lock()
        self.dropped_frames = 0

    def push(self, data):
        if not isinstance(data, bytes) or len(data) % self.frame_bytes:
            raise ValueError('Invalid float PCM packet')
        if not data: return
        with self._lock:
            self._chunks.append(data)
            self._bytes += len(data)
            excess = max(0, self._bytes - self.capacity)
            self.dropped_frames += excess // self.frame_bytes
            self._discard(excess)

    def _discard(self, size):
        while size and self._chunks:
            chunk = self._chunks.popleft()
            taken = min(size, len(chunk))
            if taken < len(chunk): self._chunks.appendleft(chunk[taken:])
            self._bytes -= taken
            size -= taken

    def read(self, frames):
        if type(frames) is not int or frames < 0: raise ValueError('Invalid PCM duration')
        size = frames * self.frame_bytes
        result = bytearray()
        with self._lock:
            while len(result) < size and self._chunks:
                chunk = self._chunks.popleft()
                taken = min(size - len(result), len(chunk))
                result.extend(chunk[:taken])
                self._bytes -= taken
                if taken < len(chunk): self._chunks.appendleft(chunk[taken:])
        result.extend(bytes(size - len(result)))
        return bytes(result)


def discover_devices():
    import pyaudiowpatch as pa
    audio = pa.PyAudio()
    try:
        host = audio.get_host_api_info_by_type(pa.paWASAPI)
        devices = list(audio.get_device_info_generator())
        return {'desktop_audio': [d['name'] for d in devices if d.get('isLoopbackDevice')],
                'mic': [d['name'] for d in devices if d['hostApi'] == host['index'] and
                        d['maxInputChannels'] > 0 and not d.get('isLoopbackDevice')],
                'default_desktop': audio.get_default_wasapi_loopback()['name']}
    finally:
        audio.terminate()


class PcmAudioPipe:
    def __init__(self, role, device):
        if role not in {'desktop_audio', 'mic'} or not isinstance(device, str) or not device:
            raise ValueError('Choose an explicit WASAPI input')
        self.role = role
        self.device = device
        self.path = r'\\.\pipe\AI_BS_Audio_' + uuid.uuid4().hex
        self.rate = 48000
        self.channels = 2
        self._audio = self._stream = self._handle = self._thread = self._queue = None
        self._stop = threading.Event()
        self.frames_captured = 0
        self.frames_written = 0
        self.rms_dbfs = -120.0
        self.error_code = None
        self.error_type = None
        self.stage = 'inactive'
        self.active = False

    def snapshot(self):
        return {'role': self.role, 'device': self.device, 'active': self.active,
                'frames_captured': self.frames_captured, 'frames_written': self.frames_written,
                'rms_dbfs': round(self.rms_dbfs, 2), 'signal_detected': self.rms_dbfs > -65,
                'dropped_frames': self._queue.dropped_frames if self._queue else 0,
                'error_code': self.error_code}

    def start(self):
        if self._thread is not None: raise ValueError('Audio capture already started')
        import pyaudiowpatch as pa
        import win32api, win32con, win32file, win32pipe, win32security, pywintypes
        try:
            self._audio = pa.PyAudio()
            host = self._audio.get_host_api_info_by_type(pa.paWASAPI)
            devices = list(self._audio.get_device_info_generator())
            if self.role == 'desktop_audio' and self.device == 'default':
                device = self._audio.get_default_wasapi_loopback()
            else:
                matches = [d for d in devices if d['name'] == self.device and
                           d['hostApi'] == host['index'] and d['maxInputChannels'] > 0 and
                           bool(d.get('isLoopbackDevice')) == (self.role == 'desktop_audio')]
                if len(matches) != 1: raise ValueError('AUDIO_DEVICE_UNAVAILABLE')
                device = matches[0]
            self.device = device['name']
            self.rate = int(device['defaultSampleRate'])
            self.channels = min(2, int(device['maxInputChannels']))
            self.chunk_frames = max(1, self.rate // 100)
            self._queue = PcmQueue(self.channels, self.rate // 4)
            def callback(data, frames, _time_info, status):
                if self._stop.is_set(): return None, pa.paComplete
                try:
                    self._queue.push(data)
                    self.frames_captured += frames
                except Exception:
                    self.error_code = 'AUDIO_CAPTURE_FAILED'
                    return None, pa.paAbort
                return None, pa.paContinue
            self._stream = self._audio.open(format=pa.paFloat32, channels=self.channels,
                rate=self.rate, input=True, input_device_index=device['index'],
                frames_per_buffer=self.chunk_frames, stream_callback=callback, start=False)
            token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
            try: sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            finally: token.Close()
            sid_text = win32security.ConvertSidToStringSid(sid)
            attrs = pywintypes.SECURITY_ATTRIBUTES()
            attrs.SECURITY_DESCRIPTOR = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
                f'D:P(A;;GA;;;SY)(A;;GA;;;{sid_text})', win32security.SDDL_REVISION_1)
            self._handle = win32pipe.CreateNamedPipe(self.path,
                win32pipe.PIPE_ACCESS_OUTBOUND | win32file.FILE_FLAG_OVERLAPPED,
                win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT | 8, 1, 65536, 65536, 0, attrs)
            self._stream.start_stream()
            self.active = True
            self._thread = threading.Thread(target=self._run, name='AI-BS-WASAPI-' + self.role, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self.error_code = 'AUDIO_DEVICE_OPEN_FAILED'
            self.stop()
            raise RuntimeError(self.error_code) from None

    def _operation(self, action):
        import pywintypes, win32event, win32file
        event = win32event.CreateEvent(None, True, False, None)
        operation = pywintypes.OVERLAPPED()
        operation.hEvent = event
        try:
            try:
                result = action(operation)
                code = result[0] if isinstance(result, tuple) else result
                if code in (0, 535): return True
            except pywintypes.error as error:
                if error.winerror == 535: return True  # client connected before ConnectNamedPipe
                if error.winerror != 997: raise
            while not self._stop.is_set():
                if win32event.WaitForSingleObject(event, 50) == 0:
                    win32file.GetOverlappedResult(self._handle, operation, False)
                    return True
            win32file.CancelIoEx(self._handle, operation)
            # Keep OVERLAPPED/event memory alive until Windows acknowledges
            # cancellation; closing it while I/O is pending is unsafe.
            try: win32file.GetOverlappedResult(self._handle, operation, True)
            except pywintypes.error as error:
                if error.winerror != 995: raise
            return False
        finally:
            event.Close()

    def _run(self):
        import numpy as np
        import win32file, win32pipe
        try:
            self.stage = 'connecting'
            if not self._operation(lambda operation: win32pipe.ConnectNamedPipe(self._handle, operation)): return
            self.stage = 'writing'
            deadline = time.monotonic()
            period = self.chunk_frames / self.rate
            while not self._stop.is_set():
                data = self._queue.read(self.chunk_frames)
                samples = np.nan_to_num(np.frombuffer(data, dtype='<f4'), nan=0., posinf=0., neginf=0.)
                rms = float(np.sqrt(np.mean(samples * samples))) if len(samples) else 0.
                self.rms_dbfs = max(-120., 20 * math.log10(max(rms, 1e-6)))
                if not self._operation(lambda operation: win32file.WriteFile(self._handle, data, operation)): break
                self.frames_written += self.chunk_frames
                deadline += period
                now = time.monotonic()
                if deadline < now - period: deadline = now
                self._stop.wait(max(0., deadline - now))
        except Exception as error:
            if not self._stop.is_set():
                self.error_code = 'AUDIO_PIPE_CLOSED'
                self.error_type = type(error).__name__
        finally:
            self.active = False

    def stop(self, timeout=2.):
        self._stop.set()
        if self._handle is not None:
            try:
                import win32file
                win32file.CancelIoEx(self._handle, None)
            except Exception: pass
        if self._thread and self._thread is not threading.current_thread(): self._thread.join(timeout)
        if self._handle is not None:
            try: self._handle.Close()
            except Exception: pass
            self._handle = None
        if self._stream is not None:
            try: self._stream.close()
            except Exception: pass
            self._stream = None
        if self._audio is not None:
            try: self._audio.terminate()
            except Exception: pass
            self._audio = None
        self.active = False
        return not (self._thread and self._thread.is_alive())


if __name__ == '__main__':
    print(json.dumps(discover_devices()))
