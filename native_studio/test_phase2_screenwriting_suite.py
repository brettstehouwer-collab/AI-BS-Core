"""Phase 2 Verification Suite: All-States Film Budget, DOOD, Theatrical Budget, Analytics & Page Doctor."""

import os
import sys

os.environ["PYTEST_CURRENT_TEST"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.screenwriting_modals import (
    ALL_STATES_INCENTIVES,
    PageReviewDialog,
    ProductionBreakdownDialog,
    ScriptAnalyticsDialog,
    StagePlayBreakdownDialog,
    parse_screenplay_breakdown,
)
from native_studio.screenwriting_view import ScreenwritingNativeView

SAMPLE_SCRIPT = """Title: The Judge Made Him Go!

FADE IN:

EXT. SUBURBAN NEIGHBORHOOD - DAY

Toby and Tommy play outside their home, a small bungalow.

TOBY
Do you understand why Mom and Dad don't live in the same house?

TOMMY
They fight and argue. It wouldn't be fun living together after that.

INT. SUBURBAN LIVING ROOM - DAY

JESSICA speaks with them before their departure.

JESSICA
Remember to behave well for your dad this weekend.

EXT. SUBURBAN STREET - DAY

Sam arrives in his pickup truck. Toby and Tommy run towards him.

SAM
Hey boys! Ready for the weekend?

EXT. CAMPGROUND ENTRANCE - NIGHT

The pickup pulls into the dark campsite. Suddenly, an EXPLOSION of fireworks fills the sky.

SAM
Watch out!

TOBY
Look at the colors!
"""

import pytest

@pytest.fixture
def app():
    return QApplication.instance() or QApplication(sys.argv)


def test_production_breakdown_dialog(app):
    print("Testing ProductionBreakdownDialog...")
    dlg = ProductionBreakdownDialog(SAMPLE_SCRIPT)
    dlg.show()
    app.processEvents()

    # 1. Verify All-States database coverage
    assert len(ALL_STATES_INCENTIVES) >= 45, f"Expected >=45 states/territories, got {len(ALL_STATES_INCENTIVES)}"
    state_codes = [s["code"] for s in ALL_STATES_INCENTIVES]
    for required in ["GA", "CA", "NM", "NY", "NJ", "LA", "IL", "TX", "MA", "OK", "UT", "UK", "CA_FED", "AU"]:
        assert required in state_codes, f"Required state/territory {required} missing from database"

    # 2. Verify state selector dropdown
    assert dlg.combo_state.count() == len(ALL_STATES_INCENTIVES)

    # 3. Verify Georgia 30% calculation
    dlg.combo_state.setCurrentIndex(state_codes.index("GA"))
    dlg.chk_uplift.setChecked(True)
    app.processEvents()
    assert "Georgia" in dlg.lbl_b_state.text()
    assert "30%" in dlg.lbl_b_rate.text()
    top_gross = dlg._calc_data["top_sheet"]["gross"]
    expected_tax_credit = top_gross * 0.30
    expected_net = top_gross - expected_tax_credit
    assert f"-${expected_tax_credit:,.2f}" in dlg.lbl_b_credit.text()
    assert f"${expected_net:,.2f}" in dlg.lbl_b_net.text()

    # 4. Verify California 45% calculation
    dlg.combo_state.setCurrentIndex(state_codes.index("CA"))
    app.processEvents()
    assert "California" in dlg.lbl_b_state.text()
    assert "45%" in dlg.lbl_b_rate.text()

    # 5. Verify all 4 Tabs have data
    assert dlg.tabs.count() == 4
    # Tab 1: Stripboard has days
    assert dlg.schedule_lay.count() >= 1
    # Tab 2: Script Breakdown has scenes
    assert dlg.table_breakdown.rowCount() >= 4
    # Tab 3: DOOD table has cast rows
    assert dlg.table_dood.rowCount() >= 3
    # Tab 4: Top sheet budget has account rows
    assert dlg.table_budget.rowCount() == 7

    dlg.close()
    print("  ✅ ProductionBreakdownDialog passed 100%!")


def test_stageplay_breakdown_dialog(app):
    print("Testing StagePlayBreakdownDialog...")
    dlg = StagePlayBreakdownDialog(SAMPLE_SCRIPT)
    dlg.show()
    app.processEvents()

    assert dlg.tabs.count() == 3
    assert dlg.table_cap.rowCount() == 6
    assert dlg.table_weekly.rowCount() == 5
    assert len(dlg.txt_recoupment.toPlainText()) > 100
    assert "RECOUPMENT TIMELINE" in dlg.txt_recoupment.toPlainText()

    dlg.close()
    print("  ✅ StagePlayBreakdownDialog passed 100%!")


def test_script_analytics_dialog(app):
    print("Testing ScriptAnalyticsDialog...")
    dlg = ScriptAnalyticsDialog(SAMPLE_SCRIPT)
    dlg.show()
    app.processEvents()

    data = parse_screenplay_breakdown(SAMPLE_SCRIPT)
    assert len(data["scenes"]) >= 4
    assert "Toby" in data["character_counts"]
    assert "Tommy" in data["character_counts"]
    assert "Sam" in data["character_counts"]

    dlg.close()
    print("  ✅ ScriptAnalyticsDialog passed 100%!")


def test_page_review_dialog(app):
    print("Testing PageReviewDialog...")
    applied_data = {}

    def _apply_cb(p_num, proofed_text, next_p):
        applied_data["p_num"] = p_num
        applied_data["text"] = proofed_text
        applied_data["next_p"] = next_p

    dlg = PageReviewDialog(1, 10, "INT SUBURBAN LIVING ROOM - DAY\njessica speaks.\n", on_apply=_apply_cb)
    dlg.show()
    app.processEvents()

    assert dlg.txt_orig.toPlainText().startswith("INT SUBURBAN")
    assert "INT. SUBURBAN" in dlg.txt_proof.toPlainText()  # Formatted with period

    dlg._apply_and_close(next_page=False)
    assert applied_data.get("p_num") == 1
    assert "INT. SUBURBAN" in applied_data.get("text", "")

    dlg.close()
    print("  ✅ PageReviewDialog passed 100%!")


def test_screenwriting_native_view_integration(app):
    print("Testing ScreenwritingNativeView Phase 2 modal integration...")
    bus = EngineBus()
    view = ScreenwritingNativeView(bus)
    view.resize(1366, 768)
    view.show()
    app.processEvents()

    # Verify buttons are wired and callable without errors
    view._show_telemetry_dialog()
    view._show_production_cms_dialog()
    view._show_stageplay_breakdown_dialog()
    view._review_active_page()

    view.close()
    bus.shutdown()
    print("  ✅ ScreenwritingNativeView Phase 2 integration passed 100%!")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    test_production_breakdown_dialog(app)
    test_stageplay_breakdown_dialog(app)
    test_script_analytics_dialog(app)
    test_page_review_dialog(app)
    test_screenwriting_native_view_integration(app)
    print("\n🎉 ALL PHASE 2 VERIFICATION TESTS PASSED 100% PERFECTLY!")


if __name__ == "__main__":
    main()
