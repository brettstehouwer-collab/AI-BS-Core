import os
import sys
import asyncio
import logging
import sqlite3

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.accounting_router import (
    get_entries,
    save_entry,
    get_tax_summary,
    EntrySchema,
)


def run_accounting_test():
    print("\n======================================================================")
    print("[INIT] RUNNING MASTER ACCOUNTING & TAX SUITE VERIFICATION")
    print("======================================================================\n")

    # 1. Fetch entries
    res_entries = get_entries()
    assert res_entries["status"] == "success"
    print(f"[PASS 1] Successfully fetched {res_entries['count']} ledger entries.")

    # 2. Add test entry
    test_entry = EntrySchema(
        date="2026-07-25",
        category="Hardware & Electronics",
        description="Test Secondary RTX GPU Rig",
        entry_type="expense",
        amount=899.99,
        is_tax_deductible=True,
        schedule_c_code="Sec179_Hardware",
        receipt_note="Test Invoice",
    )
    res_save = save_entry(test_entry)
    assert res_save["status"] == "success"
    print(f"[PASS 2] Successfully saved test ledger entry (ID: {res_save['id']}).")

    # 3. Calculate tax summary
    summary = get_tax_summary()
    assert summary["gross_income"] >= 0.0
    assert summary["tax_deductible_expenses"] > 0.0
    assert summary["estimated_michigan_state_tax"] >= 0.0

    print("\n[PASS 3] Tax Calculations Audit:")
    print(f"   - Gross Income: ${summary['gross_income']:,.2f}")
    print(f"   - Deductible Expenses: ${summary['tax_deductible_expenses']:,.2f}")
    print(
        f"   - Section 179 Hardware Write-off: ${summary['section_179_hardware_deduction']:,.2f}"
    )
    print(
        f"   - Michigan State Tax (4.25% Flat): ${summary['estimated_michigan_state_tax']:,.2f}"
    )
    print(
        f"   - US Federal SE Tax (15.3%): ${summary['estimated_federal_se_tax']:,.2f}"
    )
    print(
        f"   - Total Estimated Tax Liability: ${summary['total_estimated_tax_liability']:,.2f}"
    )
    print(
        f"   - Tax Savings from Write-offs: ${summary['estimated_tax_savings_from_writeoffs']:,.2f}"
    )

    print("\n======================================================================")
    print("SUMMARY: ALL 3 ACCOUNTING & TAX VERIFICATION PASSES SUCCEEDED!")
    print("======================================================================\n")


if __name__ == "__main__":
    run_accounting_test()
