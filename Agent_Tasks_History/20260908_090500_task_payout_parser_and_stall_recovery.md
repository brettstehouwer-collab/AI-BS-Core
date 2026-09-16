# Task: HeroMiners String Payment Parsing & Mining Socket Stall Auto-Recovery (v5.215.0)

- [x] 1. Update `miners/pearl_payout_watcher.py` payment parsing logic for HeroMiners colon-delimited string format (`<tx_hash>:<amount_units>:<mixin>`) <!-- id: 0 -->
- [x] 2. Implement automated socket stall watchdog in `pearl_payout_watcher.py` (monitoring low power / 0 hashrate and recycling peakminer via WSL2) <!-- id: 1 -->
- [x] 3. Restart `pearl_payout_watcher.py` and verify live mempool ingestion of payout `dd1b3a45...` (1.9933 PRL) into `backend/aibs_master.db` <!-- id: 2 -->
- [x] 4. Verify backend accounting API endpoint `GET /api/accounting/crypto-transfers` reflects real mined income <!-- id: 3 -->
- [x] 5. Perform `v5.215.0` version sweep across frontend/backend components <!-- id: 4 -->
- [x] 6. Compile frontend bundle (`npm run build`) and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 5 -->
- [x] 7. Synchronize Master Architectural Ledger, Ecosystem Manual, and archive plans/tasks <!-- id: 6 -->
