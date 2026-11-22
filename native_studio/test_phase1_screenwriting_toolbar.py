"""Phase 1 Verification Suite: Screenwriting Studio Multi-Row Header, Zero-Truncation Toolbar & 5-Deck Dynamic Ribbon."""

import os
import sys

os.environ["PYTEST_CURRENT_TEST"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.screenwriting_view import ScreenwritingNativeView


def run_phase1_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    bus = EngineBus()
    view = ScreenwritingNativeView(bus)
    view.resize(1440, 900)
    view.show()
    app.processEvents()

    # 1. Verify separate header_ribbon_bar and act_bar
    assert hasattr(view, "header_ribbon_bar") and view.header_ribbon_bar.isVisible(), "header_ribbon_bar missing"
    assert hasattr(view, "act_bar") and view.act_bar.isVisible(), "act_bar missing"
    assert hasattr(view, "ribbon_bar") and view.ribbon_bar.isVisible(), "ribbon_bar missing"

    # 2. Verify zero text truncation on all primary action pills and ribbon switcher tabs
    critical_buttons = [
        view.btn_new_proj,
        view.btn_zen,
        view.btn_novelize,
        view.btn_table_read,
        view.btn_telemetry,
        view.btn_import,
        view.btn_find,
        view.btn_export_fdx,
        view.btn_export_pdf,
        view.btn_save,
        view.btn_write,
        view.btn_elem,
        view.btn_views,
        view.btn_previs,
        view.btn_prod,
    ]
    for btn in critical_buttons:
        text_w = btn.fontMetrics().horizontalAdvance(btn.text())
        actual_w = btn.width()
        min_w = btn.minimumWidth()
        print(f"  [Button Check] {btn.text():32s} | text_px={text_w:3d} | min_w={min_w:3d} | actual_w={actual_w:3d}")
        assert actual_w >= text_w, f"Button truncated: {btn.text()} (actual={actual_w}, text={text_w})"

    # 3. Verify 5-Deck Dynamic Contextual Ribbon Switching
    assert view.ribbon_stack.count() == 5, f"Expected 5 ribbon decks, got {view.ribbon_stack.count()}"
    assert view.ribbon_stack.currentIndex() == 0, "Default ribbon deck should be 0 (Write)"

    view.btn_elem.click()
    app.processEvents()
    assert view.ribbon_stack.currentIndex() == 1, "Elements tab should switch ribbon_stack to index 1"

    view.btn_views.click()
    app.processEvents()
    assert view.ribbon_stack.currentIndex() == 2, "Views & Split tab should switch ribbon_stack to index 2"

    view.btn_previs.click()
    app.processEvents()
    assert view.ribbon_stack.currentIndex() == 3, "3D & Previs tab should switch ribbon_stack to index 3"
    assert view.btn_send_video.isVisible()
    assert view.btn_export_unreal_csv.isVisible()
    assert view.btn_export_unreal_py.isVisible()

    view.btn_prod.click()
    app.processEvents()
    assert view.ribbon_stack.currentIndex() == 4, "Production & CMS tab should switch ribbon_stack to index 4"
    prod_buttons = [
        view.btn_prod_char_vault,
        view.btn_prod_coverage,
        view.btn_prod_analytics,
        view.btn_prod_film_budget,
        view.btn_prod_stage_budget,
        view.btn_revision_toggle,
        view.btn_prod_title_page,
        view.btn_prod_fdx,
        view.btn_prod_pdf,
        view.btn_prod_publish_cms,
    ]
    for pb in prod_buttons:
        assert pb.isVisible(), f"Production ribbon button not visible: {pb.text()}"

    # 4. Verify Revision Mode Toggle & Color Selector
    assert not view.combo_revision_color.isVisible()
    view.btn_revision_toggle.click()
    app.processEvents()
    assert "Revision ON" in view.btn_revision_toggle.text()
    assert view.combo_revision_color.isVisible()

    # 5. Verify Inline Find & Replace Toggle
    assert not view.find_replace_bar.isVisible()
    view.btn_find.click()
    app.processEvents()
    assert view.find_replace_bar.isVisible()

    view.close()
    bus.shutdown()
    print("\n✅ ALL PHASE 1 SCREENWRITING TOOLBAR & 5-DECK RIBBON TESTS PASSED!")


if __name__ == "__main__":
    run_phase1_tests()
