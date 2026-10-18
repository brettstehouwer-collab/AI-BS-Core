# RTX 4090 24GB Profit Maximization Matrix (7-Day Yield Comparison)

## Hardware Profile
- **GPU:** NVIDIA GeForce RTX 4090 (24.6 GB GDDR6X)
- **CPU:** AMD Ryzen 9 9950X 16-Core / 32-Thread (5.7 GHz Boost)
- **RAM:** 64 GB DDR5 6000 MHz (52 GB allocated to WSL2)
- **Storage:** Samsung 990 Pro NVMe (4,611 MB/s read bandwidth, 860 GB allocated)
- **Uplink:** Metronet Fiber (855.5 Mbps Down / 371.7 Mbps Up)
- **Electricity Cost:** $0.00 / kWh (Zero marginal cost)

---

## 7-Day Net Profit Comparison

| Strategy | Primary Yield Mechanism | Payout Currency | 7-Day Estimated Yield | Key Pros & Cons |
| :--- | :--- | :--- | :--- | :--- |
| **1. Sovereign Pearl PoUW Mining** | 100% hashing on HeroMiners pool (~80 GH/s matrix compute) | PRL (Layer-1 Coin) | **~$5.00 – $7.00 USD** (17 – 22 PRL) | • 100% self-custody directly to local wallet.<br>• Extremely low dollar yield due to current token valuation ($0.30/PRL). |
| **2. Clore.ai Marketplace** | Background crypto rentals (often Scash / Xmrig / AI containers) | CLORE or BTC | **~$45.00 – $65.00 USD** (assuming $0.35–$0.40/hr net) | • Higher withdrawal thresholds.<br>• Slower rental pickup for non-enterprise host tiers.<br>• Renter container CPU spikes can starve host. |
| **3. Vast.ai Marketplace (Standard)** | Direct AI training, LLM fine-tuning, ComfyUI cloud rendering | USD Cash (Stripe / ACH / Crypto) | **~$55.00 – $74.00 USD** ($0.44/hr on-demand, $0.34/hr spot) | • Highest rental liquidity for single 4090s globally.<br>• Direct USD payouts without exchange bridge friction.<br>• Requires Verified badge for >80% occupancy. |
| **4. Hybrid Dual-Stack (Recommended)** | **Vast.ai Primary Rental + Automated Pearl Mining Idle Fallback** | USD Cash + PRL | **~$60.00 – $78.00 USD** | • **Zero idle hardware time:** Earns $0.44/hr when rented; automatically mines Pearl when unrented.<br>• Daemon auto-suspends miner when container starts; auto-resumes when container stops. |

---

## Optimal Pricing Architecture for Vast.ai (Machine 150272)

To maximize rental probability while preserving profitability:

1. **On-Demand Price (`-g`): $0.44 / hr ($10.56 / day)**
   - *Rationale:* Median verified RTX 4090 on-demand price on Vast.ai is $0.42–$0.48/hr. Setting $0.44 places Machine 150272 in the top 25% most attractive offers for clients seeking top-tier 9950X CPUs and gigabit uplink.
2. **Minimum Spot Bid Floor (`-b`): $0.34 / hr ($8.16 / day)**
   - *Rationale:* If no on-demand renter is active, spot bidders automatically fill the machine above $0.34/hr. This ensures the machine never sits idle at low rates.
3. **Storage Allocation (`-s`): $0.10 / GB / month**
   - *Rationale:* Industry standard on Vast. Provides additional passive yield for clients maintaining persistent container volumes.
4. **Internet Bandwidth (`-u` & `-d`): $0.01 / GB**
   - *Rationale:* Low enough to attract data-heavy training jobs (PyTorch vision / audio datasets), while covering network transport.

---

## Automated Concurrency Architecture (Zero Waste)

```
       +--------------------------------------------------------+
       |               Vast.ai Host Daemon (Ubuntu-24.04)        |
       |                Listens for Rental Containers           |
       +--------------------------------------------------------+
                                  |
            [Client Rents Container] / [Container Stops]
                                  |
                                  v
       +--------------------------------------------------------+
       |         AI-BS Concurrency Watchdog Daemon              |
       +--------------------------------------------------------+
            /                                        \
           v                                          v
   [Container Active]                         [Container Stopped / Idle]
           |                                          |
           v                                          v
   Pause Sovereign Mining                     Resume Sovereign Mining
 (kill -STOP <peakminer_pid>)               (kill -CONT <peakminer_pid>)
   -> 100% GPU to Client ($0.44/hr)           -> 100% GPU to Pearl Mining
```

---

## Required Steps to Activate
1. **List Machine 150272:**
   ```bash
   vastai list machine 150272 -g 0.44 -b 0.34 -s 0.10 -u 0.01 -d 0.01 --url https://console.vast.ai
   ```
2. **Execute Verified Self-Test:**
   - Temporarily pause `peakminer` in `Ubuntu`.
   - Run `vastai self-test machine 150272 --url https://console.vast.ai`.
   - Wait ~5–10 minutes for the PyTorch benchmark to complete.
   - Once the machine shows `Verified` with its official DLPerf score, resume `peakminer`.
3. **Activate Concurrency Watchdog:**
   - Ensure the automated loop monitors `Ubuntu-24.04` container state to manage `peakminer` signals seamlessly.
