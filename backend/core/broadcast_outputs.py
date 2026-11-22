"""Independent, bounded per-platform encoders fed by the owned local HLS.

No capture, process creation or network occurs on import/construction.
"""
from collections import deque
import os
from pathlib import Path
import re
import subprocess
import threading
import time

FFMPEG = Path('C:/Users/footb/AppData/Local/Microsoft/WinGet/Links/ffmpeg.EXE')
SOURCE = 'http://127.0.0.1:9011/hls/native/index.m3u8'


def encoder_command(profile, destination, hardware_decode=True):
    command = [str(FFMPEG), '-hide_banner', '-nostdin', '-loglevel', 'warning',
               '-progress', 'pipe:1', '-stats_period', '1', '-thread_queue_size', '32',
               '-re', '-live_start_index', '-2']
    if hardware_decode: command += ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
    command += ['-i', SOURCE, '-map', '0:v:0', '-map', '0:a:0']
    scale = 'scale_cuda' if hardware_decode else 'scale'
    size = f"{profile['width']}:{profile['height']}"
    command += ['-vf', f"{scale}={size},fps={profile['fps']}",
                '-c:v', 'h264_nvenc', '-preset', 'p5', '-profile:v', 'high', '-rc', 'cbr',
                '-b:v', f"{profile['video_kbps']}k", '-maxrate', f"{profile['video_kbps']}k",
                '-bufsize', f"{profile['video_kbps'] * 2}k", '-g', str(profile['fps'] * 2),
                '-bf', '2', '-spatial-aq', '1', '-aq-strength', '8', '-rc-lookahead', '16',
                '-c:a', 'aac', '-b:a', f"{profile['audio_kbps']}k", '-ar', '48000', '-ac', '2',
                '-rw_timeout', '8000000', '-tls_verify', '1', '-f', 'flv', destination]
    return command


class DestinationEncoder:
    def __init__(self, endpoint, profile):
        self.name = endpoint['name']
        self.profile = dict(profile)
        self._url = endpoint['url'].rstrip('/') + '/' + endpoint['key'].lstrip('/')
        self._secret = endpoint['key']
        self.process = None
        self.frames = 0
        self.media_us = 0
        self.attempts = 0
        self.error_code = None
        self._next_retry = 0.
        self._stopping = False
        self._hardware_decode = True
        self._errors = deque(maxlen=12)
        self._readers = []
        self._last_frame = self._last_media = 0
        self._frame_advanced = self._media_advanced = time.monotonic()

    def _redact(self, text):
        return re.sub(r'rtmps?://\S+', '[publish destination]',
                      text.replace(self._secret, '[redacted]').replace(self._url, '[publish destination]'))[:2000]

    def start(self):
        self.attempts += 1
        self.frames = self.media_us = 0
        self.error_code = None
        self._last_frame = self._last_media = 0
        self._frame_advanced = self._media_advanced = time.monotonic()
        self._errors.clear()
        self.process = subprocess.Popen(encoder_command(self.profile, self._url, self._hardware_decode),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        process = self.process
        def progress():
            try:
                for line in process.stdout:
                    if len(line) > 4096: continue
                    key, _, value = line.strip().partition('=')
                    if value.isdigit() and self.process is process:
                        if key == 'frame': self.frames = int(value)
                        elif key == 'out_time_us': self.media_us = int(value)
            finally:
                process.stdout.close()
        def errors():
            try:
                for line in process.stderr:
                    if self.process is process: self._errors.append(self._redact(line.strip()))
            finally:
                process.stderr.close()
        self._readers = [threading.Thread(target=fn, daemon=True,
                         name='AI-BS-output-' + self.name) for fn in (progress, errors)]
        for reader in self._readers: reader.start()
        return process

    def maintain(self):
        if self._stopping or self.process is None: return None
        now = time.monotonic()
        if self.frames > self._last_frame: self._last_frame = self.frames; self._frame_advanced = now
        if self.media_us > self._last_media: self._last_media = self.media_us; self._media_advanced = now
        if self.process.poll() is None:
            if now - self._frame_advanced <= 15 and now - self._media_advanced <= 15: return None
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=2)
            self.error_code = 'OUTPUT_STALLED'
        else:
            self.error_code = 'OUTPUT_ENCODER_EXITED'
        text = ' '.join(self._errors).lower()
        rejected = any(word in text for word in ('authentication', 'unauthorized', 'forbidden', 'invalid stream key'))
        if rejected:
            self.error_code = 'OUTPUT_AUTHENTICATION_REJECTED'
            return None
        if self.attempts >= 3: return None
        if not self._next_retry:
            self._next_retry = time.monotonic() + min(4, 2 ** (self.attempts - 1))
            return None
        if time.monotonic() < self._next_retry: return None
        self._next_retry = 0.
        if any(word in text for word in ('cuda', 'hardware device', 'hwaccel')):
            self._hardware_decode = False  # one bounded CPU-decoder fallback; still NVENC encode
        return self.start()

    def snapshot(self):
        alive = self.process is not None and self.process.poll() is None
        return {**self.profile, 'status': 'sending_unverified' if alive and self.frames else
                'connecting' if alive else 'failed', 'frames_encoded': self.frames,
                'out_time_us': self.media_us, 'attempts': self.attempts,
                'error_code': self.error_code, 'platform_acceptance_verified': False}

    def stop(self):
        self._stopping = True
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for reader in self._readers: reader.join(.25)
        return self.process is None or self.process.poll() is not None
