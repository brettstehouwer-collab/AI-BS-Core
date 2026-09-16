# Implementation Plan: Discord Bot Interactive UI Controls & Granular Telemetry Dispatch (v5.214.0)

## Overview
Transform Discord outbound telemetry from passive, stale text updates into a real-time, interactive command center featuring persistent clickable buttons, ephemeral diagnostic deep-dives, remote hardware re-clamping, and comprehensive PoUW mining telemetry.

## Changes Implemented
1. **Zombie Process Clean-up**: Terminated 6 duplicate background Python processes running stale code.
2. **Persistent Interactive Buttons (`discord.ui.View`)**:
   - `[🔄 Refresh Telemetry]`: In-place embed edit updating live stats.
   - `[⛏️ Mining Details]`: Ephemeral breakdown with worker, accepted shares, and maturity countdowns.
   - `[🖥️ Hardware Clocks]`: Ephemeral RTX 4090 power, clocks, and thermals.
   - `[🛡️ Enforce 310W Clamp]`: On-demand driver clamp enforcement (`nvidia-smi -pl 310 -lmc 5001`).
   - `[💼 Fiscal Ledger]`: Ephemeral accounting records from SQLite.
3. **Operator Chat Commands**: Added prefix commands (`!status`, `!miner`, `!gpu`, `!clamp`, `!ledger`, `!payout`, `!help`).
4. **Daemon Launch & Verification**: Ran `discord_bot_daemon.py` and `pearl_payout_watcher.py`, successfully connecting and dispatching interactive cards to `#trade-signals`.
