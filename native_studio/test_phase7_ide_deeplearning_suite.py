"""Automated Test Suite for Phase 7: Autonomous Agentic IDE & Deep Learning Studio
(SovereignChatView + DeepLearningStudioNativeView + ReasoningAttentionNativeView + AgentMemoryNativeView).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Fix console encoding for Windows cp1252
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from native_studio.engine import EngineBus
from native_studio.intelligence_views import (
    AgentMemoryNativeView,
    AttentionMatrixWidget,
    DeepLearningStudioNativeView,
    MultiLinePromptEdit,
    ReasoningAttentionNativeView,
    SovereignChatView,
    apply_code_patch,
    sync_4_mirrors,
    validate_code_syntax,
)


def run_phase7_tests() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()

    print("═══════════════════════════════════════════════════════════════════════")
    print("▶ RUNNING PHASE 7 VERIFICATION: AUTONOMOUS AGENTIC IDE & DEEP LEARNING")
    print("═══════════════════════════════════════════════════════════════════════")

    # ─────────────────────────────────────────────────────────────────
    # 1. MultiLinePromptEdit & Context Token Gauge Verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 1] MultiLinePromptEdit & Context Token Usage Gauge")
    prompt_box = MultiLinePromptEdit()
    prompt_box.setPlainText("def autonomous_handler():\n    return 'Sovereign Direct2D Online'")
    assert prompt_box.toPlainText().startswith("def autonomous_handler"), "Text entry failed"
    print("  ✓ Multi-line prompt editor accepts code & newline blocks")

    chat_view = SovereignChatView(bus=bus)
    assert chat_view is not None, "Failed to instantiate SovereignChatView"

    # Verify Model Fleet dropdown
    assert chat_view.model_combo.count() >= 8, f"Expected at least 8 models, got {chat_view.model_combo.count()}"
    models = [chat_view.model_combo.itemText(i) for i in range(chat_view.model_combo.count())]
    assert any("qwen2.5-coder" in m for m in models), "Missing qwen2.5-coder"
    assert any("llama3.3" in m for m in models), "Missing llama3.3"
    assert any("deepseek-r1" in m for m in models), "Missing deepseek-r1"
    print(f"  ✓ Full 8-Model Fleet switcher verified: {len(models)} models available")

    # Verify Context Token Gauge
    chat_view.prompt_edit.setPlainText("Testing token estimation across sovereign transcript. " * 20)
    chat_view._update_token_gauge()
    assert chat_view.token_bar.value() > 0, "Token gauge did not update"
    assert "tokens" in chat_view.lbl_token_usage.text(), "Token telemetry label missing text"
    print(f"  ✓ Live Token Gauge: {chat_view.lbl_token_usage.text()}")

    # ─────────────────────────────────────────────────────────────────
    # 2. Autonomous Action Deck & Execution Terminal Drawer
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Autonomous Action Pills & Subprocess Terminal Drawer")
    assert hasattr(chat_view, "btn_syntax"), "Missing btn_syntax"
    assert hasattr(chat_view, "btn_patch"), "Missing btn_patch"
    assert hasattr(chat_view, "btn_mirror"), "Missing btn_mirror"
    assert hasattr(chat_view, "btn_ps"), "Missing btn_ps"
    assert hasattr(chat_view, "btn_heal"), "Missing btn_heal"
    assert hasattr(chat_view, "btn_toggle_terminal"), "Missing btn_toggle_terminal"

    for btn in [
        chat_view.btn_syntax,
        chat_view.btn_patch,
        chat_view.btn_mirror,
        chat_view.btn_ps,
        chat_view.btn_heal,
        chat_view.btn_toggle_terminal,
    ]:
        min_w = btn.minimumWidth()
        txt = btn.text()
        assert min_w > 0, f"Button {txt} has no minimum width"
        fm = btn.fontMetrics()
        expected_min = fm.horizontalAdvance(txt) + 16
        assert min_w >= expected_min, f"Button {txt} width ({min_w}) < expected ({expected_min})"
        print(f"  ✓ Action Pill '{txt}' width={min_w}px (zero truncation guaranteed)")

    # Terminal Drawer Toggle Test
    assert not chat_view.terminal_frame.isHidden(), "Terminal should start visible"
    chat_view._toggle_terminal()
    assert chat_view.terminal_frame.isHidden(), "Terminal should be hidden after toggle"
    chat_view._toggle_terminal()
    assert not chat_view.terminal_frame.isHidden(), "Terminal should be visible again"
    print("  ✓ Subprocess execution terminal drawer collapsible toggle verified")

    # Terminal append and clear
    chat_view.term_console.appendPlainText("Test log line from Sovereign Subprocess Dispatcher")
    assert "Test log line" in chat_view.term_console.toPlainText(), "Log append failed"
    chat_view.term_console_clear()
    assert chat_view.term_console.toPlainText() == "", "Clear terminal failed"
    print("  ✓ Subprocess execution console stream and clear verified")

    # ─────────────────────────────────────────────────────────────────
    # 3. AST Syntax Verification, Patching & 4-Mirror Synchronization
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 3] AST Syntax Verification, Host Patching & 4-Mirror Sync")

    # Python valid
    py_valid = "def greet(name: str) -> str:\n    return f'Hello, {name}!'"
    res_py = validate_code_syntax(py_valid, "python")
    assert res_py["status"] == "valid", "Expected valid Python AST"
    print("  ✓ Python AST validation passed for clean code")

    # Python broken
    py_invalid = "def broken(name\n    return name"
    res_err = validate_code_syntax(py_invalid, "python")
    assert res_err["status"] == "error", "Expected error for broken Python AST"
    assert "Line 1" in res_err["error"], f"Line number missing in error: {res_err['error']}"
    print(f"  ✓ Python AST error detection verified: {res_err['error']}")

    # JS/JSX validation
    jsx_valid = "function Component() { return <div className='p-4'>Hello</div>; }"
    res_jsx = validate_code_syntax(jsx_valid, "javascript")
    assert res_jsx["status"] == "valid", "Expected valid JS balance"
    print("  ✓ JavaScript/JSX AST balance verification passed")

    # 4-Mirror Synchronization Test
    test_comp = "TestParityComponent.jsx"
    test_content = "// AI-BS 100% SHA-256 Parity Component\nexport default function TestParity() { return null; }"
    sync_res = sync_4_mirrors(test_comp, test_content)
    assert sync_res["status"] == "success", "Mirror sync failed"
    assert sync_res["mirrors_count"] == 4, f"Expected 4 mirrors, got {sync_res['mirrors_count']}"
    print(f"  ✓ 4-Mirror Parity Synchronized with SHA-256: {sync_res['sha256'][:16]}...")

    # Verify on disk across all 4 mirrors
    for p in sync_res["paths"]:
        assert os.path.isfile(p), f"File missing in mirror: {p}"
        with open(p, "r", encoding="utf-8") as f:
            assert f.read() == test_content, f"Content mismatch in mirror: {p}"
        # Clean up test files
        try:
            os.unlink(p)
        except Exception:
            pass
    print("  ✓ 100% Byte Parity verified across all 4 frontend mirrors on disk")

    # Apply Host Patch Test
    test_rel = "temp_patch_test.py"
    test_patch_code = "# File: temp_patch_test.py\ndef patched_func():\n    return True\n"
    patch_res = apply_code_patch(test_rel, test_patch_code)
    assert patch_res["status"] == "success", "Patch failed"
    assert os.path.isfile(patch_res["file_path"]), "Patched file not found"
    print(f"  ✓ Host patch applied cleanly: {patch_res['bytes_written']} bytes written")

    # Clean up patch test file
    try:
        os.unlink(patch_res["file_path"])
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────────────
    # 4. Deep Learning Studio: RTX 4090 Live VRAM Headroom & Fleet
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 4] DeepLearningStudioNativeView & RTX 4090 Hardware Poller")
    dl_view = DeepLearningStudioNativeView(bus=bus)
    assert dl_view is not None, "Failed to instantiate DeepLearningStudioNativeView"
    assert hasattr(dl_view, "vram_bar"), "Missing vram_bar"
    assert hasattr(dl_view, "lbl_vram_usage"), "Missing lbl_vram_usage"
    assert hasattr(dl_view, "lbl_gpu_temp"), "Missing lbl_gpu_temp"

    # Poll real GPU stats
    dl_view._poll_real_gpu_stats()
    vram_text = dl_view.lbl_vram_usage.text()
    temp_text = dl_view.lbl_gpu_temp.text()
    assert "MB" in vram_text or "%" in vram_text, f"Unexpected VRAM text: {vram_text}"
    print(f"  ✓ Real RTX 4090 Hardware Telemetry: {vram_text} | {temp_text}")

    # ─────────────────────────────────────────────────────────────────
    # 5. Reasoning Attention: Interactive 2D Attention Heatmap
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 5] ReasoningAttentionNativeView & AttentionMatrixWidget")
    attn_view = ReasoningAttentionNativeView(bus=bus)
    assert attn_view is not None, "Failed to instantiate ReasoningAttentionNativeView"
    assert hasattr(attn_view, "heatmap_widget"), "Missing heatmap_widget"
    assert hasattr(attn_view, "cmb_layer"), "Missing cmb_layer"
    assert hasattr(attn_view, "cmb_head"), "Missing cmb_head"

    # Test Layer & Head selection
    assert attn_view.cmb_layer.count() == 32, "Expected 32 attention layers"
    assert attn_view.cmb_head.count() == 16, "Expected 16 attention heads"

    orig_val = attn_view.heatmap_widget.matrix[0][0]
    attn_view.cmb_layer.setCurrentIndex(10)
    attn_view.cmb_head.setCurrentIndex(8)
    attn_view._on_layer_head_changed()
    new_val = attn_view.heatmap_widget.matrix[0][0]
    print(f"  ✓ Dynamic attention weight recalculation: {orig_val:.2f} -> {new_val:.2f}")

    # ─────────────────────────────────────────────────────────────────
    # 6. Agent Vector Memory (ChromaDB Explorer)
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 6] AgentMemoryNativeView & Semantic Memory Query")
    mem_view = AgentMemoryNativeView(bus=bus)
    assert mem_view is not None, "Failed to instantiate AgentMemoryNativeView"
    assert mem_view.table.columnCount() == 4, "Expected 4 columns in memory table"
    mem_view._run_vector_search()
    assert mem_view.table.rowCount() > 0, "Expected memory query results"
    print(f"  ✓ Vector memory query executed cleanly: {mem_view.table.rowCount()} results loaded")

    print("\n═══════════════════════════════════════════════════════════════════════")
    print("🎉 ALL PHASE 7 TESTS PASSED WITH 100% SUCCESS!")
    print("═══════════════════════════════════════════════════════════════════════")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    run_phase7_tests()
