# Task: Discord Bot Interactive UI Controls & Granular Telemetry Dispatch (v5.214.0)

## Completed Tasks
- [x] Diagnose root cause of stale 2-hour text message (PIDs 28992 and 36004 running old Python 3.12 code in memory) <!-- id: 0 -->
- [x] Terminate all 6 zombie bot daemons using `kill_zombie_bots.py` <!-- id: 1 -->
- [x] Design and implement `TelemetryControlView(discord.ui.View)` with 5 persistent interactive buttons: `[🔄 Refresh Telemetry]`, `[⛏️ Mining Details]`, `[🖥️ Hardware Clocks]`, `[🛡️ Enforce 310W Clamp]`, `[💼 Fiscal Ledger]` <!-- id: 2 -->
- [x] Support remote operator chat commands: `!status`, `!miner`, `!gpu`, `!clamp`, `!ledger`, `!payout`, `!help`, `!ping` <!-- id: 3 -->
- [x] Re-launch unified `discord_bot_daemon.py` (`task-5990`) and `pearl_payout_watcher.py` (`task-5996`) under `pyppeteer_env` <!-- id: 4 -->
- [x] Verify live dispatch with buttons to `#trade-signals` (`1526361931399827466`) <!-- id: 5 -->
- [x] Perform `v5.214.0` version sweep across 25 files and synchronize all Master Ledgers <!-- id: 6 -->
