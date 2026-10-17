"""Automated pytest test suite for AI-BS Native Studio."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, r"C:\AI-BS")

from native_studio.engine import (
    VAULT_DATABASES,
    EngineBus,
    GpuProbe,
    list_tables,
    probe_ports,
    sample_system,
)
from native_studio.theme import severity_color


def test_system_telemetry():
    data = sample_system()
    assert "cpu_pct" in data
    assert "ram_pct" in data
    assert data["ram_total_gb"] > 0
    assert len(data["disks"]) >= 1


def test_gpu_probe():
    probe = GpuProbe()
    sample = probe.sample()
    assert sample.get("detected") is True
    assert sample.get("temp_c") is not None
    assert sample.get("vram_total_gb") is not None


def test_port_matrix_probe():
    ports = probe_ports()
    assert len(ports) == 25
    assert 11434 in ports
    assert 8080 in ports
    assert 5174 in ports
    assert 8008 in ports
    assert 8055 in ports
    assert 8188 in ports


def test_vault_inspection():
    p = VAULT_DATABASES.get("stehouwer_vault.db")
    if p and p.exists():
        tables = list_tables(p)
        assert len(tables) > 0
        names = [t[0] for t in tables]
        assert "vault_items" in names


def test_engine_bus_execution():
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    res_box = []

    def _worker(val: int):
        return val * 2

    task = bus.submit(_worker, 21, on_result=lambda r: res_box.append(r))
    bus.pool.waitForDone(2000)
    app.processEvents()
    assert 42 in res_box


def test_theme_severity():
    assert severity_color(50.0, warn=70.0, crit=90.0) == "#00f0ff"
    assert severity_color(75.0, warn=70.0, crit=90.0) == "#ff8a00"
    assert severity_color(95.0, warn=70.0, crit=90.0) == "#f43f5e"


def test_trippy_root_wallpaper_toggle():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.app import TrippyRootWidget

    app = QApplication.instance() or QApplication(sys.argv)
    root = TrippyRootWidget()
    assert root.wallpaper_enabled is True
    state = root.toggle_wallpaper()
    assert state is False
    state = root.toggle_wallpaper()
    assert state is True


def test_all_46_subtabs_instantiation():
    print("--> ENTERING test_all_46_subtabs_instantiation", flush=True)
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.app import MainWindow
    from native_studio.navigation_registry import get_all_subtabs_flat

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    print("--> CREATING MainWindow...", flush=True)
    win = MainWindow()
    print("--> MainWindow CREATED!", flush=True)
    assert win is not None
    assert win.trippy_root is not None

    all_tabs = get_all_subtabs_flat()
    assert len(all_tabs) >= 46

    for tab in all_tabs:
        key = tab.key
        print(f"--> Instantiating tab: {key}", flush=True)
        widget = win._get_or_create_subview(key)
        assert widget is not None, f"Failed to instantiate view for subtab: {key}"

    print("--> SHUTTING DOWN HUB & BUS...", flush=True)
    win.hub.shutdown()
    win.bus.shutdown()
    win.close()
    print("--> TEST COMPLETED SUCCESSFULLY!", flush=True)


def test_october7_executable_presence():
    p = Path(r"C:\Program Files\October7_VocalStudio_DAW\October7_VocalStudio_Native.exe")
    assert p.exists(), f"October7_VocalStudio_Native.exe not found at {p}"
    assert p.stat().st_size > 1_000_000, "Executable is unexpectedly small"


def test_screenwriting_and_music_daw_views():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.screenwriting_view import ScreenwritingNativeView
    from native_studio.music_daw_view import MusicDawView
    from native_studio.creative_suite_views import UniversalOmniStudioNativeView

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)

    # Test Screenwriting Studio & Universal Creation Suite
    screen_view = ScreenwritingNativeView(bus)
    assert screen_view.editor is not None
    assert "The Judge Made Him Go!" in screen_view.editor.toPlainText()
    assert screen_view.scene_list is not None
    assert screen_view.scene_list.count() > 0
    assert screen_view.suite_stack.count() == 5
    assert screen_view.video_page is not None
    assert screen_view.comfy_page is not None
    assert screen_view.visual_page is not None
    assert screen_view.lock_page is not None
    
    # Test switching sub-tools
    screen_view._switch_suite_tab("video")
    assert screen_view.suite_stack.currentIndex() == 1
    screen_view._switch_suite_tab("comfy")
    assert screen_view.suite_stack.currentIndex() == 2
    screen_view._switch_suite_tab("visual")
    assert screen_view.suite_stack.currentIndex() == 3
    screen_view._switch_suite_tab("writing")
    assert screen_view.suite_stack.currentIndex() == 0

    # Test Screenwriting view modes (Editor, Page View, Split, Beat Board)
    assert screen_view.view_stack.count() == 4
    screen_view._set_view_mode("page")
    assert screen_view.view_stack.currentIndex() == 1
    screen_view._set_view_mode("split")
    assert screen_view.view_stack.currentIndex() == 2
    screen_view._set_view_mode("beat")
    assert screen_view.view_stack.currentIndex() == 3
    assert screen_view.beat_board._beats is not None
    assert len(screen_view.beat_board._beats) > 0
    screen_view._set_view_mode("editor")
    assert screen_view.view_stack.currentIndex() == 0

    # Test QMenus on dropdown action buttons
    assert screen_view.btn_import.menu() is not None
    assert screen_view.btn_export_fdx.menu() is not None
    assert screen_view.btn_export_pdf.menu() is not None
    assert screen_view.btn_elem.menu() is not None
    assert screen_view.btn_views.menu() is not None
    assert screen_view.btn_prod.menu() is not None

    # Test cross-tool script ingestion into ComfyUI
    screen_view._parse_active_editor_into_comfy()
    assert len(screen_view.comfy_page.scenes) > 0

    # Test Music DAW View
    daw_view = MusicDawView(bus)
    assert daw_view.grid is not None
    assert daw_view.mixer is not None
    assert daw_view.playlist is not None
    assert daw_view.video_monitor is not None
    assert daw_view.btn_october7 is not None

    # Test Universal Omni Broadcast View
    omni_view = UniversalOmniStudioNativeView(bus)
    assert omni_view.txt_telemetry is not None
    assert "NVENC" in omni_view.txt_telemetry.toPlainText()
    assert "October 7 Vocal DAW" in omni_view.txt_telemetry.toPlainText()

    omni_view.shutdown()
    bus.shutdown()


def test_service_orchestrator():
    from native_studio.service_orchestrator import (
        probe_port,
        query_sqlite_vault,
        query_chroma_vectors,
        ensure_comfyui_online,
        ensure_ollama_online,
    )
    # Test socket probing
    assert isinstance(probe_port(11434), bool)
    assert isinstance(probe_port(8189), bool)

    # Test SQLite vault direct query
    records = query_sqlite_vault("media", limit=3)
    assert isinstance(records, list)

    # Test ChromaDB query
    chroma_res = query_chroma_vectors("test", n_results=2)
    assert isinstance(chroma_res, list)


@pytest.fixture(scope="session")
def audit_report():
    import json
    report_file = Path(r"C:\AI-BS\native_studio\comprehensive_audit_report.json")
    if not report_file.exists():
        from native_studio.comprehensive_interactive_audit import run_full_audit
        run_full_audit()
    return json.loads(report_file.read_text(encoding="utf-8"))


def test_audit_verdict_pass(audit_report):
    assert audit_report["verdict"] == "PASS"


def test_audit_zero_unhandled_ui_exceptions(audit_report):
    exceptions = audit_report["ui_verification"]["unhandled_exceptions"]
    assert len(exceptions) == 0, f"Detected UI exceptions: {exceptions}"


def test_audit_widget_discovery_thresholds(audit_report):
    ui = audit_report["ui_verification"]
    counts = ui["counts"]
    assert ui["visited_tab_indices"] >= 46
    assert counts["buttons_discovered"] >= 300
    assert counts["buttons_clicked"] >= 200
    assert counts["line_edits_exercised"] >= 50
    assert counts["combos_exercised"] >= 20
    assert counts["sliders_exercised"] >= 10
    assert counts["checkboxes_exercised"] >= 10


def test_audit_hardware_telemetry_active(audit_report):
    hw = audit_report["hardware_telemetry"]
    gpu = hw["gpu"]
    assert gpu.get("available") is True
    assert "RTX 4090" in gpu.get("name", "")
    assert 0 < gpu.get("temperature_c") <= 85.0
    assert gpu.get("vram_total_mb") >= 24000.0

    cpu = hw["cpu"]
    assert cpu["logical_cores"] >= 16

    ram = hw["ram"]
    assert ram["total_gb"] >= 30.0

    audio = hw["audio_wasapi"]
    assert audio["operational"] is True
    assert audio["active_output_endpoints"] >= 1


def test_audit_daemons_and_ports(audit_report):
    dm = audit_report["daemon_verification"]
    assert dm["ports_online"] >= 10
    http_checks = dm["http_handshakes"]
    assert http_checks.get("FastAPI_Core", {}).get("valid") is True
    assert http_checks.get("Ollama_Primary", {}).get("valid") is True


def test_ecosystem_25_ports():
    from native_studio.engine import PORT_MATRIX
    from native_studio.telemetry_shm import PORT_ORDER
    from backend.aibs_matrix_doctor import ECOSYSTEM_PORTS
    assert len(PORT_MATRIX) == 25
    assert len(PORT_ORDER) == 25
    assert len(ECOSYSTEM_PORTS) == 25
    assert tuple(p for p, _ in PORT_ORDER) == tuple(PORT_MATRIX)
    assert 5174 in PORT_MATRIX
    assert 8008 in PORT_MATRIX
    assert 8055 in PORT_MATRIX
    assert 8188 in PORT_MATRIX


def test_broadcast_stream_engine_specs():
    from native_studio.broadcast_stream_engine import (
        STREAM_PLATFORM_SPECS,
        PING_TEST_TARGETS,
        OUTPUT_RESOLUTION_PRESETS,
        StreamProfileManager,
    )
    assert len(STREAM_PLATFORM_SPECS) >= 6
    for p_name in ["Twitch", "YouTube Live", "Kick", "TikTok Live", "Facebook Live", "Sovereign Broadcast"]:
        assert p_name in STREAM_PLATFORM_SPECS
        spec = STREAM_PLATFORM_SPECS[p_name]
        assert spec["max_video_bitrate_kbps"] >= 6000
        assert spec["keyframe_interval_sec"] in [2.0, 1.0]
        assert "CBR" in spec["rate_control"]

    assert len(PING_TEST_TARGETS) >= 10
    assert len(OUTPUT_RESOLUTION_PRESETS) >= 6

    mgr = StreamProfileManager()
    profiles = mgr.get_profiles()
    assert "twitch_standard" in profiles
    assert "youtube_4k_av1" in profiles
    assert "kick_pro" in profiles
    assert "tiktok_vertical" in profiles


def test_broadcast_canvas_preview_options():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.omni_broadcast_studio import LiveBroadcastCanvas

    app = QApplication.instance() or QApplication(sys.argv)
    canvas = LiveBroadcastCanvas()

    # Test Studio Mode toggle
    assert canvas.studio_mode is False
    canvas.set_studio_mode(True)
    assert canvas.studio_mode is True

    # Test Safe Areas toggle
    canvas.set_safe_areas_enabled(True)
    assert canvas.safe_areas_enabled is True
    canvas.set_safe_areas_enabled(False)
    assert canvas.safe_areas_enabled is False

    # Test Aspect Ratio Presets
    canvas.set_aspect_preset("9:16 Mobile (Shorts / TikTok)")
    assert canvas.orientation == "vertical"
    canvas.set_aspect_preset("16:9 Standard (1080p)")
    assert canvas.orientation == "horizontal"

    # Test Scale Filter
    canvas.set_scale_filter("Lanczos (36-tap Sinc Sharp)")
    assert "Lanczos" in canvas.scale_filter

    # Test FPS Target
    canvas.set_fps_target("59.94 FPS")
    assert canvas.fps_target == "59.94"

    # Test Transitions
    prev = canvas.preview_scene_title
    prog = canvas.program_scene_title
    canvas.trigger_cut_transition()
    assert canvas.preview_scene_title == prog
    assert canvas.program_scene_title == prev

    canvas.shutdown()


def test_multi_rtmp_settings_widget_presets():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.omni_broadcast_studio import MultiRtmpSettingsWidget

    app = QApplication.instance() or QApplication(sys.argv)
    widget = MultiRtmpSettingsWidget()

    # Test Twitch preset
    widget.apply_platform_preset("Twitch")
    assert "6,000" in widget.combo_bitrate.currentText()
    assert widget.chk_tw.isChecked() is True

    # Test YouTube 4K preset
    widget.apply_platform_preset("YouTube Live")
    assert "25,000" in widget.combo_bitrate.currentText()
    assert "AV1" in widget.combo_codec.currentText()
    assert widget.chk_yt.isChecked() is True

    # Test TikTok preset
    widget.apply_platform_preset("TikTok Live")
    assert widget.dest_checkboxes["tiktok"].isChecked() is True

    # Test destinations badges
    assert len(widget.dest_badges) >= 6
    assert "twitch" in widget.dest_badges
    assert "youtube" in widget.dest_badges

    widget.shutdown()


def test_omni_studio_preview_toolbar_and_requirements_dialog():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.omni_broadcast_studio import (
        UniversalOmniStudioNativeView,
        StreamRequirementsDialog,
    )

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)

    omni_view = UniversalOmniStudioNativeView(bus)
    assert hasattr(omni_view, "btn_studio_mode")
    assert hasattr(omni_view, "btn_safe_areas")
    assert hasattr(omni_view, "combo_aspect_preset")
    assert hasattr(omni_view, "combo_scale_filter")
    assert hasattr(omni_view, "combo_fps")

    # Test toggles
    omni_view.btn_studio_mode.setChecked(True)
    assert omni_view.canvas.studio_mode is True

    omni_view.combo_aspect_preset.setCurrentText("9:16 Mobile (Shorts / TikTok)")
    assert omni_view.canvas.orientation == "vertical"

    # Test StreamRequirementsDialog instantiation
    dlg = StreamRequirementsDialog()
    assert dlg.tab_widget.count() == 5
    assert dlg.ping_table is not None
    assert dlg.platform_table is not None

    dlg.close()
    omni_view.shutdown()
    bus.shutdown()


def test_bs_chat_autonomous_host_file_write():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.bs_chat_ide_full import BsChatIdeFullView

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    view = BsChatIdeFullView(bus)
    chunks = []
    view.token_chunk.connect(chunks.append)

    prompt = "write a file to host system then tell me the host file location on my C drive"
    view._is_streaming = True
    view._stream_response("stehouwer_llm", prompt)
    output = "".join(chunks)

    assert "AUTONOMOUS HOST FILE WRITE EXECUTED & VERIFIED" in output
    assert r"C:\AI-BS\exampleFile.txt" in output
    assert os.path.isfile(r"C:\AI-BS\exampleFile.txt")
    assert os.path.getsize(r"C:\AI-BS\exampleFile.txt") > 0
    bus.shutdown()


def test_bs_chat_hyperlink_click_open_in_editor_and_explorer():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QUrl
    from native_studio.engine import EngineBus
    from native_studio.bs_chat_ide_full import BsChatIdeFullView, format_chat_text_to_html

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    view = BsChatIdeFullView(bus)

    # 1. Verify format_chat_text_to_html converts paths and markdown links to clickable anchors
    test_raw = "File created at [C:\\AI-BS\\exampleFile.txt](file:///C:/AI-BS/exampleFile.txt) and C:\\AI-BS\\package.json."
    html_out = format_chat_text_to_html(test_raw)
    assert '<a href="file:///C:/AI-BS/exampleFile.txt"' in html_out
    assert '<a href="file:///C:/AI-BS/package.json"' in html_out

    # 2. Verify clicking anchor in BsChatBrowser emits file_open_requested and opens file in Code Editor
    test_file = r"C:\AI-BS\exampleFile.txt"
    assert os.path.isfile(test_file)
    view.chat_display._on_anchor_clicked(QUrl(f"file:///{test_file.replace(os.sep, '/')}"))

    # Assert split view is opened and code editor has file content
    assert view._split_active is True
    assert view._current_editor_file == test_file
    assert view.code_editor.get_current_file() == test_file
    assert "Hello, this is a host file created by AI-BS" in view.code_editor.toPlainText()

    # 3. Verify Show in Explorer button exists and is connected
    assert hasattr(view, "btn_show_explorer")
    assert view.btn_show_explorer.isEnabled() is True

    bus.shutdown()


def test_bs_chat_natural_language_intent_suite():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.bs_chat_ide_full import BsChatIdeFullView

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    view = BsChatIdeFullView(bus)

    # 1. Setup sample host file
    test_src = r"C:\AI-BS\nl_test_file.txt"
    with open(test_src, "w", encoding="utf-8") as f:
        f.write("Host NL test file content for autonomous rename and delete.\n")

    # 2. Open in editor via natural language
    view._open_file_in_editor(test_src)
    assert view._current_editor_file == test_src
    assert view._last_referenced_file == test_src
    assert view._split_active is True

    # 3. Test natural language rename with pronoun resolution ("re name it testfilbrett")
    handled, msg, should_stop = view._execute_host_intent_standalone("re name it nl_renamed_brett")
    assert handled is True
    assert should_stop is True
    assert "AUTONOMOUS HOST FILE RENAME EXECUTED & VERIFIED" in msg
    expected_dst = r"C:\AI-BS\nl_renamed_brett.txt"
    assert view._current_editor_file == expected_dst
    assert view._last_referenced_file == expected_dst
    assert os.path.isfile(expected_dst)
    assert not os.path.isfile(test_src)

    # 4. Test natural language delete with pronoun resolution ("delete it")
    handled_del, msg_del, should_stop_del = view._execute_host_intent_standalone("delete it")
    assert handled_del is True
    assert should_stop_del is True
    assert "AUTONOMOUS HOST FILE DELETED & VERIFIED" in msg_del
    assert not os.path.isfile(expected_dst)
    assert view._current_editor_file is None

    # 5. Test natural language developer commands without slash commands
    view.chat_display.setPlainText("Some prior chat output...")
    view.input_edit.setText("clear chat")
    view._send()
    assert view.chat_display.toPlainText() == ""

    # Test check vram natural language trigger
    view.input_edit.setText("check vram")
    view._send()
    assert "check vram" in view.chat_display.toPlainText().lower()

    bus.shutdown()


def test_bs_chat_1m_rag_offload_and_budget_expansion():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.bs_chat_ide_full import BsChatIdeFullView

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    view = BsChatIdeFullView(bus)

    # 1. Assert budget bar maximum is expanded to the 1,000,000 max window (1M+ Offload RAG Active)
    assert view.budget_bar.maximum() == 1000000
    assert view.budget_bar.minimum() == 0

    # 2. Assert budget calculations update dynamically with input text
    sample_text = "A" * 400
    view.input_edit.setText(sample_text)
    assert view.budget_bar.value() == 100
    assert "1,000,000 max window" in view.lbl_budget.text()

    # 3. Assert hierarchical semantic chunking divides text with correct overlap
    long_doc = "Paragraph " * 500  # ~5,000 characters
    chunks = view._chunk_text_semantic(long_doc, chunk_size=1000, overlap=200)
    assert len(chunks) >= 5
    for c in chunks:
        assert len(c) <= 1000

    # 4. Assert 1M+ RAG context retrieval connects to vector store and vault gracefully
    rag_ctx = view._retrieve_1m_rag_context("screenplay judge trial", top_k=2)
    assert isinstance(rag_ctx, str)
    # RAG offload queries ChromaDB Port 8001 and SQLite vault without throwing exceptions

    # 5. Assert RAG quick action pills exist and format correctly
    view._insert_slash_command("/rag ")
    assert view.input_edit.text() == "/rag "

    # 6. Test /rag slash command execution
    view._handle_slash_command("/rag test query")
    assert "[CHROMADB 1M+ VECTOR SEARCH]" in view.chat_display.toPlainText()

    # 7. Test natural language trigger without slash command
    view.input_edit.setText("search rag for judge")
    view._send()
    assert "judge" in view.chat_display.toPlainText().lower()

    bus.shutdown()


def test_bs_chat_stage1_stage2_stage3_and_mobile_dpi_parity():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication
    from native_studio.engine import EngineBus
    from native_studio.bs_chat_ide_full import BsChatIdeFullView

    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus(max_threads=2)
    view = BsChatIdeFullView(bus)

    # 1. Stage 1 Auto-Heal toggle
    assert view._auto_heal_enabled is True
    assert "Auto-Heal: ON" in view.btn_auto_heal.text()
    view._toggle_auto_heal()
    assert view._auto_heal_enabled is False
    assert "Auto-Heal: OFF" in view.btn_auto_heal.text()
    view._toggle_auto_heal()
    assert view._auto_heal_enabled is True

    # 2. Mobile Synergy & DPI Scaling Profile selector
    assert view.dpi_picker.count() == 3
    view.dpi_picker.setCurrentIndex(2)  # 1080p @ 150% DPI
    assert view._dpi_profile_id == "mobile_1080p_150"
    assert view._mobile_synergy_active is True
    assert "12.5pt" in view.chat_display.styleSheet()

    # 3. Stage 2 (/blast & /graph) and Stage 3 (/distill) and Mobile (/dpi) slash commands
    view._handle_slash_command("/blast ChatTab.jsx")
    assert "[STAGE 2 BLAST-RADIUS ENGINE]" in view.chat_display.toPlainText()

    view._handle_slash_command("/graph")
    assert "[STAGE 2 AST GRAPH ENGINE]" in view.chat_display.toPlainText()

    view._handle_slash_command("/distill")
    assert "[STAGE 3 SOVEREIGN QLORA DISTILLATION]" in view.chat_display.toPlainText()

    view._handle_slash_command("/dpi 125")
    assert view._dpi_profile_id == "mobile_1440p_125"

    bus.shutdown()
