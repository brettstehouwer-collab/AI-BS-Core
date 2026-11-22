"""Automated test suite for Hollywood Screenwriting Studio Step-by-Step Guide & Tool Reference."""

import os
import sys

os.environ["PYTEST_CURRENT_TEST"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.screenwriting_modals import ScreenwritingHelpGuideDialog
from native_studio.screenwriting_view import ScreenwritingNativeView


def run_help_guide_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()

    print("\n═══════════════════════════════════════════════════════════════════════")
    print("▶ RUNNING SCREENWRITING STUDIO STEP-BY-STEP HELP GUIDE VERIFICATION")
    print("═══════════════════════════════════════════════════════════════════════\n")

    # 1. Instantiate ScreenwritingHelpGuideDialog
    dlg = ScreenwritingHelpGuideDialog()
    assert dlg is not None, "Failed to instantiate ScreenwritingHelpGuideDialog"
    assert dlg.windowTitle() == "Universal Screenwriting Studio — Complete Step-by-Step Guide & Tool Reference"
    print("  ✓ ScreenwritingHelpGuideDialog instantiated successfully")

    # 2. Verify all 6 Categories
    assert dlg.list_categories.count() == 6, f"Expected 6 categories, got {dlg.list_categories.count()}"
    cat_titles = [dlg.list_categories.item(i).text() for i in range(dlg.list_categories.count())]
    print(f"  ✓ 6 Guide categories verified: {cat_titles}")
    assert any("8-Step Production Workflow" in c for c in cat_titles)
    assert any("Action Bar" in c for c in cat_titles)
    assert any("5 Dynamic Ribbon Decks" in c for c in cat_titles)
    assert any("Navigation, Sidebar & Layout" in c for c in cat_titles)
    assert any("Keyboard Shortcuts" in c for c in cat_titles)
    assert any("Film Budget" in c for c in cat_titles)

    # 3. Verify total cards populated
    total_cards = len(dlg._all_cards)
    print(f"  ✓ Total indexed tool cards: {total_cards}")
    assert total_cards >= 30, f"Expected at least 30 detailed tool cards, got {total_cards}"

    # 4. Test Live Search Filtering
    test_queries = [
        "Table Read",
        "Alt-Take",
        "Stripboard",
        "DOOD",
        "Zen Mode",
        "50-State",
        "Heading",
        "F1",
    ]
    dlg.show()
    app.processEvents()

    for q in test_queries:
        dlg.txt_search.setText(q)
        matching_cards = [c for c, text, idx in dlg._all_cards if not c.isHidden()]
        print(f"  ✓ Search query '{q}': found {len(matching_cards)} matching cards")
        assert len(matching_cards) >= 1, f"Search for '{q}' returned 0 matches"

    dlg.txt_search.setText("")
    all_visible = [c for c, text, idx in dlg._all_cards if not c.isHidden()]
    assert len(all_visible) == total_cards, "Clearing search should restore all cards"
    print("  ✓ Search clear restores 100% of cards")

    # 5. Verify ScreenwritingNativeView Integration & Button Non-Truncation
    view = ScreenwritingNativeView(bus)
    view.resize(1440, 900)
    view.show()
    app.processEvents()

    assert hasattr(view, "btn_help_guide"), "ScreenwritingNativeView missing btn_help_guide"
    assert view.btn_help_guide.isVisible(), "btn_help_guide not visible"
    text_w = view.btn_help_guide.fontMetrics().horizontalAdvance(view.btn_help_guide.text())
    actual_w = view.btn_help_guide.width()
    min_w = view.btn_help_guide.minimumWidth()
    print(f"  ✓ Button '📖 Help Guide': text_px={text_w} | min_w={min_w} | actual_w={actual_w} (zero truncation guaranteed)")
    assert actual_w >= text_w, "Help Guide button text is truncated"

    # 6. Verify Write Ribbon Deck Help Guide button
    assert "❓ Help Guide" in view._format_buttons, "Write ribbon missing '❓ Help Guide' button"
    print("  ✓ Write ribbon deck has '❓ Help Guide' button")

    # 7. Test triggering guide method
    view._show_screenwriting_guide()
    print("  ✓ view._show_screenwriting_guide() executed cleanly")

    print("\n═══════════════════════════════════════════════════════════════════════")
    print("🎉 ALL SCREENWRITING HELP GUIDE TESTS PASSED 100% PERFECTLY!")
    print("═══════════════════════════════════════════════════════════════════════\n")


def test_screenwriting_help_guide_suite():
    run_help_guide_tests()


if __name__ == "__main__":
    run_help_guide_tests()
