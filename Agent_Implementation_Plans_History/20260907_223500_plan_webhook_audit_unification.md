# Implementation Plan: Unified Mining & Trading Discord Webhook Integration

## Overview
Comprehensive audit of ecosystem webhooks, live miners, and trading feeds. While the underlying daemons and hardware are operating at peak efficiency (595 accepted shares, 100% efficiency, block maturity unlocking 0.2164 PRL, live websocket feeds on CRO/USD), webhook dispatches currently have gaps in automated delivery:
1. **Miners Telemetry:** `pearl_payout_watcher.py` writes strictly to `aibs_master.db` and log files; it is not yet wired to push Discord webhook notifications on block maturity or payout events.
2. **Trading Bot:** `crypto_trader_bot.py` is actively receiving live websocket prices ($0.05608 CRO), but because live exchange order execution is dormant (running in paper/ledger mode), trade fill alerts have not fired.
3. **Discord Telemetry Daemon:** 4 duplicate background instances existed, with two running on a Python environment lacking `discord.py`, preventing periodic status broadcasts.

---

## Proposed Changes

### Component 1: Miner Webhook Integration

#### [MODIFY] [miners/pearl_payout_watcher.py](file:///C:/AI-BS/miners/pearl_payout_watcher.py)
* Add `dispatch_discord_webhook(title, description, fields, color)` utility function.
* Load `DISCORD_WEBHOOK_URL` from `C:\AI-BS\.env`.
* Trigger rich embeds on:
  * Mempool payout detection (`color=0x00ffcc`, Emerald/Pearl)
  * Block maturity unlock (`color=0x3498db`, Blue)
  * Hourly health summary (`color=0x9b59b6`, Purple)

---

### Component 2: Daemon Consolidation & Clean Startup

#### [EXECUTE] Terminate Duplicate Daemons & Standardize Runtime
* Terminate all 4 duplicate `discord_bot_daemon.py` processes.
* Launch a single consolidated instance using `C:\AI-BS\pyppeteer_env\Scripts\python.exe` (where `discord.py 2.7.1` is confirmed active).

---

## Verification Plan

### Automated Tests
1. **Webhook Probe:** Dispatch a test JSON payload to the Discord webhook and verify `HTTP 204 No Content` response from Discord API.
2. **Heartbeat Verification:** Trigger on-demand status broadcast to confirm channel receipt.
