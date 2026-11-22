"""AI-BS Native Audio Kernel: WASAPI Exclusive + MMCSS "Pro Audio" + SPSC event ring.

Replaces the browser Tone.js / Web Audio engine used by the AI Music Studio.

Architecture (zero sockets, zero web runtimes):

    Qt GUI thread  --(SpscRing: note/step/transport events)-->  audio callback thread
    audio callback thread --(scope ring + stats)-->  Qt GUI thread (read only)

* The GUI thread is the only producer of the event ring, the PortAudio/WASAPI
  callback thread is the only consumer. Indices are single-writer, so no lock is
  taken on the audio thread.
* All voice/drum buffers are pre-allocated at start-up. The callback performs no
  allocation beyond short numpy temporaries sized to one block.
* Output goes through WASAPI Exclusive mode (bypasses the Windows mixer) when the
  endpoint accepts it, with an explicit, honest fallback chain that is reported
  in ``stats()["mode"]`` so the UI never claims latency it does not have.

``stats()`` only reports values measured from the live stream (PortAudio reported
latency, measured callback time, underflow count). Nothing is simulated.
"""

from __future__ import annotations

import ctypes
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:  # PortAudio binding, WASAPI host API
    import sounddevice as sd
except Exception as _exc:  # noqa: BLE001
    sd = None  # type: ignore[assignment]
    _SD_ERROR = str(_exc)
else:
    _SD_ERROR = ""

# ---------------------------------------------------------------------------
# Event protocol (rows of float64[6]: type, a, b, c, d, e)
# ---------------------------------------------------------------------------
EV_PLAY = 1        # a=1 start / 0 stop
EV_BPM = 2         # a=bpm
EV_STEP = 3        # a=track b=step c=on(0/1) d=midi note
EV_NOTE = 4        # a=track b=midi note c=velocity(0-1)  (live audition)
EV_GAIN = 5        # a=track(-1 master) b=gain
EV_CLEAR = 6       # clear whole pattern
EV_SWING = 7       # a=swing 0..0.5
EV_MUTE = 8        # a=track b=mute(0/1)

N_TRACKS = 8
N_STEPS = 16
TRACK_NAMES = ("Kick", "Snare", "Clap", "Hat C", "Hat O", "Tom", "Bass", "Lead")
SYNTH_TRACKS = (6, 7)
_EVENT_WIDTH = 6


class SpscRing:
    """Single-producer / single-consumer ring of fixed-width event rows.

    ``head`` is written only by the producer and ``tail`` only by the consumer,
    so neither side needs a lock. Capacity must be a power of two.
    """

    def __init__(self, capacity: int = 4096, width: int = _EVENT_WIDTH) -> None:
        if capacity & (capacity - 1):
            raise ValueError("capacity must be a power of two")
        self.buf = np.zeros((capacity, width), dtype=np.float64)
        self.mask = capacity - 1
        self.head = 0
        self.tail = 0
        self.dropped = 0

    def push(self, *row: float) -> bool:
        head = self.head
        if ((head + 1) & self.mask) == self.tail:
            self.dropped += 1
            return False
        slot = self.buf[head]
        slot[:] = 0.0
        slot[: len(row)] = row
        self.head = (head + 1) & self.mask
        return True

    def pop(self) -> np.ndarray | None:
        tail = self.tail
        if tail == self.head:
            return None
        row = self.buf[tail]
        self.tail = (tail + 1) & self.mask
        return row


# ---------------------------------------------------------------------------
# Windows MMCSS (Multimedia Class Scheduler Service)
# ---------------------------------------------------------------------------
AVRT_PRIORITY_CRITICAL = 2


def register_mmcss(task: str = "Pro Audio") -> dict[str, Any]:
    """Register the *calling* thread with MMCSS. Returns what Windows actually did."""
    info: dict[str, Any] = {"task": task, "registered": False, "handle": 0, "error": None}
    try:
        avrt = ctypes.WinDLL("avrt.dll", use_last_error=True)
        avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p
        avrt.AvSetMmThreadCharacteristicsW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        avrt.AvSetMmThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
        idx = ctypes.c_ulong(0)
        handle = avrt.AvSetMmThreadCharacteristicsW(task, ctypes.byref(idx))
        if handle:
            avrt.AvSetMmThreadPriority(handle, AVRT_PRIORITY_CRITICAL)
            info.update(registered=True, handle=int(handle), task_index=int(idx.value))
        else:
            err = ctypes.get_last_error()
            if err == 1552:  # ERROR_THREAD_ALREADY_IN_TASK: PortAudio's WASAPI host thread already joined MMCSS
                info.update(registered=True, note="already registered by PortAudio WASAPI host (Pro Audio)")
            else:
                info["error"] = f"AvSetMmThreadCharacteristicsW failed (winerr={err})"
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def boost_process_priority() -> bool:
    """Raise process priority class so UI/AI work cannot starve the audio thread."""
    try:
        k32 = ctypes.WinDLL("kernel32.dll")
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        return bool(k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00008000))  # ABOVE_NORMAL
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Pre-rendered drum voices
# ---------------------------------------------------------------------------
def _env(n: int, sr: int, decay_s: float) -> np.ndarray:
    return np.exp(-np.arange(n) / (sr * decay_s))


def _render_drums(sr: int) -> list[np.ndarray]:
    rng = np.random.default_rng(1996)
    t = lambda s: np.arange(int(sr * s)) / sr  # noqa: E731

    tk = t(0.45)
    sweep = 45.0 + 110.0 * np.exp(-tk * 28.0)
    kick = np.sin(2 * np.pi * np.cumsum(sweep) / sr) * _env(len(tk), sr, 0.16)
    kick += 0.35 * np.sin(2 * np.pi * 1800 * tk) * _env(len(tk), sr, 0.004)

    ts = t(0.28)
    snare = (0.55 * rng.standard_normal(len(ts)) * _env(len(ts), sr, 0.07)
             + 0.6 * np.sin(2 * np.pi * 185 * ts) * _env(len(ts), sr, 0.06))

    tc = t(0.30)
    clap_env = sum(_env(len(tc), sr, 0.045) * (np.arange(len(tc)) >= int(sr * d)) for d in (0.0, 0.011, 0.022))
    clap = rng.standard_normal(len(tc)) * clap_env * 0.35

    def hat(length: float, decay: float) -> np.ndarray:
        n = int(sr * length)
        noise = rng.standard_normal(n)
        hp = np.diff(noise, prepend=0.0)  # crude high-pass
        return hp * _env(n, sr, decay) * 0.35

    tt = t(0.35)
    tom = np.sin(2 * np.pi * np.cumsum(90.0 + 90.0 * np.exp(-tt * 14.0)) / sr) * _env(len(tt), sr, 0.12)

    return [a.astype(np.float32) for a in (kick, snare, clap, hat(0.07, 0.018), hat(0.35, 0.11), tom * 0.9)]


@dataclass
class _Voice:
    active: bool = False
    freq: float = 0.0
    phase: float = 0.0
    env: float = 0.0
    rate: float = 8.0       # exponential decay rate (1/s)
    gain: float = 0.0
    track: int = 6


@dataclass
class EngineStats:
    mode: str = "stopped"
    exclusive: bool = False
    device: str = ""
    samplerate: int = 0
    blocksize: int = 0
    reported_latency_ms: float = 0.0
    block_ms: float = 0.0
    cb_avg_ms: float = 0.0
    cb_max_ms: float = 0.0
    cpu_load: float = 0.0
    underflows: int = 0
    callbacks: int = 0
    events_dropped: int = 0
    mmcss: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True)
class PatternSnapshot:
    """Detached control-plane intent; independent of live callback buffers."""
    samplerate: int
    pattern: np.ndarray
    notes: np.ndarray
    track_gain: np.ndarray
    mute: np.ndarray
    master: float
    bpm: float
    swing: float


class AudioEngine:
    """Sequencer + synth + WASAPI Exclusive output."""

    MAX_BLOCK = 2048
    N_VOICES = 24
    SCOPE_LEN = 4096

    def __init__(self, samplerate: int = 48000) -> None:
        self.sr = samplerate
        self.ring = SpscRing()
        self._pattern = np.zeros((N_TRACKS, N_STEPS), dtype=bool)
        self._notes = np.tile(np.array([36, 38, 39, 42, 46, 45, 36, 60], dtype=np.int16)[:, None], (1, N_STEPS))
        self._track_gain = np.array([1.0, 0.85, 0.7, 0.55, 0.5, 0.8, 0.9, 0.55], dtype=np.float32)
        self._mute = np.zeros(N_TRACKS, dtype=bool)
        self.master = 0.8
        self.bpm = 124.0
        self.swing = 0.0
        self.playing = False
        self._step = 0
        self._samples_to_step = 0.0
        self._drums = _render_drums(samplerate)
        self._drum_pos: list[list[tuple[np.ndarray, int, float]]] = [[] for _ in self._drums]
        self._voices = [_Voice() for _ in range(self.N_VOICES)]
        self._idx = (np.arange(self.MAX_BLOCK, dtype=np.float64) / samplerate)
        self._mix = np.zeros(self.MAX_BLOCK, dtype=np.float32)
        self.scope = np.zeros(self.SCOPE_LEN, dtype=np.float32)
        self._scope_w = 0
        self.play_step = -1               # read by GUI for the playhead
        self._stats = EngineStats()
        self._cb_sum = 0.0
        self._mmcss_done = False
        self._stream: Any = None
        self._lock = threading.Lock()     # control-plane only, never taken in callback
        self._export_lock = threading.Lock()
        self._export_pattern = self._pattern.copy()
        self._export_notes = self._notes.copy()
        self._export_gain = self._track_gain.copy()
        self._export_mute = self._mute.copy()
        self._export_master, self._export_bpm, self._export_swing = self.master, self.bpm, self.swing

    # ----------------------------------------------------------- control API
    def send(self, *row: float) -> bool:
        """Queue GUI intent; the audio consumer remains lock-free.

        Keep an export mirror of accepted events so an idle device is never
        opened, nor the live single-consumer queue drained, merely to save audio.
        """
        accepted = self.ring.push(*row)
        if not accepted:
            return False
        event = list(row) + [0.0] * _EVENT_WIDTH
        with self._export_lock:
            kind = int(event[0])
            if kind == EV_STEP:
                track, step = int(event[1]) % N_TRACKS, int(event[2]) % N_STEPS
                self._export_pattern[track, step] = event[3] > 0.5
                if event[4] >= 0:
                    self._export_notes[track, step] = int(event[4])
            elif kind == EV_BPM:
                self._export_bpm = float(min(300.0, max(40.0, event[1])))
            elif kind == EV_SWING:
                self._export_swing = float(min(0.5, max(0.0, event[1])))
            elif kind == EV_GAIN:
                if int(event[1]) < 0:
                    self._export_master = float(event[2])
                else:
                    self._export_gain[int(event[1]) % N_TRACKS] = event[2]
            elif kind == EV_MUTE:
                self._export_mute[int(event[1]) % N_TRACKS] = event[2] > 0.5
            elif kind == EV_CLEAR:
                self._export_pattern[:] = False
        return True

    def pattern_snapshot(self) -> PatternSnapshot:
        """Capture accepted edits without touching the audio callback or device."""
        with self._export_lock:
            arrays = [value.copy() for value in (self._export_pattern, self._export_notes, self._export_gain, self._export_mute)]
            for value in arrays:
                value.setflags(write=False)
            return PatternSnapshot(self.sr, *arrays, self._export_master, self._export_bpm, self._export_swing)

    def set_step(self, track: int, step: int, on: bool, note: int | None = None) -> None:
        self.send(EV_STEP, track, step, 1.0 if on else 0.0, -1 if note is None else note)

    def play(self, on: bool = True) -> None:
        self.send(EV_PLAY, 1.0 if on else 0.0)

    def set_bpm(self, bpm: float) -> None:
        self.send(EV_BPM, bpm)

    def audition(self, track: int, note: int = -1, vel: float = 0.9) -> None:
        if self._stream is None:
            try:
                self.start()
            except Exception as exc:
                self._stats.mode = "failed"
                self._stats.error = str(exc)
                return
            if self._stream is None:
                return
        self.send(EV_NOTE, track, note, vel)

    # --------------------------------------------------------------- stream
    @staticmethod
    def list_devices() -> list[dict[str, Any]]:
        if sd is None:
            return []
        out = []
        apis = sd.query_hostapis()
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] > 0:
                out.append({"index": i, "name": d["name"], "host": apis[d["hostapi"]]["name"],
                            "default_sr": d["default_samplerate"]})
        return out

    def start(self, device: int | None = None, blocksize: int = 64, prefer_exclusive: bool = True) -> EngineStats:
        if sd is None:
            self._stats.error = f"sounddevice unavailable: {_SD_ERROR}"
            return self._stats
        self.stop()
        boost_process_priority()
        wasapi = next((i for i, h in enumerate(sd.query_hostapis()) if "WASAPI" in h["name"]), None)
        if device is None and wasapi is not None:
            device = sd.query_hostapis(wasapi)["default_output_device"]
        dev_info = sd.query_devices(device) if device is not None else sd.query_devices(kind="output")
        dev_name = dev_info["name"]
        rates = [int(dev_info["default_samplerate"]), 48000, 44100, 96000]
        rates = list(dict.fromkeys(rates))
        attempts: list[tuple[bool, int, int]] = []
        if prefer_exclusive and wasapi is not None:
            for sr in rates:
                for bs in dict.fromkeys((blocksize, 128, 256, 512)):
                    attempts.append((True, sr, bs))
        attempts.append((False, rates[0], max(blocksize, 128)))
        errors: list[str] = []
        for exclusive, sr, bs in attempts:
            try:
                if sr != self.sr:
                    self._rebuild(sr)
                extra = sd.WasapiSettings(exclusive=True) if exclusive else (
                    sd.WasapiSettings(auto_convert=True) if wasapi is not None else None)
                stream = sd.OutputStream(
                    samplerate=sr, blocksize=bs, device=device, channels=2, dtype="float32",
                    latency="low", extra_settings=extra, callback=self._callback)
                stream.start()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{'EXCL' if exclusive else 'SHARED'} {sr}Hz/{bs}: {str(exc)[:70]}")
                continue
            self._stream = stream
            st = self._stats
            st.exclusive, st.samplerate, st.blocksize, st.device = exclusive, sr, bs, dev_name
            st.mode = "WASAPI Exclusive" if exclusive else "WASAPI Shared (fallback)"
            st.reported_latency_ms = float(stream.latency) * 1000.0
            st.block_ms = bs / sr * 1000.0
            st.error = " | ".join(errors[-3:])
            return st
        self._stats.mode = "failed"
        self._stats.error = " | ".join(errors[-4:])
        return self._stats

    def stop(self) -> None:
        s, self._stream = self._stream, None
        if s is not None:
            try:
                s.stop()
                s.close()
            except Exception:  # noqa: BLE001
                pass
        self._stats.mode = "stopped"

    def _rebuild(self, sr: int) -> None:
        self.sr = sr
        self._drums = _render_drums(sr)
        self._drum_pos = [[] for _ in self._drums]
        self._idx = np.arange(self.MAX_BLOCK, dtype=np.float64) / sr
        self._samples_to_step = 0.0

    def stats(self) -> EngineStats:
        st = self._stats
        st.events_dropped = self.ring.dropped
        if self._stream is not None:
            try:
                st.cpu_load = float(self._stream.cpu_load) * 100.0
            except Exception:  # noqa: BLE001
                pass
        return st

    # ------------------------------------------------------------------ DSP
    def _drain_events(self) -> None:
        ring = self.ring
        while True:
            ev = ring.pop()
            if ev is None:
                return
            kind = int(ev[0])
            if kind == EV_STEP:
                tr, stp = int(ev[1]) % N_TRACKS, int(ev[2]) % N_STEPS
                self._pattern[tr, stp] = ev[3] > 0.5
                if ev[4] >= 0:
                    self._notes[tr, stp] = int(ev[4])
            elif kind == EV_PLAY:
                self.playing = ev[1] > 0.5
                if self.playing:
                    self._step, self._samples_to_step = 0, 0.0
                else:
                    self.play_step = -1
            elif kind == EV_BPM:
                self.bpm = float(min(300.0, max(40.0, ev[1])))
            elif kind == EV_SWING:
                self.swing = float(min(0.5, max(0.0, ev[1])))
            elif kind == EV_NOTE:
                self._trigger(int(ev[1]) % N_TRACKS, int(ev[2]), float(ev[3]))
            elif kind == EV_GAIN:
                if int(ev[1]) < 0:
                    self.master = float(ev[2])
                else:
                    self._track_gain[int(ev[1]) % N_TRACKS] = ev[2]
            elif kind == EV_MUTE:
                self._mute[int(ev[1]) % N_TRACKS] = ev[2] > 0.5
            elif kind == EV_CLEAR:
                self._pattern[:] = False

    def _trigger(self, track: int, note: int, vel: float) -> None:
        if self._mute[track]:
            return
        g = float(self._track_gain[track]) * vel
        if track in SYNTH_TRACKS:
            note = note if note >= 0 else int(self._notes[track, 0])
            voice = next((v for v in self._voices if not v.active), min(self._voices, key=lambda v: v.env))
            voice.active, voice.freq, voice.phase = True, 440.0 * 2 ** ((note - 69) / 12.0), 0.0
            voice.env, voice.gain, voice.track = 1.0, g, track
            voice.rate = 6.5 if track == 6 else 14.0
        else:
            self._drum_pos[track].append((self._drums[track], 0, g))
            if len(self._drum_pos[track]) > 6:
                self._drum_pos[track].pop(0)

    def _mix_voices(self, n: int, out: np.ndarray) -> None:
        idx = self._idx[:n]
        for track, plist in enumerate(self._drum_pos):
            if not plist:
                continue
            alive = []
            for buf, pos, g in plist:
                take = min(n, len(buf) - pos)
                if take > 0:
                    out[:take] += buf[pos:pos + take] * g
                if pos + take < len(buf):
                    alive.append((buf, pos + take, g))
            self._drum_pos[track] = alive
        for v in self._voices:
            if not v.active:
                continue
            ph = v.phase + v.freq * idx
            w = 2.0 * math.pi * ph
            if v.track == 6:   # bass: sine + 2nd harmonic
                sig = np.sin(w) + 0.35 * np.sin(2.0 * w)
            else:              # lead: band-limited square (3 odd partials)
                sig = np.sin(w) + np.sin(3.0 * w) / 3.0 + np.sin(5.0 * w) / 5.0
            env = v.env * np.exp(-v.rate * idx)
            out += (sig * env * v.gain * 0.45).astype(np.float32)
            v.phase = (v.phase + v.freq * n / self.sr) % 1.0
            v.env = float(v.env * math.exp(-v.rate * n / self.sr))
            if v.env < 1e-3:
                v.active = False

    def _fire_step(self) -> None:
        s = self._step
        for tr in range(N_TRACKS):
            if self._pattern[tr, s]:
                self._trigger(tr, int(self._notes[tr, s]), 1.0)
        self.play_step = s
        self._step = (s + 1) % N_STEPS

    def render_block(self, frames: int) -> np.ndarray:
        """Render one mono block (also used for offline verification)."""
        self._drain_events()
        mix = self._mix[:frames]
        mix[:] = 0.0
        pos = 0
        if self.playing:
            step_len = self.sr * 60.0 / self.bpm / 4.0
            while pos < frames:
                if self._samples_to_step <= 0.0:
                    self._fire_step()
                    after_even = (self._step % 2) == 1  # swing delays the off-beat 16th
                    self._samples_to_step += step_len * (1.0 + (self.swing if after_even else -self.swing))
                run = min(frames - pos, max(1, int(math.ceil(self._samples_to_step))))
                self._mix_voices(run, mix[pos:pos + run])
                self._samples_to_step -= run
                pos += run
        else:
            self._mix_voices(frames, mix)
        np.multiply(mix, self.master, out=mix)
        np.tanh(mix, out=mix)
        w = self._scope_w
        end = w + frames
        if end <= self.SCOPE_LEN:
            self.scope[w:end] = mix
        else:
            k = self.SCOPE_LEN - w
            self.scope[w:] = mix[:k]
            self.scope[:frames - k] = mix[k:]
        self._scope_w = end % self.SCOPE_LEN
        return mix

    def _callback(self, outdata, frames, time_info, status) -> None:  # noqa: ANN001
        t0 = time.perf_counter()
        if not self._mmcss_done:
            self._stats.mmcss = register_mmcss("Pro Audio")
            self._mmcss_done = True
        st = self._stats
        if status.output_underflow:
            st.underflows += 1
        mix = self.render_block(min(frames, self.MAX_BLOCK))
        outdata[:len(mix), 0] = mix
        outdata[:len(mix), 1] = mix
        if len(mix) < frames:
            outdata[len(mix):] = 0.0
        dt = (time.perf_counter() - t0) * 1000.0
        st.callbacks += 1
        self._cb_sum += dt
        st.cb_avg_ms = self._cb_sum / st.callbacks
        if dt > st.cb_max_ms:
            st.cb_max_ms = dt

    # ------------------------------------------------------------- analysis
    def spectrum(self, bins: int = 64) -> np.ndarray:
        """Log-binned magnitude spectrum (0..1) of the last SCOPE_LEN samples. GUI-side only."""
        w = self._scope_w
        data = np.concatenate((self.scope[w:], self.scope[:w]))
        mag = np.abs(np.fft.rfft(data * np.hanning(len(data)))) / (len(data) / 4)
        edges = np.unique(np.geomspace(2, len(mag) - 1, bins + 1).astype(int))
        out = np.zeros(bins, dtype=np.float32)
        for i in range(min(bins, len(edges) - 1)):
            out[i] = mag[edges[i]:max(edges[i] + 1, edges[i + 1])].max()
        return np.clip(np.log10(out * 20.0 + 1.0), 0.0, 1.0)

    def waveform(self, points: int = 512) -> np.ndarray:
        w = self._scope_w
        data = np.concatenate((self.scope[w:], self.scope[:w]))
        return data[-points * 4::4].copy()


def measure_roundtrip(blocksize: int = 64, seconds: float = 2.0) -> dict[str, Any]:
    """Open the real stream, play a pattern for ``seconds`` and report measured numbers."""
    eng = AudioEngine()
    st = eng.start(blocksize=blocksize)
    if st.mode in ("failed", "stopped"):
        return {"ok": False, "mode": st.mode, "error": st.error}
    for tr, steps in ((0, (0, 4, 8, 12)), (3, tuple(range(0, 16, 2))), (6, (0, 6, 10))):
        for s in steps:
            eng.set_step(tr, s, True)
    eng.play(True)
    time.sleep(seconds)
    st = eng.stats()
    out = {"ok": True, "mode": st.mode, "device": st.device, "samplerate": st.samplerate,
           "blocksize": st.blocksize, "block_ms": round(st.block_ms, 3),
           "reported_output_latency_ms": round(st.reported_latency_ms, 3),
           "callback_avg_ms": round(st.cb_avg_ms, 4), "callback_max_ms": round(st.cb_max_ms, 4),
           "cpu_load_pct": round(st.cpu_load, 2), "underflows": st.underflows,
           "callbacks": st.callbacks, "mmcss": st.mmcss, "fallback_notes": st.error}
    eng.stop()
    return out
