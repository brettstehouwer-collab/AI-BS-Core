# Implementation Plan: Additional Pearl & Rig Optimization Levers (v5.220.0)

## Overview
Based on the operator's inquiry regarding additional settings (power, connection, clocks, software) to increase income on Pearl, this plan provides a structured execution path across four high-impact levers:
1. **Power Limit Expansion:** Testing 420W vs 450W (factory 100% TDP) to unlock an estimated +10% to +18% additional hashrate (~260–280 TH/s) under zero electricity cost ($0.00/kWh).
2. **Core Frequency Offset:** Applying a positive V/F curve offset (`+150 MHz`) to extract additional matrix GEMM compute at identical power.
3. **Stratum Connection Resilience:** Integrating the newly benchmarked `us3.pearl.herominers.com:1200` (52.9 ms) node and `--keepalive` to eliminate failover latency spikes and avoid HeroMiners' >2% stale share penalty ladder.
4. **Rig-Level CPU Dual-Monetization:** Utilizing the idle AMD Ryzen 9 9950X (16-core / 32-thread) for RandomX cryptocurrency mining (XMR/ZEPH) to generate +$0.40 – $0.75/day in pure additive revenue without affecting GPU throughput.

---

## User Review Required
> [!IMPORTANT]
> - **Power Limit Expansion:** Moving from 390W to 420W or 450W will increase GPU power draw by 30W–60W. With 100% fan duty, temperatures are projected at 57°C–61°C (well below the 84°C throttle point). Since power is $0.00/kWh, every additional watt produces pure top-line revenue.
> - **CPU Dual-Mining:** Running RandomX on the Ryzen 9 9950X will utilize 28–30 CPU threads, raising CPU temperatures to ~68°C–74°C. The Tri-Yield concurrency watchdog will automatically pause CPU mining if a Vast.ai or Clore.ai rental arrives.
> - **Explicit Manual Consent Required:** In adherence to AI-BS safety rules, no hardware limits, miner arguments, or background services will be altered until explicit instructions are given in chat.

---

## Proposed Technical Changes

### 1. Stratum & Connection Upgrades
#### [MODIFY] `C:\AI-BS\miners\Mine_Pearl.bat`
- Insert `stratum+tcp://us3.pearl.herominers.com:1200` as the secondary stratum ahead of Canadian/US-West nodes.
- Add `--keepalive` flag to PeakMiner invocation.

#### [MODIFY] `C:\AI-BS\miners\mine_pearl.sh`
- Mirror stratum order and `--keepalive` flag in the WSL2 shell script.

### 2. Hardware Power & Clock Tuning (Upon Operator Approval)
#### Option A: Power Step-Up to 420W
- Execute `nvidia-smi -pl 420`.
- Update `pearl_payout_watcher.py` drift ceiling to 425W.

#### Option B: Full Factory TDP (450W)
- Execute `nvidia-smi -pl 450`.
- Update `pearl_payout_watcher.py` drift ceiling to 455W.

#### Option C: Core Clock Offset (+150 MHz)
- Add `--gpu-core 150` to PeakMiner startup parameters in `Mine_Pearl.bat`.

### 3. CPU Monetization Integration (Optional)
#### [NEW] `C:\AI-BS\miners\Mine_RandomX_CPU.bat`
- Configure lightweight, open-source XMRig daemon bound to Zen 5 architecture.
- Integrate into `vast_clore_pearl_watchdog.py` with automatic `kill -STOP` / `kill -CONT` orchestration.

---

## Verification Plan
1. **Stratum Handshake & Latency:** Verify PeakMiner connects to `us2` with ~40ms ping, and verifies failover to `us3` with ~53ms ping.
2. **Thermal & Clock Verification:** Continuously monitor `nvidia-smi` to ensure GPU temps remain under 65°C and core clocks boost above 2,600 MHz.
3. **Share Acceptance & Zero Stales:** Query `http://127.0.0.1:4068/summary` to ensure 100% share efficiency and 0 invalid/stale shares.
4. **Tri-Yield Mutual Exclusion:** Confirm that active Vast.ai / Clore.ai rental orders continue to take absolute priority.
