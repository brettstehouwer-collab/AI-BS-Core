"""Comprehensive Verification Suite for Phase 5:
- Master Accounting & Money Track Native View (Schedule C, MI 4.25% tax engine, AI Copilot)
- Steam Gaming Hub Native View (Direct Valve ACF manifest bridge, NVMe footprint, Game Mode Governor)
- Clinical Nutrition & Detox Engine View (5-serving formulations, keto snacks, refeeding protocol)
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QLabel

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


app = QApplication.instance() or QApplication(sys.argv[:1])

from native_studio.engine import EngineBus
from native_studio.accounting_view import MasterAccountingNativeView, EditTransactionDialog
from native_studio.steam_gaming_view import SteamGamingNativeView
from native_studio.nutrition_view import NutritionNativeView, JUICE_SCHEDULE, KETO_SNACKS, RAW_PROTOCOL_PAYLOAD


bus = EngineBus()


def test_master_accounting_ledger_and_tax_suite():
    print("Testing MasterAccountingNativeView...")
    view = MasterAccountingNativeView(bus)
    assert view is not None
    assert len(view._all_rows) > 0, f"Expected verified rows in ledger, got {len(view._all_rows)}"

    # Check HUD Cards
    assert view.card_income is not None
    assert view.card_expense is not None
    assert view.card_mi_tax is not None
    assert view.card_tax_savings is not None

    # Check Tax Summary Math
    summary = view._tax_summary
    assert "gross_income" in summary
    assert "estimated_michigan_state_tax" in summary
    assert "estimated_federal_se_tax" in summary
    assert "quarterly_payment" in summary

    # Verify Michigan 4.25% State Flat Tax calculation
    expected_mi_tax = round(summary["net_taxable_income"] * 0.0425, 2)
    assert abs(summary["estimated_michigan_state_tax"] - expected_mi_tax) < 0.05

    # Verify Subpage Switching
    view._set_subpage(1)
    assert view.stacked.currentIndex() == 1
    view._set_subpage(0)
    assert view.stacked.currentIndex() == 0

    # Verify AI Copilot Drawer Toggle
    assert view.ai_drawer.isHidden()
    view._toggle_ai_drawer()
    assert not view.ai_drawer.isHidden()
    view._toggle_ai_drawer()
    assert view.ai_drawer.isHidden()

    # Test AI Copilot Natural Language Command & Tax Advisor
    view.ai_input.setText("What is my Michigan state tax?")
    view._handle_ai_send()
    last_msg = view._chat_history[-1]["text"]
    assert "Michigan" in last_msg or "4.25%" in last_msg, f"Unexpected response: {last_msg}"

    print("  ✅ MasterAccountingNativeView passed 100%!")


def test_steam_gaming_hub_acf_bridge_and_governor():
    print("Testing SteamGamingNativeView...")
    view = SteamGamingNativeView(bus)
    assert view is not None

    # Verify direct ACF Manifest detection across drives
    assert len(view._games) >= 3, f"Expected at least 3 installed Steam games, found {len(view._games)}"
    game_names = [g["name"] for g in view._games]
    print(f"  Detected Games: {game_names}")

    # Verify disk size in GB calculation
    total_size = sum(g["size_gb"] for g in view._games)
    assert total_size > 50.0, f"Expected significant disk footprint, got {total_size} GB"

    # Verify telemetry cards
    assert view.card_games is not None
    assert view.card_disk is not None
    assert view.card_status is not None
    assert view.card_vram is not None

    # Verify Governor Mode switching
    view._engage_game_mode(silent=True)
    val_lbl = view.card_status.findChild(QLabel, "ValLabel")
    assert val_lbl is not None and "ACTIVE" in val_lbl.text()

    view._engage_ai_mode(silent=True)
    val_lbl = view.card_status.findChild(QLabel, "ValLabel")
    assert val_lbl is not None and "STANDBY" in val_lbl.text()

    print("  ✅ SteamGamingNativeView passed 100%!")


def test_nutrition_clinical_protocol_parity():
    print("Testing NutritionNativeView...")
    view = NutritionNativeView(bus)
    assert view is not None

    # Verify 5 daily formulations
    assert len(JUICE_SCHEDULE) == 5
    assert JUICE_SCHEDULE[0][0] == "07:30"
    assert JUICE_SCHEDULE[0][1] == "Anthocyanin Green Ignition"
    assert JUICE_SCHEDULE[1][0] == "10:30"
    assert JUICE_SCHEDULE[1][1] == "Betalain & Nitric Surge"
    assert JUICE_SCHEDULE[4][0] == "19:30"
    assert JUICE_SCHEDULE[4][1] == "Nocturnal Mineral Restorative"

    # Verify Keto Snacks
    assert len(KETO_SNACKS) == 3
    assert KETO_SNACKS[0][0] == "Avocado-MCT Salt Pod"
    assert KETO_SNACKS[1][0] == "Crisped Parmesan Seed Discs"
    assert KETO_SNACKS[2][0] == "Macadamia Cacao Fat Cluster"

    # Verify Raw Payload
    assert RAW_PROTOCOL_PAYLOAD["protocol_duration_days"] == 14
    assert RAW_PROTOCOL_PAYLOAD["electrolytes_target_mg_daily"]["elemental_sodium"] == 5000
    assert RAW_PROTOCOL_PAYLOAD["electrolytes_target_mg_daily"]["elemental_potassium"] == 1000
    assert RAW_PROTOCOL_PAYLOAD["electrolytes_target_mg_daily"]["elemental_magnesium"] == 300

    # Verify Payload Copying
    assert view.btn_copy_payload is not None
    view._copy_payload()

    print("  ✅ NutritionNativeView passed 100%!")


if __name__ == "__main__":
    test_master_accounting_ledger_and_tax_suite()
    test_steam_gaming_hub_acf_bridge_and_governor()
    test_nutrition_clinical_protocol_parity()
    print("\n🎉 ALL PHASE 5 VERIFICATION TESTS PASSED 100% PERFECTLY!")
    sys.stdout.flush()
    import os
    os._exit(0)
