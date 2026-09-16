# Calibration Plan: Support Target Dip Calibration & Vault Stash Governance

Evaluation of Option A (Vault Stash Liquidation) against exchange constraints and operational implementation of Option B (targeting the $0.05719 macro support level).

## User Review Required

> [!WARNING]
> **Exchange Minimum Order Limit on Option A:**
> Crypto.com Exchange enforces a strict **$1.00 USD minimum order notional**.
> - The 4.4579 CRO vault stash at $0.05995 is worth **$0.267 USD**.
> - Submitting a sell order for 4.4579 CRO will trigger error `415 BELOW_MIN_ORDER_SIZE` from Crypto.com Exchange matching engine.
> - Furthermore, the live exchange free balance is 0.30 CRO (the 4.4579 CRO was tracked on the local ledger).
> - **Recommendation:** Keep the vault stash compounding until future buy cycles accumulate at least 20+ CRO (>$1.00 USD), allowing a clean liquidation that complies with exchange rules.

> [!IMPORTANT]
> **Implementation of Option B (Support Level Target):**
> To target the verified green **"Avg. Buy price"** support zone on your 4h chart (**`$0.05719`**):
> 1. Set `BUY_DIP_PCT=0.042` (4.2% pullback threshold) in [.env](file:///C:/AI-BS/.env) and [backend/.env](file:///C:/AI-BS/backend/.env).
> 2. Remove the micro-dip trigger `or (current_price <= hourly_min * 1.002)` in `crypto_trader_bot.py`, which caused the bot to mistake 60-second micro-pauses at peak resistance for macro dips.
> 3. Enforce that entries only trigger when `current_price <= $0.05750` (or after a true ≥4.2% pullback).

## Proposed Changes

### Configuration & Core Trading Daemon

#### [MODIFY] [C:\AI-BS\.env](file:///C:/AI-BS/.env)
- Update `BUY_DIP_PCT="0.042"`.
- Add `MACRO_SUPPORT_CEILING="0.05750"`.

#### [MODIFY] [C:\AI-BS\backend\.env](file:///C:/AI-BS/backend/.env)
- Update `BUY_DIP_PCT="0.042"`.
- Add `MACRO_SUPPORT_CEILING="0.05750"`.

#### [MODIFY] [C:\AI-BS\backend\crypto_trader_bot.py](file:///C:/AI-BS/backend/crypto_trader_bot.py)
- Refactor `update_hourly_and_check_dip` to enforce a true pullback of `DCA_DIP_PCT` (4.2%) from rolling highs/averages without false-positive micro-minima triggers at resistance peaks.
- Guard buy execution: `if current_price <= float(keys.get("MACRO_SUPPORT_CEILING", 0.05750)):`.

#### [MODIFY] [C:\AI-BS\frontend\src\components\CryptoSwarmMobileController.jsx](file:///C:/AI-BS/frontend/src/components/CryptoSwarmMobileController.jsx)
- Update default `buyDipPct` form state from `1.0` to `4.2`.

## Verification Plan

### Automated Verification
- Query `http://127.0.0.1:8007/api/v1/telemetry` to confirm updated parameter state.
- Tail `backend/logs/crypto_trader_bot.log` to confirm that the bot remains patient and does NOT trigger buys until price drops to the `$0.05719 – $0.05750` zone.
