# Tasks: Support Target Dip Calibration & Vault Stash Governance

- [x] Analyze Option A against Crypto.com Exchange minimum order notional rules (identified $1.00 minimum vs $0.27 stash valuation) <!-- id: 1 -->
- [x] Formulate Option B calibration plan targeting the $0.05719 macro support level <!-- id: 2 -->
- [x] Await user confirmation on the plan in `implementation_plan.md` <!-- id: 3 -->
- [x] Update `backend/.env` and root `.env` with `BUY_DIP_PCT=0.042` and `MACRO_SUPPORT_CEILING=0.05750` <!-- id: 4 -->
- [x] Refactor `update_hourly_and_check_dip` in `crypto_trader_bot.py` to eliminate false-positive micro-dip triggers at resistance <!-- id: 5 -->
- [x] Update `CryptoSwarmMobileController.jsx` default dip parameter to 4.2% and add macro support ceiling input <!-- id: 6 -->
- [x] Restart daemon, verify live telemetry on Port 8007, and deploy frontend to Firebase <!-- id: 7 -->
- [x] Synchronize Master Architectural Ledger and Ecosystem Manual <!-- id: 8 -->

