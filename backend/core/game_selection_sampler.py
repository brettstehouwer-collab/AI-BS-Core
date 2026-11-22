"""One owned discovery worker and nonblocking, expiring capture decisions.

Filesystem/OS discovery runs only in the worker. Video writers and control
handlers consume cached immutable evidence; they never join a discovery call.
A stuck filesystem operation cannot be forcibly cancelled in Python. stop()
therefore has a bounded wait, reports unconfirmed cleanup, retains ownership of
the same worker, and never starts a replacement thread behind the caller's back.
"""
from __future__ import annotations

from dataclasses import replace
from itertools import islice
import math
import threading
import time

from backend.core.game_capture_selection import (
    MAX_WINDOWS, ManualSource, ProcessIdentity, SelectionDecision,
    WindowEvidence, WindowsGameAdapter,
)

_UNSET = object()
_REASONS = frozenset({
    'VERIFIED_GAME','MANUAL_SCREEN','MANUAL_WINDOW','MANUAL_SOURCE_UNAVAILABLE',
    'NO_VERIFIED_GAME','EVIDENCE_LIMIT_EXCEEDED','INVALID_WINDOW_EVIDENCE',
    'WINDOW_EVIDENCE_UNAVAILABLE',
})


def _number(value, minimum, maximum, message):
    if (type(value) not in (int,float) or not math.isfinite(value)
            or not minimum <= value <= maximum):
        raise ValueError(message)
    return float(value)


def _intent_key(manual, approved_game):
    if manual is not None and not isinstance(manual,ManualSource):
        raise ValueError('A verified manual source is required')
    if approved_game is not None and not isinstance(approved_game,ProcessIdentity):
        raise ValueError('An approved game process identity is required')
    manual_key = None if manual is None else (
        manual.window.source_key if manual.kind=='window' else ('screen',manual.screen_id))
    process_key = None if approved_game is None else (
        approved_game.pid,approved_game.create_time,approved_game.exe)
    return manual_key,process_key


class GameSelectionSampler:
    def __init__(self,adapter=None,*,interval=.5,max_age=2.,clock=time.monotonic):
        self._interval = _number(interval,.01,5.,'Discovery interval exceeds bounds')
        self._max_age = _number(max_age,.05,10.,'Evidence age exceeds bounds')
        if not callable(clock):raise ValueError('A monotonic clock is required')
        self._adapter = WindowsGameAdapter() if adapter is None else adapter
        if not callable(getattr(self._adapter,'decide',None)):
            raise ValueError('A discovery adapter is required')
        self._clock = clock; self._lock = threading.RLock()
        self._wake = threading.Event(); self._stop = threading.Event()
        self._thread = None; self._closed = False
        self._manual = None; self._approved_game = None; self._intent_key = (None,None)
        self._generation = 0; self._published_generation = None
        self._decision = None; self._sampled_at = None; self._previous = None
        self._windows = (); self._windows_at = None
        self._samples_completed = 0; self._max_clock = None

    def _now(self):
        value = self._clock()
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Monotonic clock unavailable')
        with self._lock:
            if self._max_clock is not None and value < self._max_clock:
                raise ValueError('Monotonic clock moved backwards')
            self._max_clock = value
        return float(value)

    def start(self) -> bool:
        """Start exactly one worker. A stopped sampler cannot be restarted."""
        with self._lock:
            if self._closed:return False
            if self._thread is not None:return self._thread.is_alive()
            worker = threading.Thread(target=self._run,name='AI-BS-Game-Discovery',daemon=True)
            self._thread = worker
            try:worker.start()
            except Exception:
                self._closed = True; self._stop.set()
                raise
            return True

    def set_intent(self,*,manual=_UNSET,approved_game=_UNSET):
        """Change intent without OS/filesystem work; None explicitly releases it."""
        with self._lock:
            next_manual = self._manual if manual is _UNSET else manual
            next_approved = self._approved_game if approved_game is _UNSET else approved_game
            key = _intent_key(next_manual,next_approved)
            if self._closed:return False
            if key == self._intent_key:return True
            self._manual = next_manual; self._approved_game = next_approved; self._intent_key = key
            self._generation += 1; self._decision = None; self._sampled_at = None
            self._published_generation = None; self._previous = None
            self._wake.set()
            return True

    def _holding(self,reason):
        return SelectionDecision(None,reason,True,self._manual is not None,manual_source=self._manual)

    def latest(self,*,manual=_UNSET,approved_game=_UNSET,previous=None) -> SelectionDecision:
        """Immediate cache read. No discovery, thread join, queue or lock-held I/O."""
        if manual is not _UNSET or approved_game is not _UNSET:
            self.set_intent(manual=manual,approved_game=approved_game)
        try:now = self._now()
        except Exception:
            with self._lock:return self._holding('SAMPLER_CLOCK_UNAVAILABLE')
        with self._lock:
            if self._closed:return self._holding('SAMPLER_STOPPED')
            if self._thread is None:return self._holding('SAMPLER_NOT_STARTED')
            if self._decision is None or self._published_generation != self._generation:
                return self._holding('SAMPLER_INTENT_PENDING')
            if self._sampled_at is None or not 0 <= now-self._sampled_at < self._max_age:
                return self._holding('SAMPLER_STALE')
            result = self._decision
            old_key = previous.source_key if isinstance(previous,(SelectionDecision,WindowEvidence)) else None
            return replace(result,must_clear=result.source is None or result.source_key!=old_key)

    def resolve_window(self,hwnd,pid,title) -> WindowEvidence | None:
        """Resolve frontend HWND/PID/raw title against fresh server OS evidence.

        Frontend executable paths and process start times are never trusted.
        A source not present in this cache stays held until fresh discovery.
        """
        if (type(hwnd) is not int or hwnd<=0 or type(pid) is not int or pid<=0
                or type(title) is not str or not title):return None
        try:now = self._now()
        except Exception:return None
        with self._lock:
            if (self._closed or self._windows_at is None
                    or not 0 <= now-self._windows_at < self._max_age):return None
            matches = [w for w in self._windows if w.hwnd==hwnd and w.process.pid==pid
                       and w.title==title and w.visible and not w.minimized and w.width>0 and w.height>0]
            # Conflicting duplicate evidence never chooses an arbitrary identity.
            return matches[0] if len(matches)==1 else None

    def _run(self):
        while not self._stop.is_set():
            with self._lock:
                generation = self._generation; manual = self._manual
                approved = self._approved_game; previous = self._previous
            sampled_at = None; windows = ()
            try:
                sampled_at = self._now()
                result = self._adapter.decide(manual=manual,approved_game=approved,previous=previous)
                if (not isinstance(result,SelectionDecision) or result.reason not in _REASONS
                        or type(result.manual) is not bool or type(result.must_clear) is not bool
                        or (result.source is not None and not isinstance(result.source,WindowEvidence))
                        or result.manual != (manual is not None)):
                    raise ValueError('Invalid discovery result')
                if manual is not None:
                    if manual.kind=='screen' and result.source is not None:
                        raise ValueError('A manual screen cannot fall back to a window')
                    if (manual.kind=='window' and result.source is not None
                            and result.source_key!=manual.window.source_key):
                        raise ValueError('The manual window identity changed')
                    result = replace(result,manual_source=manual)
                windows = tuple(islice(getattr(self._adapter,'cached_windows',()),MAX_WINDOWS+1))
                if len(windows)>MAX_WINDOWS or any(not isinstance(w,WindowEvidence) for w in windows):
                    windows = ()
            except Exception:
                result = SelectionDecision(None,'SAMPLER_EVIDENCE_UNAVAILABLE',True,
                                           manual is not None,manual_source=manual)
                windows = ()
            with self._lock:
                if self._stop.is_set():break
                if generation != self._generation:
                    # A newer explicit sharing intent invalidates in-flight work.
                    continue
                self._decision = result; self._sampled_at = sampled_at
                self._published_generation = generation; self._previous = result
                self._windows = windows; self._windows_at = sampled_at
                self._samples_completed += 1
            self._wake.wait(self._interval); self._wake.clear()

    def status(self) -> dict:
        """Fixed numeric/lifecycle fields only; no titles, paths or exception text."""
        with self._lock:
            return {'worker_alive':self._thread is not None and self._thread.is_alive(),
                    'stopped':self._closed,'intent_generation':self._generation,
                    'samples_completed':self._samples_completed,'max_age_seconds':self._max_age,
                    'cleanup_confirmed':self._closed and (self._thread is None or not self._thread.is_alive())}

    def stop(self,timeout=.5) -> bool:
        timeout = _number(timeout,0.,5.,'Sampler stop deadline exceeds bounds')
        with self._lock:
            self._closed = True; self._stop.set(); self._wake.set()
            self._decision = None; self._sampled_at = None; self._previous = None
            self._windows = (); self._windows_at = None; worker = self._thread
        if worker is None:return True
        if worker is threading.current_thread():return False
        worker.join(timeout)
        return not worker.is_alive()
