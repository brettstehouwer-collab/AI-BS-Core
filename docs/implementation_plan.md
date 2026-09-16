# Implementation Plan: HeroMiners String Payment Parsing & Socket Stall Auto-Recovery

## Overview
Operationalizes automated on-chain payout ingestion into the AI-BS accounting ledger and equips the background payout watcher daemon (`miners/pearl_payout_watcher.py`) with self-healing socket stall recovery for unattended continuous mining.

---

## Proposed Changes

### Component: Mining Supervision & Accounting Watchdog (`miners/pearl_payout_watcher.py`)
1. **HeroMiners String Format Parsing:**
   - Enhance `payments` array parser in `run_watcher()` to inspect elements formatted as `"<tx_hash>:<amount_units>:<mixin>"`.
   - Parse `tx_hash` (`dd1b3a458a7cc1713c1b5a69df3b5db6ca1a4aabe443c2e807a1281c95b458c0`), amount in PRL (`1.99333790 PRL`), and timestamp.
   - Insert verified record into `crypto_transfers` table in `backend/aibs_master.db`.
   - Dispatch Discord embed alert to `#trade-signals`.
2. **Socket Stall Detection & Auto-Recovery:**
   - Add `check_and_recover_stalled_miner(worker_hashrate, good_shares, cycle)` in `pearl_payout_watcher.py`.
   - Track consecutive stalled cycles where GPU power < 100W while peakminer process exists in WSL2, or hashrate = 0 and no new shares for > 15 minutes.
   - Issue graceful `pkill -TERM -f peakminer` inside WSL2, triggering `Mine_Pearl.bat`'s auto-restart loop with a clean socket reconnect.

---

## Verification Plan

### Automated Verification:
- Run `pearl_payout_watcher.py` test cycle to confirm extraction of transaction `dd1b3a45...`.
- Verify record exists in `backend/aibs_master.db` via SQLite query.
- Query `GET http://localhost:8080/api/accounting/crypto-transfers` to verify live JSON response.
- Test stall detection logic with simulated parameter check.

### Production Deployment:
- Sweep version badges to `v5.215.0`.
- Build frontend (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Synchronize all master architectural ledgers.
