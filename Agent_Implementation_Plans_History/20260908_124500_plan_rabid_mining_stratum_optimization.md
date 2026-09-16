# Forensic Video Analysis & Pearl Income Optimization Plan
**Source Video:** [Rabid Mining: *Herominers Just Added Pearl! 0% Pool Fees = Top Pool?*](https://youtu.be/zc-dsSauYGM)  
**Target Hardware:** NVIDIA GeForce RTX 4090 24GB | AMD Ryzen 9 9950X | Metronet Fiber (West Michigan)  
**Date:** September 8, 2026  

---

## Executive Summary

Rabid Mining's video evaluates HeroMiners' newly launched Pearl mining pool, comparing it against competitor pools (AlphaMine, PearlHash), demonstrating Windows/HiveOS stratum configurations, explaining solo mining mechanics, and presenting empirical 48-hour earnings data.

Analyzing the video alongside live telemetry and network benchmarks on the operator's machine reveals **one direct, immediately executable network optimization (+59% lower latency)**, validates that the operator is **already on the highest-yielding pool**, confirms that the current **PeakMiner engine beats SRBMiner on fees and throughput**, and provides the exact mechanism for **Solo Mining** if desired.

---

## 1. Key Intelligence Extracted from Video

### A. HeroMiners Empirically Outperforms Competitors (+20.4% Yield)
- **Controlled Pool Test Results (AlphaMine vs HeroMiners):**
  - **Day 1:** AlphaMine = 2.62 PRL | HeroMiners = 2.82 PRL (+7.6%)
  - **Day 2:** AlphaMine = 2.48 PRL | HeroMiners = 3.3277 PRL (+34.2%)
  - **2-Day Total:** AlphaMine = 5.10 PRL | HeroMiners = 6.14 PRL (**+20.4% higher net earnings**)
- **Root Drivers:**
  - **0% Pool Fee Promotion:** HeroMiners operates at 0% pool fee, whereas AlphaMine, PearlHash, and others charge between **3.0% and 8.0%**.
  - **Higher Pool Hashrate & Block Frequency:** HeroMiners' larger aggregate hashrate smooths out PPLNS/PROP reward luck.
- **Operator Status:** **Verified.** The AI-BS ecosystem is already hashing to HeroMiners, capturing this +20.4% yield advantage over competing pools.

---

### B. Stratum Latency Optimization: The #1 Actionable Income Booster
- **Video Principle:** Rabid emphasizes testing stratum latency and binding strictly to the server with the lowest ping (`02:30` - *"adjust the pool based on your latency... pick the closest stratum for you"*).
- **Current Live AI-BS Configuration:**
  - `POOL1`: `us.pearl.herominers.com:1200` (US West / California)
  - `POOL2`: `eu.pearl.herominers.com:1200` (Europe)
  - `POOL3`: `as.pearl.herominers.com:1200` (Asia)
- **Empirical Network Latency Test (from Metronet Fiber in West Michigan):**

| Stratum Endpoint | Location | Measured Ping | Status |
| :--- | :--- | :--- | :--- |
| **`us2.pearl.herominers.com:1200`** | **US East (Chicago/Ashburn)** | **34 ms** | **Fastest (59% lower latency)** |
| **`ca.pearl.herominers.com:1200`** | **Canada East (Montreal/Toronto)** | **37 ms** | **Secondary (55% lower latency)** |
| `us.pearl.herominers.com:1200` | US West | 70 – 84 ms | Current primary (suboptimal) |
| `eu.pearl.herominers.com:1200` | Frankfurt / EU | 115 ms | Fallback |
| `as.pearl.herominers.com:1200` | Singapore / Asia | 225 ms | Fallback |

- **Why Latency Increases Income:**
  - In Pearl's fast-block PoUW architecture, every millisecond saved between share computation and pool receipt reduces the probability of **stale shares** (shares submitted after another miner finds the block).
  - Dropping ping from **84ms to 34ms** cuts round-trip packet flight time by more than half, ensuring immediate share registration during block difficulty updates.

---

### C. Miner Engine Evaluation: PeakMiner vs SRBMiner-MULTI v3.3.4
- **Rabid Mining Demonstration:**
  - Showcases SRBMiner-MULTI v3.3.4 running natively on Windows.
  - SRBMiner charges a **3.0% developer fee** for Pearl mining.
- **AI-BS Active Engine (`peakminer:v2.15.0` in WSL2):**
  - Custom C++/CUDA Ada Lovelace GEMM kernel specifically targeting RTX 4090 Tensor/CUDA architecture.
  - Developer fee: **2.0%** (saving **1.0% net yield** on every block mined compared to SRBMiner).
  - Current Performance: **169.4 TH/s @ 308W (549.9 GH/W)** with **100.0% share acceptance (40/40 shares)** and 51°C operating temperature.
- **Conclusion:** PeakMiner remains superior to SRBMiner for the RTX 4090 due to 1% lower dev fee and tailored matrix multiplication performance.

---

### D. Solo Mining Mechanics on HeroMiners
- **Video Walkthrough (`06:53`):**
  - Rabid highlights that HeroMiners supports on-pool solo mining without needing to compile or run a local daemon node.
  - **Syntax:** Prepend `solo:` directly to the wallet string:  
    `solo:prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5.Rig4090`
- **Solo Mining Feasibility on RTX 4090:**
  - **Pros:** When your rig solves a block, you receive 100% of the block reward directly to your wallet without sharing among pool participants.
  - **Cons (High Variance):** A single RTX 4090 (~169 TH/s) represents a fractional percentage of total network difficulty. Days or weeks could pass with 0 rewards until a block is hit.
  - **Recommendation:** Keep **PPLNS/PROP pool mining** active for consistent daily accrual, especially since the rig automatically alternates between Vast.ai ($0.44/hr), Clore.ai, and background Pearl.

---

### E. Overclock & Power Envelope Confirmation
- Rabid validates locking GDDR6X memory clocks to minimum operational frequencies for compute-bound algorithms.
- Our active configuration:
  - `nvidia-smi -lmc 5001`: Locks GDDR6X clock, saving ~40W of heat/power.
  - `nvidia-smi -pl 310`: Directs all power headroom to core clock boost (2,415 – 2,445 MHz).
  - Result: 51°C GPU temperature under continuous 169.4 TH/s load.

---

## 2. Recommended Action Items to Maximize Pearl Income

1. **Re-Order Stratum Endpoints in `Mine_Pearl.bat`:**
   - Change primary endpoint from `us.pearl.herominers.com:1200` (84ms) to `us2.pearl.herominers.com:1200` (34ms).
   - Set secondary fallback to `ca.pearl.herominers.com:1200` (37ms).
   - Set tertiary fallback to `us.pearl.herominers.com:1200` (70-84ms).
2. **Apply Stratum Re-Order to Active PeakMiner Process:**
   - Restart the WSL2 PeakMiner instance with `us2.pearl.herominers.com:1200` as primary to lock in the 34ms ping immediately.
3. **Maintain Tri-Yield Priority:**
   - Continue letting Vast.ai ($0.44/hr) and Clore.ai take precedence over Pearl, since marketplace rentals generate ~$10.56/day vs ~$0.85/day from sovereign Pearl hashing.

---

## 3. Comparison Matrix: Current vs Video-Informed Config

| Parameter | Current AI-BS Setup | Video Benchmark / Recommendation | Net Impact |
| :--- | :--- | :--- | :--- |
| **Pool** | HeroMiners (0% fee) | HeroMiners (0% fee) | Verified top-earning pool (+20.4% over AlphaMine) |
| **Primary Stratum** | `us.pearl` (84 ms) | `us2.pearl` (34 ms) | **-50 ms (-59%) latency reduction** |
| **Miner Engine** | `peakminer:v2.15.0` (2% fee) | `SRBMiner v3.3.4` (3% fee) | **PeakMiner saves +1% dev fee** |
| **Mining Mode** | PPLNS Pool Mining | PPLNS (or Solo with `solo:`) | PPLNS optimal for single RTX 4090 |
| **VRAM Clock** | Locked 5001 MHz | Low memory clock recommended | ~40W power saved, 51°C operating temp |
