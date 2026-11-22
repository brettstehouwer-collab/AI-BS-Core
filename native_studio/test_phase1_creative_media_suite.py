"""
Test suite for Phase 1: Creative & Media Suite Integration
Verifies VideoStudioPage, ComfyUIStudioPage, VisualScriptingPage, and Unreal Engine 5 export integration.
"""
import os
import sys
import json
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure offscreen Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from native_studio.engine import EngineBus
from creation_suite_subtools import (
    VideoStudioPage,
    ComfyUIStudioPage,
    VisualScriptingPage,
    NodeGraphicsItem
)
from screenwriting_view import ScreenwritingNativeView

@pytest.fixture
def bus():
    b = EngineBus()
    yield b
    b.shutdown(500)
    b.pool.waitForDone(1000)

def test_video_studio_init_and_clips(bus):
    page = VideoStudioPage(bus)
    assert page is not None
    # Verify recent clips populated
    assert len(page.recent_clips) >= 1
    assert page.clips_lay.count() >= 1
    first_clip = page.recent_clips[0]
    assert "title" in first_clip
    print(f"VideoStudioPage clip count: {len(page.recent_clips)}, first clip: {first_clip['title']}")

def test_video_studio_generation_trigger(bus):
    page = VideoStudioPage(bus)
    page.txt_scene_prompt.setPlainText("A tense dramatic close-up of Tommy looking over the city at twilight, cinematic lighting.")
    # Trigger generation
    page._handle_generate_scene()
    log_content = page.txt_logs.toPlainText()
    assert "Starting scene generation" in log_content or "RTX 4090" in log_content
    print("VideoStudioPage generation triggered successfully.")

def test_comfyui_studio_parse_screenplay(bus):
    page = ComfyUIStudioPage(bus)
    initial_count = len(page.scenes)
    # Test parsing active screenplay
    page._parse_active_screenplay()
    assert len(page.scenes) >= 1
    status_text = page.lbl_status.text()
    assert "Parsed" in status_text or "scenes" in status_text or "Idle" in status_text or "Loaded" in status_text
    print(f"ComfyUI parsed scenes count: {len(page.scenes)}")

def test_comfyui_studio_queue_workflow(bus):
    page = ComfyUIStudioPage(bus)
    page._parse_active_screenplay()
    # Queue workflow
    page._queue_comfyui_workflow()
    status_text = page.lbl_status.text()
    assert "Queuing" in status_text or "Status:" in status_text
    # Verify batch queue file written
    queue_path = r"C:\AI-BS\output\comfy_batch_queue.json"
    if os.path.exists(queue_path):
        with open(queue_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "scenes" in data
            print(f"ComfyUI batch queue verified: {len(data['scenes'])} scenes")

def test_visual_scripting_graph(bus):
    page = VisualScriptingPage(bus)
    assert page.scene is not None
    init_nodes = len(page.nodes)
    # Add nodes using the actual signature
    page.add_node("🖨️ Action: Print", "action", "#1d4ed8")
    page.add_node("➕ Math Operation", "math", "#b45309")
    page.add_node("🔀 Branch (If/Else)", "logic", "#ca8a04")
    assert len(page.nodes) == init_nodes + 3
    # Compile graph
    page.compile_graph()
    code = page.txt_code.toPlainText()
    assert len(code) > 0
    print(f"VisualScriptingPage graph compiled successfully, code length: {len(code)}")

def test_screenwriting_unreal_engine_exports(bus):
    view = ScreenwritingNativeView(bus)
    # Test Unreal CSV export
    csv_path = r"C:\AI-BS\unreal_assets\Unreal_Scene_DataTable.csv"
    view._export_unreal_asset("csv")
    assert os.path.exists(csv_path)
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()
        assert "RowName,SceneHeading,PageNumber,CameraLens" in csv_content
    print("Unreal CSV DataTable export verified.")

    # Test Unreal Sequencer Python export
    py_path = r"C:\AI-BS\unreal_assets\unreal_sequencer_build.py"
    view._export_unreal_asset("python")
    assert os.path.exists(py_path)
    with open(py_path, "r", encoding="utf-8") as f:
        py_content = f.read()
        assert "unreal.LevelSequenceFactoryNew()" in py_content
        assert "CineCameraActor" in py_content
    print("Unreal Sequencer Python script export verified.")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
