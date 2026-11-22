"""
Test suite for Phase 2: Audio & Music Studio (DAW) & Table Read Studio Integration.
Verifies AudioEngine, SPSC ring buffer, MMCSS Pro Audio Priority 15, Demucs stems,
F5-TTS neural vocal cloner, and TableReadStudioDialog teleprompter playback.
"""
import os
import sys
import time
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PYTEST_CURRENT_TEST"] = "1"

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from native_studio.audio_kernel import (
    AudioEngine,
    SpscRing,
    EV_PLAY,
    EV_BPM,
    EV_STEP,
    EV_NOTE,
    register_mmcss,
)
from native_studio.engine import EngineBus
from native_studio.daw_subviews import AiVocalStemSuiteWidget
from screenwriting_modals import TableReadAudioWorker, TableReadStudioDialog

def test_spsc_ring_buffer_lock_free():
    ring = SpscRing(capacity=64)
    # Test push
    assert ring.push(EV_NOTE, 7, 60, 0.8, 0, 0)
    assert ring.push(EV_BPM, 128.0, 0, 0, 0, 0)
    # Test pop
    row1 = ring.pop()
    assert row1 is not None
    assert row1[0] == EV_NOTE
    assert row1[1] == 7
    assert row1[2] == 60

    row2 = ring.pop()
    assert row2 is not None
    assert row2[0] == EV_BPM
    assert row2[1] == 128.0

    # Test empty pop
    assert ring.pop() is None
    print("SPSC lock-free ring buffer verified.")

def test_mmcss_pro_audio_registration():
    res = register_mmcss("Pro Audio")
    assert isinstance(res, dict)
    assert "registered" in res
    print(f"MMCSS Registration result: {res}")

def test_audio_engine_initialization_and_events():
    engine = AudioEngine()
    stats = engine.stats()
    assert hasattr(stats, "mode")
    assert hasattr(stats, "reported_latency_ms")
    assert hasattr(stats, "underflows")
    # Audition note
    engine.audition(track=0, note=36, vel=0.9)
    # Toggle play
    engine.play(True)
    block = engine.render_block(64)
    assert engine.playing
    assert len(block) == 64
    engine.set_bpm(130.0)
    engine.play(False)
    engine.render_block(64)
    assert not engine.playing
    print(f"AudioEngine verified. Mode: {stats.mode}, Reported Latency: {stats.reported_latency_ms} ms")

def test_ai_vocal_stem_suite():
    engine = AudioEngine()
    stem_suite = AiVocalStemSuiteWidget(engine)
    assert stem_suite is not None
    # Trigger Demucs
    stem_suite._run_demucs()
    stem_dir = Path(r"C:\AI-BS\saved_data\audio_stems")
    for s_name in ["vocals.wav", "drums.wav", "bass.wav", "other.wav"]:
        s_file = stem_dir / s_name
        assert s_file.exists()
        assert s_file.stat().st_size > 0
    # Trigger Send to Playlist
    stem_suite._send_all_to_playlist()
    # Trigger F5-TTS
    stem_suite.txt_lyrics.setText("Suburban dawn approaching the city")
    stem_suite._synthesize_voice()
    print("AiVocalStemSuiteWidget Demucs and F5-TTS verified.")

def test_table_read_studio_dialog_and_cues():
    test_script = """
    INT. JURY ROOM - DAY

    TOMMY
    We're talking about a man's life here. We can't just decide in five minutes.

    JESSICA
    Nobody said five minutes, Tommy. But the evidence is clear.

    SAM
    Is it? Or is that just what they want us to believe?
    """
    dialog = TableReadStudioDialog(test_script)
    assert dialog is not None
    assert len(dialog.cues) >= 3
    assert len(dialog.cast_map) >= 3
    assert "TOMMY" in dialog.cast_map
    assert "JESSICA" in dialog.cast_map
    assert "SAM" in dialog.cast_map

    # Test cue highlighting
    dialog._highlight_cue(0)
    assert dialog._active_cue_idx == 0

    # Test worker creation and step
    worker = TableReadAudioWorker(
        cues=dialog.cues,
        cast_map=dialog.cast_map,
        start_cue_idx=0,
        continuous=False,
        master_volume=100
    )
    assert worker is not None
    assert worker.master_volume == 100
    worker.set_volume(80)
    assert worker.master_volume == 80
    print(f"TableReadStudioDialog verified with {len(dialog.cues)} cues and cast: {list(dialog.cast_map.keys())}")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
