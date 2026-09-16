# Implementation Proposal: Headless Pearl Payout Watcher Daemon

## Problem Statement
While mining Pearl on your RTX 4090 (~290 TH/s), block rewards sit in an `unconfirmed` state on HeroMiners until they reach 100 confirmations (`depth: 100`) and the 1.0 PRL payout threshold is achieved. During this ~1 to 2 hour maturity window, your Pearl Desktop Wallet shows 0 PRL with zero progress indicators unless manually querying the pool API.

## Proposed Solution: Headless Payout Watcher Daemon
Deploy a lightweight, headless Python watcher (`miners/pearl_payout_watcher.py`) that monitors block maturity and automatically logs the transaction into your AI-BS accounting ledger the moment the payout broadcasts to the mempool.

---

## Technical Specifications

### 1. Polling & Telemetry Parameters
- **Target Endpoint:** `https://pearl.herominers.com/api/stats_address?address=prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5`
- **Polling Interval:** Every 60 seconds (1 HTTP GET request/min; negligible compute and bandwidth).
- **Tracked Variables:**
  - `networkHeight`: Current blockchain height.
  - `unconfirmed`: List of pending blocks found by pool and confirmations remaining (`100 - (networkHeight - blockHeight)`).
  - `unlocked`: Unlocked PRL balance eligible for disbursement.
  - `payments`: Payout transaction hashes and amounts.

### 2. Automated Action on Payout Broadcast
When the watcher detects a new transaction in `payments` or an increase in `stats.paid`:
1. **Console Alert:** Outputs timestamped alert with TX hash, amount, and block height.
2. **Automated Ledger Logging:** Automatically inserts a row into SQLite table `crypto_transfers` in `C:\AI-BS\backend\data\aibs_master.db`:
   - `category`: `mining_reward`
   - `source_account`: `HeroMiners Pool (us.pearl.herominers.com)`
   - `dest_account`: `Pearl Desktop Wallet (AI-BS)`
   - `asset`: `PRL`
   - `amount`: Exact PRL paid (e.g. `1.14 PRL`)
   - `usd_total_value`: Calculated using live PRL spot rate
   - `tx_hash`: On-chain transaction ID
3. **Frontend Sync:** The newly deployed **Crypto Accounting & Transfers** tab at `https://ai-bs-dashboard.web.app` will automatically show the mined income row upon next refresh.

---

## User Review Options (Select or Comment in Side Panel)

1. **Option A (Recommended): Launch Headless Watcher as Persistent Daemon**
   - Create `miners/pearl_payout_watcher.py` and run it as a silent background daemon (`task`).
   - Automatically posts mined rewards into the accounting database upon pool payout.
2. **Option B: Run Interactive Terminal Watcher**
   - Create `miners/pearl_payout_watcher.py` and provide a 1-click batch launcher (`miners/Watch_Pearl_Payout.bat`) for you to run in a dedicated command window with live countdown timers.
3. **Option C: Do Not Run Watcher**
   - Maintain current passive configuration; check the Pearl Desktop Wallet or HeroMiners web dashboard manually.

---

## Verification Plan
1. **Dry-Run Test:** Execute single verification cycle to ensure API parsing, depth countdown calculation, and DB connection work without errors.
2. **Daemon Verification:** Confirm background execution with zero GPU/CPU interference against the active miner daemon (`task-4056`).
