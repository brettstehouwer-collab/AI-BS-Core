# Sovereign Pearl Mining Status & First On-Chain Payout Audit

**Timestamp:** 2026-09-08 08:58 EDT  
**Hardware Node:** NVIDIA GeForce RTX 4090 24GB (`Rig4090`)  
**Target Payout Wallet:** `prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5` (Brett's Pearl Desktop Wallet)

---

## 1. Confirmed Payout Milestone: First On-Chain Delivery

Overnight, the HeroMiners pool reached its 1.0000 PRL maturity threshold and broadcast the first verified on-chain payout directly to your desktop wallet:

| Field | Verified Value | Reference |
| :--- | :--- | :--- |
| **Paid Amount** | **1.99333790 PRL** | Confirmed on-chain balance in desktop wallet |
| **Transaction Hash** | `dd1b3a458a7cc1713c1b5a69df3b5db6ca1a4aabe443c2e807a1281c95b458c0` | Pearl L1 Mempool broadcast |
| **Broadcast Timestamp** | `1788856015` (2026-09-08 04:26:55 UTC) | Verified via HeroMiners API |
| **Estimated Spot Value** | **~$0.74 USD** (@ $0.37/PRL) | Net profit ($0.00 power cost) |

---

## 2. Active Pool Balance & Maturing Pipeline

Mined rewards are continuing to accumulate on HeroMiners towards the next 1.0000 PRL payout:

| Metric | Current Telemetry | Notes |
| :--- | :--- | :--- |
| **Mature Unlocked Balance** | **0.3942 PRL** | 39.42% towards the next 1.0 PRL payout |
| **Pending Block Rewards** | **0.8952 PRL** | Distributed across 4 maturing blocks |
| **Cumulative Total Mined** | **3.2827 PRL** (~$1.21 USD) | Paid (1.9933) + Mature (0.3942) + Pending (0.8952) |
| **Accepted Shares** | **1,167 good shares** | 0 invalid shares (100.0% share efficiency) |
| **Network Block Height** | **#110,416** | Pearl L1 blockchain height |
| **Closest Maturing Block** | **#110317** (99/100 confs) | Unlocks **+0.2187 PRL** in ~1 block (~3.2 min) |

---

## 3. Physical Hardware Telemetry (Active Hashing State)

The miner has reconnected to the primary pool (`us.pearl.herominers.com:1200`) and is operating at 100% matrix PoUW compute:

| Sensor | Reading | Governance Profile |
| :--- | :--- | :--- |
| **Power Draw** | **306.86 W** | Strictly bounded under **310.00 W** power cap |
| **Core Temperature** | **44°C** | 22°C below thermal throttle threshold |
| **Fan Duty Cycle** | **100%** | Full acoustic and cooling lock |
| **Graphics Core Clock** | **2,565 MHz** | Peak GEMM matrix compute speed |
| **Memory Clock** | **5,001 MHz** | Locked at 5001 MHz via NVSMI (-40W GDDR6X heat savings) |
| **GPU Utilization** | **99% – 100%** | Dedicated PoUW GEMM workload |

---

## 4. Architectural Analysis & Proposed Watchdog Patch

### Diagnosis of Overnight Socket Stall
At ~04:30 AM EDT, the stratum connection to `us.pearl.herominers.com:1200` experienced a remote socket termination (`peer closed connection without sending TLS close_notify`). Because the `peakminer` binary remained open rather than exiting with a non-zero code, `Mine_Pearl.bat`'s retry loop did not trigger, and the GPU fell back to idle (52W) until manually restarted.

### Proposed Code Enhancements (Awaiting User Consent)
1. **HeroMiners String Payment Parsing (`miners/pearl_payout_watcher.py`):**
   Update `payments` parsing to handle string colon format (`"<tx_hash>:<amount_units>:<mixin>"`) so that payout `dd1b3a45...` (1.9933 PRL) is automatically ingested into `backend/aibs_master.db` (`crypto_transfers` table) and visible in `CryptoAccountingTab.jsx`.
2. **Automated Socket Stall Auto-Recovery (`pearl_payout_watcher.py`):**
   Add a watchdog check: if the miner process is running but board power stays below 100W or pool hashrate stays at 0 for >10 minutes, automatically issue a clean recycle signal to `peakminer` to re-establish the stratum socket immediately.
