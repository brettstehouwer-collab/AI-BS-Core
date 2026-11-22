"""Phase 3 & Phase 4 Verification Suite: Table Read Studio, Scene Jump, Parity Upgrades & Button Protection."""

import os
import sys

os.environ["PYTEST_CURRENT_TEST"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication, QSizePolicy
from native_studio.engine import EngineBus
from native_studio.screenwriting_modals import (
    parse_screenplay_table_read,
    TableReadStudioDialog,
    TableReadAudioWorker,
)
from native_studio.screenwriting_view import ScreenwritingNativeView
from native_studio.creative_suite_views import BvMediaCreatorNativeView
from native_studio.operations_views import SovereignNdaNativeView
from native_studio.music_daw_view import MusicDawView


SAMPLE_SCRIPT = """Title: The Judge Made Him Go!

FADE IN:

EXT. SUBURBAN NEIGHBORHOOD - DAY

Toby and Tommy play outside their home, a small bungalow.

TOBY
(whispering)
Do you understand why Mom and Dad don't live in the same house?

TOMMY
They fight and argue. It wouldn't be fun living together after that.

INT. SUBURBAN LIVING ROOM - DAY

JESSICA
Remember to behave well for your dad this weekend.

EXT. SUBURBAN STREET - DAY

SAM
Hey boys! Ready for the weekend?
"""


def test_parse_screenplay_table_read():
    data = parse_screenplay_table_read(SAMPLE_SCRIPT)
    cues = data["cues"]
    chars = data["characters"]
    scenes = data["scenes"]

    assert len(cues) >= 7, f"Expected >= 7 cues, got {len(cues)}"
    assert "TOBY" in chars, "TOBY should be detected in characters"
    assert "TOMMY" in chars, "TOMMY should be detected in characters"
    assert "JESSICA" in chars, "JESSICA should be detected in characters"
    assert "SAM" in chars, "SAM should be detected in characters"
    assert "NARRATOR" in chars, "NARRATOR should be detected for action/slugs"
    assert len(scenes) >= 3, f"Expected >= 3 scenes, got {len(scenes)}"

    # Check dialogue parenthetical extraction
    toby_cue = next(c for c in cues if c.get("character") == "TOBY")
    assert toby_cue["parenthetical"] == "(whispering)"
    assert "Mom and Dad" in toby_cue["text"]
    print("✅ test_parse_screenplay_table_read passed!")


def test_table_read_studio_dialog():
    app = QApplication.instance() or QApplication(sys.argv)
    dlg = TableReadStudioDialog(SAMPLE_SCRIPT)

    # Check UI components
    assert dlg.tbl_cast.rowCount() >= 4, "Cast matrix should have >= 4 rows"
    assert dlg.list_teleprompter.count() >= 7, "Teleprompter should have >= 7 items"
    assert dlg.meter_l is not None, "Stereo VU meter Left should exist"
    assert dlg.meter_r is not None, "Stereo VU meter Right should exist"
    assert dlg.btn_play is not None, "Play button should exist"
    assert dlg.btn_export_wav is not None, "Export WAV button should exist"
    assert dlg.chk_continuous.isChecked(), "Continuous read should default to True"
    assert dlg.combo_scene_nav.count() >= 3, "Scene nav dropdown should list scenes"

    # Test seek and highlight
    dlg._highlight_cue(1)
    assert dlg._active_cue_idx == 1 or dlg.list_teleprompter.currentRow() == 1
    assert "NVIDIA" in dlg.pill_mmcss.text() or "MMCSS" in dlg.pill_mmcss.text() or "Audio" in dlg.pill_mmcss.text()

    dlg.close()
    print("✅ test_table_read_studio_dialog passed!")


def test_table_read_audio_worker():
    data = parse_screenplay_table_read(SAMPLE_SCRIPT)
    cast_map = {
        "TOBY": {"voice_idx": 0, "timbre": "Neural Child", "pitch": 6, "rate": 2, "volume": 100},
        "NARRATOR": {"voice_idx": 0, "timbre": "Neutral", "pitch": 0, "rate": 0, "volume": 100},
    }
    worker = TableReadAudioWorker(
        cues=data["cues"][:3],
        cast_map=cast_map,
        start_cue_idx=0,
        continuous=False,
    )
    assert worker.current_idx == 0
    worker.seek_to_cue(2)
    assert worker._seek_target == 2
    worker.set_volume(80)
    assert worker.master_volume == 80
    worker.stop()
    assert not worker._is_running
    print("✅ test_table_read_audio_worker passed!")


def test_screenwriting_scene_jump_and_table_read():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()
    view = ScreenwritingNativeView(bus)

    # Set script
    view.editor.setPlainText(SAMPLE_SCRIPT)
    view._parse_scenes_and_metrics()

    assert len(view._parsed_beats) >= 3, "Expected >= 3 parsed beats"

    # Test scene jump
    first_beat = view._parsed_beats[0]
    view._jump_to_scene_beat(first_beat)

    assert view._current_page == first_beat["page"]
    assert len(view.page_viewer.page_sheets) >= 1, "page_viewer should have rendered sheets"

    # Test table read launch
    dlg = view._launch_table_read()
    assert isinstance(dlg, TableReadStudioDialog)
    assert dlg.tbl_cast.rowCount() >= 4
    dlg.close()
    print("✅ test_screenwriting_scene_jump_and_table_read passed!")


def test_bv_media_creator_5tabs_parity():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()
    view = BvMediaCreatorNativeView(bus)

    assert view.tabs.count() == 5, f"Expected 5 tabs in BvMediaCreator, got {view.tabs.count()}"
    tab_names = [view.tabs.tabText(i) for i in range(5)]
    assert any("Directorial" in t for t in tab_names), "Directorial Guide tab should exist"
    assert any("Canvas" in t for t in tab_names), "Canvas tab should exist"
    assert any("Wan2.1" in t for t in tab_names), "Video Wan2.1 tab should exist"
    assert any("Sound Lab" in t for t in tab_names), "Sound Lab tab should exist"
    assert any("ChromaDB" in t for t in tab_names), "Media Vault tab should exist"

    # Check Demucs faders
    assert len(view._stem_faders) == 4, "4 stem faders (Vocals, Drums, Bass, Other) should exist"
    assert view.tbl_vault.rowCount() >= 6, "Media vault table should have indexed assets"
    print("✅ test_bv_media_creator_5tabs_parity passed!")


def test_sovereign_nda_parity():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()
    view = SovereignNdaNativeView(bus)

    assert view.list_sections.count() == 9, f"Expected 9 section entries, got {view.list_sections.count()}"
    assert "Julie A. Stehouwer" in view.txt_company.text() or "Stehouwer Publishing" in view.txt_company.text()
    assert "SHA256:" in view.lbl_hash.text()
    assert "MASTER SERVICES" in view.txt_nda.toPlainText()
    assert "EXHIBIT A" in view.txt_nda.toPlainText()
    print("✅ test_sovereign_nda_parity passed!")


def test_music_daw_button_protection():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()
    view = MusicDawView(bus)

    # Check Transport buttons
    protected_btns = [
        view.btn_85_suno,
        view.btn_click,
        view.btn_october7,
        view.btn_wave,
        view.btn_copilot,
        view.btn_exp_wav,
        view.btn_exp_mp4,
    ]
    for b in protected_btns:
        text_w = b.fontMetrics().horizontalAdvance(b.text())
        assert b.minimumWidth() >= text_w, f"Button '{b.text()}' minWidth ({b.minimumWidth()}) must be >= text width ({text_w})"

    # Check 9 views buttons
    for key, b in view._view_buttons.items():
        text_w = b.fontMetrics().horizontalAdvance(b.text())
        assert b.minimumWidth() >= text_w, f"View button '{b.text()}' minWidth ({b.minimumWidth()}) must be >= text width ({text_w})"

    print("✅ test_music_daw_button_protection passed!")


if __name__ == "__main__":
    test_parse_screenplay_table_read()
    test_table_read_studio_dialog()
    test_table_read_audio_worker()
    test_screenwriting_scene_jump_and_table_read()
    test_bv_media_creator_5tabs_parity()
    test_sovereign_nda_parity()
    test_music_daw_button_protection()
    print("\n🎉 ALL PHASE 3 & PHASE 4 VERIFICATION TESTS PASSED 100%!")
