"""Automated Test Suite for Phase 6: Omni-Broadcast Studio Toolbar Non-Truncation
& Sovereign Business Email Suite (EmailClientNativeView + ComposeEmailDialog).
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
from PyQt6.QtWidgets import QApplication, QScrollArea

from native_studio.engine import EngineBus
from native_studio.omni_broadcast_studio import UniversalOmniStudioNativeView
from native_studio.email_client_view import (
    ComposeEmailDialog,
    EmailClientNativeView,
    _apply_safe_button,
    _format_size,
    _load_cached_emails,
)


def run_phase6_tests() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()

    print("═══════════════════════════════════════════════════════════════════════")
    print("▶ RUNNING PHASE 6 VERIFICATION: OMNI-BROADCAST & EMAIL CLIENT SUITE")
    print("═══════════════════════════════════════════════════════════════════════")

    # ─────────────────────────────────────────────────────────────────
    # 1. Omni-Broadcast Studio Verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 1] UniversalOmniStudioNativeView Toolbar Non-Truncation & Controls")
    studio = UniversalOmniStudioNativeView(bus=bus)
    assert studio is not None, "Failed to instantiate UniversalOmniStudioNativeView"

    # Check that Action Trigger Bar is wrapped in a QScrollArea
    act_scrolls = [w for w in studio.findChildren(QScrollArea) if w.height() == 48]
    assert len(act_scrolls) >= 1, "Expected action trigger QScrollArea of height 48px"
    print("  ✓ Action trigger bar is safely housed in horizontal QScrollArea (h=48)")

    # Check that Preview Control Bar is wrapped in a QScrollArea
    prev_scrolls = [w for w in studio.findChildren(QScrollArea) if w.height() == 40]
    assert len(prev_scrolls) >= 1, "Expected preview control QScrollArea of height 40px"
    print("  ✓ Preview control toolbar is safely housed in horizontal QScrollArea (h=40)")

    # Verify buttons exist and have non-truncating minimum widths
    assert hasattr(studio, "btn_october7"), "Missing btn_october7"
    assert hasattr(studio, "btn_stream"), "Missing btn_stream"
    assert hasattr(studio, "btn_record"), "Missing btn_record"
    assert hasattr(studio, "btn_obs"), "Missing btn_obs"
    assert hasattr(studio, "btn_orientation"), "Missing btn_orientation"
    assert hasattr(studio, "btn_studio_mode"), "Missing btn_studio_mode"
    assert hasattr(studio, "btn_safe_areas"), "Missing btn_safe_areas"

    for btn in [
        studio.btn_october7,
        studio.btn_stream,
        studio.btn_record,
        studio.btn_obs,
        studio.btn_orientation,
        studio.btn_studio_mode,
        studio.btn_safe_areas,
    ]:
        min_w = btn.minimumWidth()
        txt = btn.text()
        assert min_w > 0, f"Button {txt} has no minimum width"
        fm = btn.fontMetrics()
        expected_min = fm.horizontalAdvance(txt) + 20
        assert min_w >= expected_min, f"Button {txt} minimum width ({min_w}) < expected ({expected_min})"
        print(f"  ✓ Button '{txt}' width={min_w}px (zero truncation guaranteed)")

    # Verify Combos
    assert studio.combo_aspect_preset.count() >= 4, "Missing aspect ratio presets"
    assert studio.combo_scale_filter.count() >= 3, "Missing scale filters"
    assert studio.combo_fps.count() >= 4, "Missing FPS presets"
    print("  ✓ Video presets verified (Aspect, Filter, FPS all configured)")

    # ─────────────────────────────────────────────────────────────────
    # 2. Sovereign Business Email Suite (EmailClientNativeView)
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 2] EmailClientNativeView Initialization & Dynamic Badges")
    email_view = EmailClientNativeView(bus=bus)
    assert email_view is not None, "Failed to instantiate EmailClientNativeView"
    assert len(email_view._emails) >= 4, "Expected seeded cached emails"
    print(f"  ✓ Initialized with {len(email_view._emails)} cached emails")

    # Check dynamic folder count badges
    inbox_btn = email_view.folder_btns["Inbox"][0]
    starred_btn = email_view.folder_btns["Starred"][0]
    sent_btn = email_view.folder_btns["Sent"][0]
    trash_btn = email_view.folder_btns["Trash"][0]

    print(f"  ✓ Inbox button: '{inbox_btn.text()}'")
    print(f"  ✓ Starred button: '{starred_btn.text()}'")
    print(f"  ✓ Sent button: '{sent_btn.text()}'")
    print(f"  ✓ Trash button: '{trash_btn.text()}'")

    assert "(" in inbox_btn.text() or inbox_btn.text() == "📥 Inbox", "Inbox badge missing"
    assert "(" in starred_btn.text() or starred_btn.text() == "⭐ Starred", "Starred badge missing"

    # Category Chips
    assert len(email_view.category_btns) == 5, "Expected 5 category chips"
    for cat in ["All", "Primary", "Promotions", "Updates", "Social"]:
        assert cat in email_view.category_btns, f"Missing category button {cat}"
    print("  ✓ 5 Category filter chips verified (All, Primary, Promotions, Updates, Social)")

    # Selection & Reader Verification
    email_view._set_folder("Inbox")
    assert email_view.email_list.count() > 0, "Expected inbox items"
    email_view.email_list.setCurrentRow(0)
    sel = email_view._selected_email
    assert sel is not None, "No email selected"
    print(f"  ✓ Selected email: '{sel.get('subject')}' from {sel.get('sender')}")

    # Reader labels
    assert email_view.lbl_msg_sub.text() == sel.get("subject"), "Subject mismatch"
    assert "From:" in email_view.lbl_msg_sender.text(), "Sender mismatch"
    assert len(email_view.txt_msg_body.toPlainText()) > 0, "Body empty"
    print("  ✓ Reader header and body synchronized")

    # Star / Unstar Toggle
    orig_starred = sel.get("starred", False)
    email_view._toggle_star()
    assert sel.get("starred") != orig_starred, "Star toggle failed"
    print(f"  ✓ Star toggle verified: new starred state = {sel.get('starred')}")
    # Toggle back
    email_view._toggle_star()
    assert sel.get("starred") == orig_starred, "Star toggle back failed"

    # Read / Unread Toggle
    orig_read = sel.get("read", True)
    email_view._toggle_read()
    assert sel.get("read") != orig_read, "Read toggle failed"
    print(f"  ✓ Read toggle verified: new read state = {sel.get('read')}")
    email_view._toggle_read()

    # Move to Trash and Restore
    target_em = sel
    email_view._trash_or_restore()
    assert target_em.get("folder") == "Trash", "Move to trash failed"
    print("  ✓ Move to trash verified")

    # To restore, switch to Trash folder and click restore
    email_view._set_folder("Trash")
    assert email_view.email_list.count() > 0, "Expected trash items"
    email_view._selected_email = target_em
    email_view._trash_or_restore()
    assert target_em.get("folder") == "Inbox", "Restore to inbox failed"
    print("  ✓ Restore from trash verified")
    email_view._set_folder("Inbox")

    # AI Tone Selector
    assert email_view.combo_ai_tone.count() == 4, "Expected 4 AI tones"
    tones = [email_view.combo_ai_tone.itemText(i) for i in range(4)]
    assert any("Professional" in t for t in tones), "Missing Professional tone"
    assert any("Contract Approval" in t for t in tones), "Missing Contract Approval tone"
    assert any("Revision Request" in t for t in tones), "Missing Revision Request tone"
    assert any("Quick Acknowledgment" in t for t in tones), "Missing Quick Acknowledgment tone"
    print(f"  ✓ Stehouwer AI Tones verified: {', '.join(tones)}")

    # ─────────────────────────────────────────────────────────────────
    # 3. ComposeEmailDialog & Attachment Manager Verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST 3] ComposeEmailDialog, Attachments Manager & Forwarding")

    # Test standard compose
    dlg = ComposeEmailDialog(parent=email_view)
    assert dlg.txt_to is not None, "Missing txt_to"
    assert dlg.txt_sub is not None, "Missing txt_sub"
    assert dlg.txt_body is not None, "Missing txt_body"
    assert dlg.btn_send.minimumWidth() >= 120, "Send button minimum width too small"

    # Test Cc/Bcc Toggle
    assert dlg.frame_cc_bcc.isHidden(), "Cc/Bcc should start hidden"
    dlg._toggle_cc_bcc()
    assert not dlg.frame_cc_bcc.isHidden(), "Cc/Bcc should not be hidden after toggle"
    print("  ✓ Collapsible Cc/Bcc drawer verified")

    # Test Attachments Manager
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp1, \
         tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp2:
        tmp1.write(b"PDF document payload" * 100)
        tmp1.flush()
        tmp2.write(b"PNG image payload" * 50)
        tmp2.flush()
        p1 = Path(tmp1.name)
        p2 = Path(tmp2.name)

    try:
        dlg._attachments.append({
            "name": p1.name,
            "path": str(p1),
            "size_bytes": p1.stat().st_size,
            "size_str": _format_size(p1.stat().st_size),
        })
        dlg._attachments.append({
            "name": p2.name,
            "path": str(p2),
            "size_bytes": p2.stat().st_size,
            "size_str": _format_size(p2.stat().st_size),
        })
        dlg._refresh_attachment_chips()

        assert not dlg.attachments_container.isHidden(), "Attachment container should not be hidden"
        assert "2 files attached" in dlg.lbl_attachments_status.text(), f"Unexpected status: {dlg.lbl_attachments_status.text()}"
        print(f"  ✓ Attachment status verified: {dlg.lbl_attachments_status.text()}")

        # Remove 1 attachment
        dlg._remove_attachment(str(p1))
        assert len(dlg._attachments) == 1, "Failed to remove attachment"
        assert "1 file attached" in dlg.lbl_attachments_status.text(), "Failed to update status after removal"
        print("  ✓ Attachment chip deletion and counter recalculation verified")
    finally:
        if p1.exists():
            os.unlink(p1)
        if p2.exists():
            os.unlink(p2)

    # Test Forwarding Action
    sample_email = {
        "id": "em_test_fwd",
        "sender": "Producer Partner",
        "email": "partner@hollywood.com",
        "account": "brett@stehouwer-publishing.com",
        "subject": "Co-Production Agreement Ratification",
        "body": "Here are the terms for the upcoming feature film.",
        "date": "Oct 17, 2026",
        "time": "02:30 PM",
    }
    fwd_dlg = ComposeEmailDialog(parent=email_view, forward_from=sample_email)
    assert fwd_dlg.txt_sub.text().startswith("Fwd: Co-Production"), f"Subject not forwarded: {fwd_dlg.txt_sub.text()}"
    assert fwd_dlg.txt_to.text() == "", "Forward recipient should be empty for user input"
    assert "---------- Forwarded message ---------" in fwd_dlg.txt_body.toPlainText(), "Missing forward banner in body"
    assert "From: Producer Partner <partner@hollywood.com>" in fwd_dlg.txt_body.toPlainText(), "Missing forward header in body"
    print("  ✓ Forward action verified (Fwd: prefix, cleared recipient, standardized quote banner)")

    # Test AI Draft Prefill
    draft_body = "Hi Producer,\n\nReceived and acknowledged. Everything looks solid."
    ai_dlg = ComposeEmailDialog(parent=email_view, reply_to=sample_email, prefill_body=draft_body)
    assert ai_dlg.txt_sub.text().startswith("Re: Co-Production"), "Reply subject failed"
    assert ai_dlg.txt_to.text() == "partner@hollywood.com", "Reply recipient failed"
    assert "Received and acknowledged" in ai_dlg.txt_body.toPlainText(), "Draft text missing"
    print("  ✓ AI Draft pre-fill verified")

    print("\n═══════════════════════════════════════════════════════════════════════")
    print("🎉 ALL PHASE 6 TESTS PASSED WITH 100% SUCCESS!")
    print("═══════════════════════════════════════════════════════════════════════")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    run_phase6_tests()
