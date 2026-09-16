# Operational Plan: Clore.ai Host Pricing Resolution ($999 Strike Price)

## Strategy Overview
Your objective is to establish a **$999.00/day ($41.63/hr)** strike price listing on Clore.ai so that 100% of your RTX 4090 runs sovereign Pearl mining (~290 TH/s, 395W) directly to your wallet, while maintaining an active listing that switches only if an outlier agrees to the $999 ask price.

---

## Analysis of Latest Screenshot

The screenshot confirms:
1. `Partial CPU rent` is now successfully **disabled** (`[ ] Allow partial rental`).
2. You populated `$999` across the **`Advanced`** pricing matrix.

However, two remaining configuration conflicts are triggering `Error: Missing required information` (`not_all_parameters_present`):

### 1. `Offer machine to Clore Partners` is Still Checked
- **Location:** Left panel, directly above `Partial CPU rent`.
- **Conflict:** The Clore Partners program is an enterprise service for Tier 3+ commercial data centers with 24/7 Network Operations Centers (NOC). When enabled, Clore automatically manages pricing and requires partner onboarding contracts and SLAs. Setting custom host pricing ($999) while this box is checked fails API validation because partner contract parameters are missing.
- **Required Action:** **Uncheck `Offer machine to Clore Partners`**.

### 2. Multi-Currency Toggles (`CLORE` and `BTC`) are Active
- **Location:** Inside the `Pricing` modal, above the three columns.
- **Conflict:**
  - `CLORE` toggle: **ON** (red)
  - `BTC` toggle: **ON** (red)
  - `USD` toggle: **ON** (red)
  When `CLORE` and `BTC` are active as payment methods, Clore's backend checks your account profile for configured CLORE and Bitcoin payout wallet addresses and currency settings. If those are not fully populated in your profile, the API returns `Missing required information`.
- **Required Action:**
  - Click the red toggle switch above **`CLORE`** to turn it **OFF**.
  - Click the red toggle switch above **`BTC`** to turn it **OFF**.
  - Keep **ONLY `USD`** turned **ON** (red).

---

## Exact Step-by-Step Resolution

Please execute these steps in your browser tab:

### Step 1: Uncheck Clore Partners
1. Close the `Pricing` modal (`X` in top right).
2. On the left panel, find **`Clore partner`**.
3. **Uncheck** the box `Offer machine to Clore Partners` (so the box is empty, matching `Partial CPU rent`).

### Step 2: Disable Crypto Toggles & Save USD Pricing
1. Click **`Server price`** to open the `Pricing` modal.
2. Ensure you are on the **`Advanced`** tab.
3. At the top of the columns:
   - Click the toggle switch above **`CLORE`** to **OFF** (turns grey/dark).
   - Click the toggle switch above **`BTC`** to **OFF** (turns grey/dark).
   - Keep the toggle switch above **`USD`** **ON** (red).
4. Verify that under **USD**:
   - `Minimal spot price`: `999`
   - `On Demand`: `999`
5. Click **`Apply`**.

---

## Current Workstation Status
- **GPU Utilization:** 99–100% (395W / 400W cap, 60°C).
- **Pearl Mining:** Peakminer running in WSL2, hashing directly to `prl1p5r4kvz636h2pa9fuww723s4r02flt25rec9qs6yjckk7lyejkvjs67a4n5.Rig4090`.
