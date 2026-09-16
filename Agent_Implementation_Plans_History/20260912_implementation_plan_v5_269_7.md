# Implementation Plan: Autonomous 24/7 Unified Crypto & Pearl Supervisor (v5.269.7)

## Problem & Context
The operator required:
1. Ensuring the CRO crypto trading swarm bots never miss a market trigger event across market rises and falls, order book pauses, or silent WebSocket disconnects.
2. Ensuring Pearl Wallet runs continuously in the background unless the operator explicitly stops it.

## Architecture & Implementation
1. **Hybrid WebSocket + REST Heartbeat Engine (`backend/crypto_trader_bot.py`)**:
   - Extracted modular `evaluate_market_tick(...)` processing order book imbalances, pending post-profit dip limit orders, trailing DCA, hourly low dips, and compounding.
   - Wrapped `watch_order_book` in a 10s watchdog timeout: on quiet markets or WebSocket stalls, immediately polls REST `fetch_ticker`.
   - Added rate-limiting throttle on pending order checks.
   - Wrapped worker loops in `resilient_worker` auto-respawn handlers.
2. **Unified Crypto & Pearl Autonomous Watchdog (`backend/core/unified_crypto_pearl_watchdog.py`)**:
   - Runs continuous 5s health loop.
   - Monitors Port 8007 `/api/v1/telemetry`, respawns crypto bot if unresponsive.
   - Monitors Pearl Wallet (`Pearl Wallet.exe`), oyster daemon (`oyster-windows-x64.exe`), and pool watcher (`pearl_payout_watcher.py`).
   - Respects operator sentinel `C:\AI-BS\.pearl_stopped`:
     - Present -> paused, honors operator stop intent.
     - Absent -> actively ensures Pearl runs 24/7 in background.
3. **Control Scripts & Endpoints**:
   - `Stop_Pearl.bat`, `Start_Pearl.bat`, `Start_Unified_Watchdog.bat`.
   - FastAPI endpoints: `/api/v1/pearl/start`, `/api/v1/pearl/stop`, `/api/v1/pearl/status`, `/api/v1/ecosystem/watchdog/status`.
4. **Multi-Mirror Synchronization & UI Parity**:
   - Version `v5.269.7` synchronized across all 4 frontend mirrors with 100% SHA256 byte parity.
5. **Production Build & Cloud Sync**:
   - Compiled production bundle and deployed live to Firebase Hosting.
