# Hardware Tuning & Income Maximization Strategy for Pearl (PRL)
**Target Hardware:** NVIDIA GeForce RTX 4090 24GB (Factory TDP: 450W, Max: 600W) | AMD Ryzen 9 9950X  
**Operating System:** Windows 11 Host + WSL2 Ubuntu  
**Electricity Cost:** $0.00 / kWh (Zero marginal cost)  
**Date:** September 8, 2026  

---

## Executive Summary

Live telemetry reveals that under the current **310W power clamp**, the RTX 4090's graphics core clock is being throttled down to **1,995 MHz** (from its native 2,700+ MHz boost capability) because compute-heavy matrix GEMM operations hit the 310W board budget.

Because your **electricity cost is $0.00/kWh**, lifting this power limit and applying a GPU core clock offset represents the **single largest untapped lever to increase your Pearl income (+25% to +35% hashrate)** while keeping thermals safely below 60°C.

---

## 1. Setting 1: Board Power Limit (310W vs 360W vs 400W)

### The Technical Reality
- The RTX 4090 factory default power limit is **450W** with a hardware ceiling of **600W**.
- At **310W**, the card runs at only **68.8%** of factory TDP, causing core clocks to drop to **1,995 MHz** during heavy matrix multiplication.
- In Pearl PoUW, hashrate scales near-linearly with Core Clock TFLOPS.

| Configuration | Board Power Limit | Expected Graphics Core Clock | Estimated Hashrate | Expected Temp | Net Income Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Current Baseline** | **310 W** | ~1,995 – 2,355 MHz | ~170 TH/s | 51 – 54°C | Baseline (~$0.85/day) |
| **Balanced Boost** | **360 W** (+16%) | ~2,450 – 2,600 MHz | ~205 – 215 TH/s | ~56 – 58°C | **+20% to +25% More PRL** |
| **Max Safe Compute** | **390 – 400 W** (+29%) | ~2,650 – 2,775 MHz | ~230 – 245 TH/s | ~59 – 62°C | **+30% to +38% More PRL** |

> [!NOTE]
> NVIDIA's thermal throttle point is 84°C, and maximum junction is 90°C. Even at 390W, running at 100% fan speed keeps your RTX 4090 around 59–62°C, well within safe parameters.

---

## 2. Setting 2: Positive GPU Core Clock Offset (`+100` to `+150 MHz`)

### How It Works
- By applying a positive core clock offset (e.g., `+120 MHz` via `nvidia-smi` or PeakMiner's `--gpu-core0 120`), the GPU achieves higher clock speeds at any given voltage tier along the V/F (voltage-frequency) curve.
- This acts as an undervolt: it extracts **higher hashrate without increasing total power consumption**.
- **Net Impact:** Additional **+3% to +5% hashrate** on top of power limit adjustments.

---

## 3. Setting 3: VRAM Memory Clock Lock (`5001 MHz` - Keep Locked)

### Why NOT to increase memory clock
- RTX 4090 GDDR6X runs at 10,251 MHz by default.
- Pearl PoUW is **pure compute matrix multiplication (GEMM)**; it does not saturate VRAM bandwidth.
- Unconstraining memory to 10,251 MHz wastes **~40W of power on memory chips**, which steals wattage away from the core and increases heat.
- **Recommendation:** **Keep `5001 MHz` locked.** It guarantees all available power goes directly to the compute cores.

---

## 4. Setting 4: Connection & Telemetry Parameters

1. **Stratum Ping Optimization (Already Active):**
   - Connected to `us2.pearl.herominers.com:1200` at **34–44 ms** (down from 84 ms).
   - Keeps share reject rate at **0.0%**.
2. **Pool Dashboard Telemetry (`--report-stats`):**
   - Enabling `--report-stats` pushes per-GPU hashrate, temperatures, and fan speeds directly to the HeroMiners web dashboard.
3. **Process Priority (`nice -n -10`):**
   - Granting high scheduling priority to PeakMiner inside WSL2 prevents any Windows background tasks from causing micro-stutter in CUDA kernel dispatch.

---

## 5. Summary of Recommended Tuning Profiles

### Profile A: Balanced High Yield (Recommended)
- **Power Limit:** `360 W` (`nvidia-smi -pl 360`)
- **Core Offset:** `+100 MHz` (`--gpu-core0 100`)
- **Memory Clock:** `5001 MHz Locked` (`nvidia-smi -lmc 5001`)
- **Expected Hashrate:** **~210 TH/s** (vs 170 TH/s baseline)
- **Expected Temp:** **~56°C**
- **Income Gain:** **~+20% to +24% more PRL mined**

### Profile B: Maximum Aggressive Yield
- **Power Limit:** `390 W` (`nvidia-smi -pl 390`)
- **Core Offset:** `+135 MHz` (`--gpu-core0 135`)
- **Memory Clock:** `5001 MHz Locked` (`nvidia-smi -lmc 5001`)
- **Expected Hashrate:** **~235 – 245 TH/s** (vs 170 TH/s baseline)
- **Expected Temp:** **~59°C**
- **Income Gain:** **~+35% to +40% more PRL mined**

---

## 6. How to Proceed
Please select your preferred profile:
1. **Profile A (360W / +100MHz Core / ~210 TH/s / ~56°C)**
2. **Profile B (390W / +135MHz Core / ~240 TH/s / ~59°C)**
3. **Keep current 310W baseline profile**
