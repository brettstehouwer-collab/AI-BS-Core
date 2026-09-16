# Implementation Plan: Pearl Mining Hub UI Telemetry Enhancement

## Overview
Analysis of the live Pearl Mining Hub UI dashboard reveals that while the hardware and stratum miner are executing at peak performance (619 shares, 100% efficiency, 1.30B hashes, 267W power draw, 47°C core temp), the UI currently lacks visibility into unlocked mature earnings and displays outdated power/binary placeholders:
1. **Unseen Mature Balance:** The pool has matured blocks #110116, #110122, and #110142, unlocking **0.3773 PRL** in mature balance with **1.6161 PRL** pending across 9 blocks. Currently, the UI only displays `VERIFIED ON-CHAIN PAYOUTS: 0.00 PRL`, obscuring the accumulated ~1.9934 PRL ($6.18 USD).
2. **Power Limit Placeholder:** The UI card and hardware panel hardcode `400.00 W (Safe)`, whereas Tier 3 persistence has clamped the card to `310.00 W`.
3. **Execution Binary Path:** The panel hardcodes `/root/peakminer_backup/peakminer` instead of the standardized `/opt/peakminer/peakminer`.

---

## User Review Required

> [!IMPORTANT]
> **Proposed Dashboard Additions:**
> 1. Add **Mature Unlocked Balance Card:** Displaying `0.3773 PRL` ($1.17 USD) and progress towards the 1.0 PRL payout threshold (37.7%).
> 2. Add **Pending Block Accrual Card:** Displaying `1.6161 PRL` across 9 blocks with real-time confirmation countdown.
> 3. Update **Power Limit & Binary Metadata:** Accurately reflect `310.00 W (3-Tier Clamped)` and `/opt/peakminer/peakminer`.

---

## Proposed Changes

### Frontend UI Components

#### [MODIFY] [frontend/src/components/PearlMiningHubTab.jsx](file:///C:/AI-BS/frontend/src/components/PearlMiningHubTab.jsx)
#### [MODIFY] [frontend/components/PearlMiningHubTab.jsx](file:///C:/AI-BS/frontend/components/PearlMiningHubTab.jsx)
#### [MODIFY] [frontend/src/components/components/PearlMiningHubTab.jsx](file:///C:/AI-BS/frontend/src/components/components/PearlMiningHubTab.jsx)
#### [MODIFY] [frontend/components/components/PearlMiningHubTab.jsx](file:///C:/AI-BS/frontend/components/components/PearlMiningHubTab.jsx)

* Expand the metric grid from 6 to 8 cards:
  * **Card: MATURE UNLOCKED BALANCE:** `(stats.balance / 1e8).toFixed(4) PRL` (37.7% of 1 PRL payout threshold).
  * **Card: PENDING BLOCK REWARDS:** `(unconfirmed_sum / 1e8).toFixed(4) PRL` (9 blocks maturing).
* Update GPU Power Limit subtitle from `Capped at 400.00 W (Safe)` to `Capped at 310.00 W (Tier 3 Clamped)`.
* Update Hardware Panel:
  * `Driver Power Envelope:` -> `310.00 W (3-Tier Persistent Guard)`
  * `Execution Binary:` -> `/opt/peakminer/peakminer`

---

## Verification Plan

### Automated Tests
1. Verify Vite frontend compiles with 0 errors.
2. Deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`) and synchronize local desktop dist folders.
3. Validate `/api/v1/mining/pearl/pool-stats` feed into the UI component.
