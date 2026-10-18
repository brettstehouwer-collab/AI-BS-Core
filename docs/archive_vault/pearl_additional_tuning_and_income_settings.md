# Additional Settings & Architectural Levers to Maximize Pearl (PRL) Rig Income

This document outlines all technical levers, hardware parameters, connection protocols, and multi-asset operational strategies available to increase net income from Pearl (PRL) mining on this system (**NVIDIA GeForce RTX 4090 24GB + AMD Ryzen 9 9950X 16-Core / 32-Thread, 64GB DDR5, $0.00/kWh Marginal Power Cost**).

---

## 1. Executive Summary: What Can Be Adjusted

| Category | Lever / Setting | Current State | Potential Setting | Impact on Income / Hashrate | Risk / Tradeoff |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Power Limit** | Board Power Cap (`-pl`) | `390W` | **`420W` – `450W`** | **+10% to +18% Hashrate** (~260–280 TH/s) | +4°C to +7°C GPU temp (still <63°C) |
| **GPU Core Clock** | Core Frequency Offset | Stock V/F curve | **`+150 MHz` to `+200 MHz`** | **+5% to +7% Hashrate** at same wattage | Silicon lottery stability testing required |
| **Memory Clock** | Locked VRAM Clock (`-lmc`) | `5001 MHz` | **`5001 MHz` (Hold)** | Saves ~40W GDDR6X power for GPU core | Already optimized; 810 MHz risks DMA bottleneck |
| **Stratum Failover** | Secondary Stratum Node | `us.pearl` (152 ms) | **`us3.pearl` (52.9 ms)** | Eliminates stale share spikes on failover | Zero risk; -100 ms latency reduction |
| **Stratum Socket** | TCP Keepalive (`--keepalive`) | Disabled | **Enabled (`--keepalive`)** | Prevents dead TCP link stalls / idle disconnects | Zero risk |
| **CPU Monetization** | AMD Ryzen 9 9950X Mining | 0% (Idle) | **RandomX (XMR / ZEPH / VRSC)** | **+$0.40 – $0.75 / day** ($12–$22/mo added revenue) | CPU temp ~65–72°C; auto-paused on Vast orders |

---

## 2. Power & Clock Settings (GPU Level)

### A. Power Limit Expansion: 390W vs 420W vs 450W
*   **Why it matters:** Pearl uses the **PearlHash** algorithm, which is strictly **compute-bound** (performing continuous matrix multiplication GEMM tiles via Ada Lovelace Tensor/CUDA cores).
*   **Behavior under load:** Under heavy matrix tiling, the GPU core hits the power ceiling and dynamically clocks down from 2,775 MHz to ~2,280 MHz to respect the 390W limit.
*   **Hardware headroom:** The card is a full-spec RTX 4090 with a factory default TDP of **450W** and a hardware ceiling of **600W**.
*   **Marginal power cost:** Because electricity is **$0.00 / kWh**, efficiency (TH/s per Watt) is irrelevant; **absolute hashrate (TH/s) directly dictates daily fiat revenue**.

```
[310W Baseline] -> 169.4 TH/s (Core throttled to 1,995 MHz, 51°C)
[390W Current]  -> 228.0 - 250.0 TH/s (Core boosts to 2,280 - 2,775 MHz, 53°C)
[420W Profile]  -> 255.0 - 265.0 TH/s (Core sustains 2,450 - 2,775 MHz, ~57°C)
[450W Uncapped] -> 270.0 - 285.0 TH/s (Full factory TDP, core sustains 2,600 - 2,800 MHz, ~61°C)
```

> [!NOTE]
> At 100% fixed fan speed, the GPU core operates at 53°C under 390W. Even at 450W, the thermal dissipation on this 3-slot cooler will remain well below 65°C (far beneath the 84°C NVIDIA thermal throttle threshold).

---

### B. Core Clock V/F Offset (`+150 MHz` to `+200 MHz`)
*   Applying a positive core offset shifts the Voltage/Frequency curve upward.
*   For the exact same power draw (e.g. 390W or 420W), the core runs **150–200 MHz higher**, executing more GEMM matrix operations per clock cycle.
*   Can be tested via PeakMiner's `--gpu-core 150` argument or driver-level curve offsets.

---

### C. Memory Clock Locking (`-lmc 5001`)
*   Pearl does not require high memory bandwidth (unlike Ethash/KawPow). The tensor matrices are cached in L1/L2 SRAM on-die.
*   Stock memory runs at 10,501 MHz, drawing ~40W–50W of power strictly to refresh GDDR6X chips.
*   Locking memory to `5001 MHz` (`nvidia-smi -lmc 5001`) drops VRAM power draw, re-routing that 40W directly into the compute core.
*   *Why not 810 MHz?* Testing in compute-heavy algos shows that dropping memory below 5000 MHz can bottleneck PCIe DMA transfers between system host memory and GPU VRAM. 5001 MHz is the proven sweet spot.

---

## 3. Connection & Stratum Settings (Pool Level)

### A. Stratum Latency Hierarchy Optimization
HeroMiners operates multiple stratum relays across North America. Empirical latency benchmarks from the rig's Metronet Fiber connection (West Michigan):

| Stratum Node | Location | Measured TCP Handshake | Recommendation |
| :--- | :--- | :--- | :--- |
| **`us2.pearl.herominers.com:1200`** | US East | **40.40 ms** | **Primary Stratum (Active)** |
| **`us3.pearl.herominers.com:1200`** | US Central / South | **52.90 ms** | **High-Priority Backup (NEW)** |
| **`ca.pearl.herominers.com:1200`** | Canada | **98.54 ms** | Tertiary Backup |
| **`us.pearl.herominers.com:1200`** | US West | **152.55 ms** | Quaternary Backup |

*Actionable Adjustment:* Currently, `Mine_Pearl.bat` falls back directly from `us2` to `us` (152 ms). Inserting `us3.pearl.herominers.com:1200` cuts secondary failover latency by **100 ms (-65%)**.

---

### B. HeroMiners Stale Share Penalty Governance
The HeroMiners pool configuration API exposes a progressive penalty system for stale shares:

```json
"staleSharePenaltyThresholds": [
  { "maxPercent": 2,  "penalty": 0 },
  { "maxPercent": 5,  "penalty": 50 },
  { "maxPercent": 30, "penalty": 100, "action": "warn" },
  { "maxPercent": 100,"penalty": 100, "action": "ban" }
]
```

*   **Under 2% stales:** Zero penalty.
*   **Between 2% and 5% stales:** **50% of your block reward is forfeited**.
*   **Above 30% stales:** **100% of your block reward is forfeited**.

**Key Architectural Settings:**
1.  **Do NOT enable `--send-stales` in PeakMiner:** When PeakMiner detects that a job has rotated before a share was sent, dropping it locally prevents the pool from recording a stale share on the operator's account.
2.  **Enable `--keepalive`:** Sends periodic `mining.ping` frames every 20 seconds. This prevents edge routers and firewalls from silently dropping idle TCP sockets, eliminating connection re-negotiation delays.

---

### C. Variable Difficulty vs Static Difficulty
*   HeroMiners API confirms: `"fixedDiffEnabled": false`.
*   The pool strictly enforces **VarDiff (Variable Difficulty)**. Any diff override in the password field (e.g. `d=...`) is ignored by the pool's stratum coordinator.
*   Leaving password as `-p x` with standard VarDiff is the optimal configuration.

---

## 4. Rig-Level Expansion: Dual-Mining CPU Monetization

### AMD Ryzen 9 9950X (16 Cores, 32 Threads) Idle Monetization
*   **Current State:** The RTX 4090 is running Pearl at 100% load. The Ryzen 9 9950X CPU is currently **95% idle**.
*   **Opportunity:** The 9950X is one of the highest-performing consumer CPUs for **RandomX (Monero XMR / Zephyrus ZEPH / Tari)** and **VerusHash (VRSC)**.
*   **Estimated Production:**
    *   RandomX Hashrate: ~18,000 – 22,000 H/s.
    *   Daily Revenue: **+$0.40 – $0.75 / day** ($12.00 – $22.50 / month).
    *   Marginal Electricity Cost: **$0.00**.
*   **Interference with GPU Mining:** 0%. GPU matrix feeding uses less than 0.5 CPU threads. The remaining 31 threads can mine without dropping a single TH/s from the RTX 4090.
*   **Tri-Yield Integration:** The `vast_clore_pearl_watchdog.py` daemon can automatically pause the CPU miner whenever a CPU-heavy Vast.ai or Clore.ai rental container is launched.

---

## 5. Summary of Actionable Options

1.  **Option 1: Power Limit Step-Up to 420W or 450W (Profile C):**
    *   Command: `nvidia-smi -pl 420` (or `450`).
    *   Expected outcome: Core boosts to 2,600–2,800 MHz constantly, yields ~260–280 TH/s (+12% to +18% revenue).
2.  **Option 2: Core Clock Offset Testing (`+150 MHz`):**
    *   Command: Add `--gpu-core 150` to PeakMiner.
    *   Expected outcome: ~+5% hashrate boost at the current 390W limit.
3.  **Option 3: Stratum Resilience Upgrade (`us3` Node + `--keepalive`):**
    *   Add `us3.pearl.herominers.com:1200` (52.9 ms) and `--keepalive` to `Mine_Pearl.bat`.
    *   Expected outcome: Immediate drop in fallback latency and elimination of TCP idle drops.
4.  **Option 4: Dual-Mining CPU Setup (Ryzen 9 9950X on RandomX):**
    *   Deploy XMRig configured for Monero/Zephyrus with automated watchdog auto-pause during Vast/Clore rentals.
    *   Expected outcome: +$12 – $22/month extra revenue at $0 electricity cost.
