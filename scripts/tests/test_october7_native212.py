"""Synthetic offline regressions; AST extraction never imports/starts the DAW."""
import ast
import math
import os
import threading
import time
import uuid
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest
import soundfile as sf
from scipy import signal

SOURCE = Path(__file__).resolve().parents[2] / "October7_VocalStudio_DAW" / "source" / "app_native.py"


@pytest.fixture
def native(tmp_path):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"), filename=str(SOURCE))
    names = {"SPSCRingBuffer", "RealtimeVocalDSPChain", "VST3HostManager", "NativeStudioEngine", "RecordingCapture"}
    bodies = [n for n in tree.body if (isinstance(n, ast.ClassDef) and n.name in names)
              or (isinstance(n, ast.FunctionDef) and n.name == "mix_tracks_block")]
    env = dict(np=np, math=math, signal=signal, threading=threading, time=time, os=os,
               uuid=uuid, Path=Path, Optional=Optional, Dict=Dict, List=List, Tuple=Tuple,
               sf=sf, BASE_DIR=tmp_path, DATA_DIR=tmp_path, json=json,
               __name__="isolated_october7_definitions")
    # No application imports, module top-level code, UI construction or sounddevice access.
    exec(compile(ast.Module(body=bodies, type_ignores=[]), str(SOURCE), "exec"), env)
    gui = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MasterStudioMainWindow")
    for name in ("toggle_rec", "_export_master_mix_wav", "_export_stems_wav"):
        node = next(n for n in gui.body if isinstance(n, ast.FunctionDef) and n.name == name)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), env)
    messages = []
    env["QMessageBox"] = SimpleNamespace(information=lambda *args: messages.append(("info", args)),
                                          warning=lambda *args: messages.append(("warning", args)),
                                          critical=lambda *args: messages.append(("critical", args)))
    env["QFileDialog"] = SimpleNamespace(getSaveFileName=lambda *_: (str(tmp_path / "mix.wav"), "WAV"),
                                          getExistingDirectory=lambda *_: str(tmp_path))
    env["messages"] = messages
    yield env


def engine_without_devices(native):
    engine = native["NativeStudioEngine"]()
    engine._feeder_running = False
    engine._feeder_thread.join(timeout=1)
    engine.dsp_chain = SimpleNamespace(process_block=lambda samples: samples)
    engine.vst3_manager = SimpleNamespace(process=lambda samples: samples)
    engine.is_running = True
    engine.input_available = True  # Synthetic capability; never opens a real device.
    return engine


def record_window(engine):
    button = SimpleNamespace(setText=lambda *_: None, setStyleSheet=lambda *_: None)
    return SimpleNamespace(engine=engine, btn_rec=button,
                           toggle_play=lambda: setattr(engine, "is_playing", True))


@pytest.mark.parametrize("seconds", [15, 60])
def test_long_recording_retains_every_frame(native, seconds):
    engine = engine_without_devices(native)
    window = record_window(engine)
    try:
        native["toggle_rec"](window)
        block = np.full((128, 1), 0.125, dtype=np.float32)
        out = np.zeros((128, 2), dtype=np.float32)
        for idx in range(seconds * 48000 // 128):
            engine._audio_callback(block, out, 128, None, None)
            if idx % 64 == 0:
                time.sleep(0.001)  # Let the non-audio writer run, without real-time/device waits.
        native["toggle_rec"](window)
        files = list((native["BASE_DIR"] / "takes").glob("*.wav"))
        assert len(files) == 1
        assert sf.info(files[0]).frames == seconds * 48000
    finally:
        engine.stop()


def test_nonloop_eof_does_not_discard_buffered_audio(native):
    engine = engine_without_devices(native)
    engine.tracks = {"one": dict(audio=np.full(48000, 0.2, np.float32), gain=1.0, pan=0.0, mute=False, solo=False)}
    engine.is_looping = False
    engine.is_playing = True
    engine._feeder_running = True
    sleeps = 0
    def bounded_sleep(_):
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 30 or not engine.is_playing:
            engine._feeder_running = False
    native["time"] = SimpleNamespace(sleep=bounded_sleep)
    engine._playback_feeder_worker()
    assert engine.playback_ring.read_available() >= 48000
    assert engine.is_playing, "Producer EOF must not stop the consumer while audio remains queued"


@pytest.mark.parametrize("method", ["_export_stems_wav", "_export_master_mix_wav"])
def test_exports_write_actual_wav_without_undefined_capability_flag(native, method):
    engine = SimpleNamespace(sample_rate=48000, tracks={"one": dict(audio=np.full(128, .1, np.float32), gain=1., pan=0., mute=False, solo=False)})
    native[method](SimpleNamespace(engine=engine))
    files = list(native["BASE_DIR"].glob("*.wav"))
    assert len(files) == 1
    assert sf.info(files[0]).frames == 128


def test_master_export_matches_live_pan_and_solo(native):
    # Supplying the old missing flag isolates the second independent export failure.
    native["HAS_SOUNDFILE"] = True
    tracks = {"left_solo": dict(audio=np.full(128, .25, np.float32), gain=1., pan=-1., mute=False, solo=True),
              "excluded": dict(audio=np.full(128, .25, np.float32), gain=1., pan=1., mute=False, solo=False)}
    native["_export_master_mix_wav"](SimpleNamespace(engine=SimpleNamespace(sample_rate=48000, tracks=tracks)))
    data, rate = sf.read(native["BASE_DIR"] / "mix.wav", dtype="float32", always_2d=True)
    assert rate == 48000
    np.testing.assert_allclose(data[:, 0], .25, atol=1 / 32768)
    np.testing.assert_allclose(data[:, 1], 0, atol=1 / 32768)


def test_live_mixer_honors_solo(native):
    engine = engine_without_devices(native)
    engine.tracks = {"silent_solo": dict(audio=np.zeros(2048, np.float32), gain=1., pan=0., mute=False, solo=True),
                     "excluded": dict(audio=np.full(2048, .2, np.float32), gain=1., pan=0., mute=False, solo=False)}
    engine.is_playing = True
    engine.is_looping = False
    engine._feeder_running = True
    native["time"] = SimpleNamespace(sleep=lambda _: setattr(engine, "_feeder_running", False))
    engine._playback_feeder_worker()
    out = np.zeros((2048, 2), np.float32)
    engine.playback_ring.read(out, len(out))
    assert not np.any(out)


def test_consumer_stops_only_after_last_queued_sample(native):
    engine = engine_without_devices(native)
    engine.playback_ring.write(np.full((100, 2), .2, np.float32))
    engine._playback_eof = True
    engine.is_playing = True
    out = np.zeros((64, 2), np.float32)
    engine._audio_callback(np.zeros((64, 1), np.float32), out, 64, None, None)
    assert engine.is_playing and engine.play_pos_samples == 64
    engine._audio_callback(np.zeros((64, 1), np.float32), out, 64, None, None)
    assert not engine.is_playing and engine.play_pos_samples == 100
    np.testing.assert_allclose(out[:36], .2)
    assert not np.any(out[36:])


def test_capture_overflow_is_explicit_and_stops_accepting(native):
    ring = native["SPSCRingBuffer"](9, 1)
    capture = native["RecordingCapture"](ring, 48000, native["BASE_DIR"], "test.wav")
    capture.accepting = True  # Deliberately stalled non-audio writer.
    assert capture.write(np.ones((16, 1), np.float32)) == 8
    assert capture.dropped_frames == 8
    assert "overflow" in capture.error.lower()
    assert not capture.accepting and capture._stop.is_set()
    assert capture.write(np.ones((16, 1), np.float32)) == 0
    assert ring.read_available() == 8


def test_write_failure_keeps_original_take_and_recovery_samples(native):
    class FailingWav:
        def __init__(self, *args, **kwargs):
            self.file = sf.SoundFile(*args, **kwargs)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.file.close()
        def write(self, _):
            raise OSError("synthetic disk failure")
        def flush(self):
            self.file.flush()
    native["sf"] = SimpleNamespace(SoundFile=FailingWav)
    engine = engine_without_devices(native)
    original = np.full(100, .4, np.float32)
    engine.tracks["Lead Vocal"]["audio"] = original
    window = record_window(engine)
    try:
        native["toggle_rec"](window)
        capture = engine._take_capture
        samples = np.full((128, 1), .123456, np.float32)
        engine._audio_callback(samples, np.zeros((128, 2), np.float32), 128, None, None)
        capture._thread.join(timeout=3)
        native["toggle_rec"](window)
        assert "synthetic disk failure" in engine.record_error
        assert engine._take_capture is capture
        assert capture.temp_path.exists()
        assert engine.tracks["Lead Vocal"]["audio"] is original
        np.testing.assert_array_equal(capture.pending_audio, samples)
        assert not any(kind == "info" for kind, _ in native["messages"])
    finally:
        engine.stop()


def test_two_takes_in_same_second_never_overwrite(native):
    engine = engine_without_devices(native)
    native["time"] = SimpleNamespace(strftime=lambda _: "same_second")
    try:
        paths = []
        for level in (.1, .2):
            assert engine.begin_recording()
            engine._audio_callback(np.full((128, 1), level, np.float32), np.zeros((128, 2), np.float32), 128, None, None)
            paths.append(engine.save_recorded_take("same_second.wav"))
        assert paths[0] != paths[1]
        for path, level in zip(paths, (.1, .2)):
            data, _ = sf.read(path, dtype="float32")
            np.testing.assert_allclose(data, level)
    finally:
        engine.stop()


def test_finalize_failure_preserves_complete_recovery_file_and_previous_take(native, monkeypatch):
    engine = engine_without_devices(native)
    original = np.full(100, .4, np.float32)
    engine.tracks["Lead Vocal"]["audio"] = original
    assert engine.begin_recording()
    capture = engine._take_capture
    engine._audio_callback(np.full((128, 1), .123456, np.float32), np.zeros((128, 2), np.float32), 128, None, None)
    rename = Path.rename
    def fail_commit(path, target):
        if path == capture.temp_path:
            raise OSError("synthetic rename denied")
        return rename(path, target)
    monkeypatch.setattr(Path, "rename", fail_commit)
    try:
        assert engine.save_recorded_take("ignored.wav") is None
        assert "synthetic rename denied" in engine.record_error
        assert engine._take_capture is capture
        assert engine.tracks["Lead Vocal"]["audio"] is original
        data, _ = sf.read(capture.temp_path, dtype="float32")
        np.testing.assert_allclose(data, .123456)
        assert not capture.final_path.exists()
        assert not engine.begin_recording(), "A new session must not clear unrecovered samples"
    finally:
        engine.stop()


@pytest.mark.parametrize("method", ["_export_stems_wav", "_export_master_mix_wav"])
def test_export_write_failure_never_reports_success(native, method):
    def fail(*_):
        raise OSError("synthetic unwritable destination")
    native["sf"] = SimpleNamespace(write=fail)
    engine = SimpleNamespace(sample_rate=48000, tracks={"one": dict(audio=np.ones(128, np.float32), gain=1., pan=0., mute=False, solo=False)})
    native[method](SimpleNamespace(engine=engine))
    assert native["messages"] and all(kind == "warning" for kind, _ in native["messages"])
    assert not list(native["BASE_DIR"].glob("*.wav"))


def test_recording_requires_an_explicitly_enabled_input(native):
    engine = engine_without_devices(native)
    engine.is_running = False
    engine.input_available = False
    try:
        assert not engine.begin_recording()
        assert not list(native["BASE_DIR"].rglob("*.wav"))
    finally:
        engine.stop()


def test_recording_uses_armed_track_and_preserves_raw_input(native):
    engine = engine_without_devices(native)
    engine.tracks["Lead Vocal"]["armed"] = False
    engine.tracks["Harmonies"]["armed"] = True
    original_lead = np.full(100, .7, np.float32)
    engine.tracks["Lead Vocal"]["audio"] = original_lead
    engine.dsp_chain = SimpleNamespace(process_block=lambda samples: samples * .1)
    engine.vst3_manager = SimpleNamespace(process=lambda samples: samples * .3)
    engine.play_pos_samples = 48000
    window = record_window(engine)
    try:
        native["toggle_rec"](window)
        # A later arm change must not reroute a take already in progress.
        engine.tracks["Harmonies"]["armed"] = False
        engine.tracks["Double (L)"]["armed"] = True
        engine._audio_callback(np.full((128, 1), .123456, np.float32), np.zeros((128, 2), np.float32), 128, None, None)
        native["toggle_rec"](window)
        assert engine.tracks["Lead Vocal"]["audio"] is original_lead
        data = engine.tracks["Harmonies"]["audio"]
        np.testing.assert_allclose(data.reshape(-1), .123456)
        assert engine.tracks["Harmonies"]["start_sample"] == 48000
        assert engine.tracks["Harmonies"]["takes"][-1]["start_sample"] == 48000
    finally:
        engine.stop()


@pytest.mark.parametrize("armed_count", [0, 2])
def test_record_start_rejects_ambiguous_arming_before_creating_audio(native, armed_count):
    engine = engine_without_devices(native)
    for idx, track in enumerate(engine.tracks.values()):
        track["armed"] = idx < armed_count
    try:
        assert not engine.begin_recording()
        assert not list(native["BASE_DIR"].rglob("*.wav"))
    finally:
        engine.stop()


def test_clip_start_is_respected_in_live_and_export_mix(native):
    tracks = {"verse": dict(audio=np.full(128, .25, np.float32), start_sample=48000,
                            gain=1., pan=-1., mute=False, solo=False)}
    assert not np.any(native["mix_tracks_block"](tracks, 0, 128))
    later = native["mix_tracks_block"](tracks, 48000, 128)
    np.testing.assert_allclose(later[:, 0], .25)
    native["_export_master_mix_wav"](SimpleNamespace(engine=SimpleNamespace(sample_rate=48000, tracks=tracks)))
    data, _ = sf.read(native["BASE_DIR"] / "mix.wav", dtype="float32", always_2d=True)
    assert len(data) == 48128
    assert not np.any(data[:48000])
    np.testing.assert_allclose(data[48000:, 0], .25, atol=1/32768)


def test_session_round_trip_preserves_clip_mix_and_history_without_devices(native):
    source = native["BASE_DIR"] / "synthetic.wav"
    sf.write(source, np.full(128, .25, np.float32), 48000, subtype="FLOAT")
    engine = engine_without_devices(native)
    engine.load_track_file("Harmonies", str(source))
    track = engine.tracks["Harmonies"]
    track.update(start_sample=96000, gain=.33, pan=-.75, mute=True, solo=True,
                 takes=[dict(path=str(source), start_sample=96000, frames=128)])
    assert engine.save_session()
    # A later save must retain the byte-exact earlier session as a history record.
    before = engine.project_path.read_bytes()
    track["gain"] = .44
    assert engine.save_session()
    assert before in [path.read_bytes() for path in engine.project_path.parent.rglob("*.json")]
    engine.stop()
    restored = engine_without_devices(native)
    try:
        track = restored.tracks["Harmonies"]
        assert restored.session_loaded
        assert (track["start_sample"], track["gain"], track["pan"], track["mute"], track["solo"]) == (96000, .44, -.75, True, True)
        assert track["takes"][-1]["path"] == str(source)
        np.testing.assert_allclose(track["audio"], .25)
    finally:
        restored.stop()


def test_main_does_not_elevate_or_activate_audio():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n.func for n in ast.walk(main) if isinstance(n, ast.Call)]
    assert not any(isinstance(n, ast.Name) and n.id == "elevate_to_admin" for n in calls)
    assert not any(isinstance(n, ast.Attribute) and n.attr == "start" and isinstance(n.value, ast.Name) and n.value.id == "engine" for n in calls)


def test_corrupt_session_is_not_overwritten_on_shutdown(native):
    path = native["BASE_DIR"] / "projects/default/session.json"
    path.parent.mkdir(parents=True)
    original = b'{"schema_version": 1, broken original evidence'
    path.write_bytes(original)
    engine = engine_without_devices(native)
    assert engine.project_error
    engine.stop()
    assert path.read_bytes() == original


def test_failed_project_commit_retains_previous_assignment_and_new_raw_file(native):
    source = native["BASE_DIR"] / "previous.wav"
    sf.write(source, np.full(128, .7, np.float32), 48000, subtype="FLOAT")
    engine = engine_without_devices(native)
    engine.load_track_file("Lead Vocal", str(source))
    assert engine.save_session()
    original = engine.tracks["Lead Vocal"]["audio"]
    before = engine.project_path.read_bytes()
    assert engine.begin_recording()
    engine._audio_callback(np.full((128, 1), .123456, np.float32), np.zeros((128, 2), np.float32), 128, None, None)
    saved = engine.save_recorded_take("ignored.wav")
    def deny(*_):
        raise PermissionError("synthetic project commit denied")
    native["os"] = SimpleNamespace(fsync=os.fsync, replace=deny)
    try:
        assert not engine.commit_recorded_take(saved)
        assert engine.tracks["Lead Vocal"]["audio"] is original
        assert engine.project_path.read_bytes() == before
        assert Path(saved).exists()
        assert "synthetic project commit denied" in engine.record_error
    finally:
        engine.stop()


def test_zero_frame_stop_allows_fresh_recording_without_deleting_evidence(native):
    engine = engine_without_devices(native)
    try:
        assert engine.begin_recording()
        empty_path = engine._take_capture.temp_path
        assert engine.save_recorded_take("empty.wav") is None
        assert empty_path.exists()
        assert engine.begin_recording(), "An empty stopped take must not trap the recorder in an unrecoverable state"
    finally:
        engine.stop()


def test_exported_stem_keeps_its_timeline_position(native):
    track = dict(audio=np.full(128, .25, np.float32), start_sample=48000,
                 gain=1., pan=0., mute=False, solo=False)
    native["_export_stems_wav"](SimpleNamespace(engine=SimpleNamespace(sample_rate=48000, tracks={"verse": track})))
    data, _ = sf.read(native["BASE_DIR"] / "verse_stem.wav", dtype="float32")
    assert len(data) == 48128
    assert not np.any(data[:48000])
    np.testing.assert_allclose(data[48000:], .25, atol=1/32768)
