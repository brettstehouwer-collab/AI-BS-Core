"""Local CPU-only pattern WAV export; no devices, API keys, or network calls."""
from __future__ import annotations

import hashlib
import io
import math
import os
from pathlib import Path
import threading
import uuid
import wave

import numpy as np

from native_studio.audio_kernel import AudioEngine, N_STEPS, N_TRACKS, PatternSnapshot


class ExportCancelled(RuntimeError):
    pass


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise ExportCancelled('Pattern export cancelled before publication.')


def write_pattern_wav(destination: str | Path, snapshot: PatternSnapshot, *, bars: int = 4,
                      tail_seconds: float = 2.0, cancel: threading.Event | None = None) -> dict:
    """Export repeated current steps with a voice tail, never replacing a file.

    This is pattern audio, not a playlist/media/VST master. Use the same DSP as
    live playback in a separate engine; accepted edits are already detached.
    Windows rename publishes a complete file atomically and refuses collisions.
    Failed disk staging is retained for diagnosis instead of removing files.
    """
    if type(bars) is not int or not 1 <= bars <= 16:
        raise ValueError('Choose between one and sixteen pattern repeats.')
    if not math.isfinite(tail_seconds) or not 0 <= tail_seconds <= 5:
        raise ValueError('Voice tail must be between zero and five seconds.')
    if not isinstance(snapshot, PatternSnapshot):
        raise ValueError('A detached pattern snapshot is required.')
    if (type(snapshot.samplerate) is not int or not 16000 <= snapshot.samplerate <= 192000 or
            not math.isfinite(snapshot.bpm) or not 40 <= snapshot.bpm <= 300 or
            not math.isfinite(snapshot.swing) or not 0 <= snapshot.swing <= 0.5 or
            not math.isfinite(snapshot.master)):
        raise ValueError('Invalid pattern sample rate, tempo, swing or gain.')
    expected = [(snapshot.pattern, (N_TRACKS, N_STEPS)), (snapshot.notes, (N_TRACKS, N_STEPS)),
                (snapshot.track_gain, (N_TRACKS,)), (snapshot.mute, (N_TRACKS,))]
    if any(np.shape(value) != shape or not np.isfinite(value).all() for value, shape in expected):
        raise ValueError('Invalid pattern control arrays.')
    if np.any(snapshot.notes < 0) or np.any(snapshot.notes > 127):
        raise ValueError('Pattern notes must be valid MIDI pitches.')
    target = Path(destination).expanduser()
    if target.suffix.lower() != '.wav':
        raise ValueError('Choose a WAV file name.')
    target = target.parent.resolve(strict=True) / target.name
    if target.exists() or target.is_symlink():
        raise FileExistsError('Choose a new file name; the existing file is preserved.')
    if os.name != 'nt':
        raise OSError('Atomic WAV publication is supported by this Windows build only.')
    _check_cancel(cancel)
    renderer = AudioEngine(snapshot.samplerate)
    renderer._pattern[:] = snapshot.pattern
    renderer._notes[:] = snapshot.notes
    renderer._track_gain[:] = snapshot.track_gain
    renderer._mute[:] = snapshot.mute
    renderer.master, renderer.bpm, renderer.swing = snapshot.master, snapshot.bpm, snapshot.swing
    pattern_frames = round(bars * N_STEPS * snapshot.samplerate * 60.0 / snapshot.bpm / 4.0)
    tail_frames = round(tail_seconds * snapshot.samplerate)
    total_frames = pattern_frames + tail_frames
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(snapshot.samplerate)
        for playing, count in [(True, pattern_frames), (False, tail_frames)]:
            renderer.playing = playing
            remaining = count
            while remaining:
                _check_cancel(cancel)
                frames = min(remaining, renderer.MAX_BLOCK)
                mono = renderer.render_block(frames)
                if not np.isfinite(mono).all():
                    raise ValueError('The pattern renderer produced invalid audio.')
                pcm = np.rint(np.clip(mono, -1.0, 1.0) * 32767).astype('<i2')
                wav.writeframesraw(np.repeat(pcm[:, None], 2, axis=1).tobytes())
                remaining -= frames
    _check_cancel(cancel)
    payload = buffer.getvalue()
    with wave.open(io.BytesIO(payload), 'rb') as verified:
        if (verified.getnchannels(), verified.getsampwidth(), verified.getframerate(), verified.getnframes()) != (2, 2, snapshot.samplerate, total_frames):
            raise OSError('Rendered WAV verification failed.')
        if len(verified.readframes(total_frames)) != total_frames * 4:
            raise OSError('Rendered WAV contains incomplete audio.')
    digest = hashlib.sha256(payload).hexdigest()
    staging = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.wavtmp')
    with staging.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if hashlib.sha256(staging.read_bytes()).hexdigest() != digest:
        raise OSError('Saved audio readback did not match the rendered file.')
    _check_cancel(cancel)
    os.rename(staging, target)  # Windows refuses an existing destination, including a late collision.
    return {'path': str(target), 'frames': total_frames, 'samplerate': snapshot.samplerate,
            'channels': 2, 'sampleWidth': 2, 'bars': bars, 'durationSeconds': total_frames / snapshot.samplerate,
            'sha256': digest, 'bytes': len(payload), 'readbackVerified': True, 'scope': 'current-pattern-with-voice-tail'}
