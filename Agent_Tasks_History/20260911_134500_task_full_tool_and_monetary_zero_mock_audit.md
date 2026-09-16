# Master Task Plan: Full Ecosystem Tool Functionality & Monetary Zero-Mock Audit (v5.253.0)

## Status: IN PROGRESS (Awaiting User Manual Consent)

- [ ] **Phase 1: Forensic Audit of All Tools, Actions & Monetary Systems** <!-- id: 1 -->
  - [x] Audit `backend/tools/tool_registry.py` (26 declared tools vs 26 executed handlers verified; identified stubs in `detect_objects` and `reconstruct_scene`)
  - [x] Audit monetary routers (`backend/routers/trading_router.py`, `backend/modules/accounting_router.py`, `backend/commercial_gateway/billing_provisioner.py`)
  - [x] Audit SQLite financial tables (`accounting_entries`, `crypto_transfers`, `billing_transactions`, `trades` across `aibs_master.db`, `stehouwer_accounting.db`, `commercial_usage.db`, `drip_ledger.db`)
  - [x] Audit frontend financial tabs (`CryptoAccountingTab.jsx`, `MasterAccountingTab.jsx`, `PearlMiningHubTab.jsx`, `MoneyTrackTab.jsx`, `DigitalStorefrontTab.jsx`)
- [ ] **Phase 2: Monetary Subsystem Refactoring & Zero-Mock Database Purge** <!-- id: 2 -->
  - [ ] Purge synthetic test rows 5 & 6 (`Test Secondary RTX GPU Rig`, $899.99) from `accounting_entries` in `backend/aibs_master.db` and `backend/stehouwer_accounting.db`
  - [ ] Purge 12 synthetic test rows (`PayPalTester`, `StripeTester`, `LiveTestClient`) from `billing_transactions` in `backend/commercial_gateway/commercial_usage.db`
  - [ ] Refactor `backend/routers/trading_router.py`: Eliminate hardcoded mock balances (`$1425.80`, USDT 850.50, SOL 2.85, ETH 0.035); wire to `crypto_ledger.json` / live CCXT or return clean unbonded state (`0.00 USD`, `balances: []`)
  - [ ] Refactor `backend/commercial_gateway/billing_provisioner.py`: Eliminate simulated payment insertions in `simulate-checkout`; ensure `billing_transactions` only records verified live webhook events (`PAYMENT.CAPTURE.COMPLETED`, `checkout.session.completed`)
  - [ ] Harden `POST /api/trading/order` to validate real exchange credentials rather than inserting synthetic "FILLED" trades
- [ ] **Phase 3: Tool Registry Upgrades (Real Vision & Spatial Processing)** <!-- id: 3 -->
  - [ ] Upgrade `detect_objects` in `backend/tools/tool_registry.py` to use `AIBSImageAnalyzer` / OpenCV / YOLO to extract real bounding boxes, confidences, and labels
  - [ ] Upgrade `reconstruct_scene` in `backend/tools/tool_registry.py` to compute real image contour, spatial geometry, and depth statistics rather than static mock nodes
- [ ] **Phase 4: Automated Verification, Ledger Sync & Production Deployment** <!-- id: 4 -->
  - [ ] Author and execute `backend/test_full_tool_and_zero_mock_audit.py` to verify all 26 tools execute on demand and monetary endpoints return zero mock figures
  - [ ] Bump ecosystem version from `v5.252.0` to `v5.253.0`
  - [ ] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` with timestamped entry, technical specs, and fallback context
  - [ ] Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (bump version to 5.253.0) and log in `NotebookLM_Records/artifact_history.md`
  - [ ] Update `MASTER_TASKS_CHRONOLOGY.md` and `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`
  - [ ] Sweep frontend UI version parity and run `npm run build; firebase deploy --only hosting --non-interactive` per Strict Deployment Rule
