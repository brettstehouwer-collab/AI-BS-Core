# Task: Persistent Hardware Clamping, Systemd Unit & Driver Recovery Watchdog

## Current Status
- [x] Draft interactive implementation plan for 3-tier persistent clock/power clamping <!-- id: 0 -->
- [x] User review and manual confirmation in chat <!-- id: 1 -->
- [x] Implement Tier 1: Windows Elevated Scheduled Task (`AI-BS-GPU-Hardware-Persistence`) to enforce 310W / 5001 MHz at OS boot <!-- id: 2 -->
- [x] Implement Tier 2: WSL2 Systemd Service (`aibs-gpu-persistent.service`) with host interop invocation <!-- id: 3 -->
- [x] Implement Tier 3: Driver Recovery Watchdog in `miners/pearl_payout_watcher.py` (auto-reapplies profile on driver crash/reset) <!-- id: 4 -->
- [x] Verification & Simulated Driver Recovery Test: Confirmed automated enforcement (400W -> 310W in <60s) <!-- id: 5 -->
- [x] Update Master Architectural Ledger & Ecosystem Manual (`v5.211.0`) <!-- id: 6 -->
- [x] Archive Task and Implementation Plan to Master Historical Repositories <!-- id: 7 -->
