# SafeTrade Operational Navigation & Off-Ramp Master Guide

This guide connects your current SafeTrade account interface with the centralized off-ramp and direct deposit playbooks in the repository.

---

## 1. Centralized Off-Ramp Playbooks (Now in `c:\AI-BS\docs\`)

The foundational operational guides from the previous session have been consolidated into your permanent project repository for instant reference:

- 🪙 **[Step 2: SafeTrade Exchange Setup Guide](file:///C:/AI-BS/docs/step_2_exchange_setup_guide.md)**
  *Step-by-step walkthrough for SafeTrade signup, 2FA setup, PRL deposit address retrieval, order book trading, and withdrawal.*
- 🏛️ **[Bank Direct Deposit Setup Guide](file:///C:/AI-BS/docs/direct_deposit_setup_guide.md)**
  *Walkthrough for linking your checking account via ACH to Crypto.com / Coinbase for $0-fee cash-outs.*
- 🔄 **[Crypto Off-Ramp Architecture Guide](file:///C:/AI-BS/docs/crypto_offramp_guide.md)**
  *Technical breakdown of HD wallet mechanics, Layer-1 Pearl vs smart-contract EVM tokens, and the 4-leg pipeline.*
- 📊 **[Financial Income Breakdown](file:///C:/AI-BS/docs/income_breakdown.md)**
  *Telemetry economics: daily/monthly projections (~$13.21/day net on RTX 4090) and Clore $999/day contingency listing.*

---

## 2. Active SafeTrade Modal: Exact Input Mapping

If you are currently on the **"Add Withdrawal Address"** dialog on SafeTrade:

### Configuration: POL (Polygon Native Token)
| Field | Input Value | Description |
| :--- | :--- | :--- |
| **Label** | `Crypto.com POL` | Address book label |
| **Select Asset** | `POL` | Kept as default |
| **Network** | `Polygon (POL)` | Sub-cent gas fee network |
| **Withdraw address** | `0x4761aD28A8A6b0F5F66E0825a03AA419376152aa` | Verified Crypto.com deposit address |

### Configuration: USDC (USD Coin Stablecoin)
| Field | Input Value | Description |
| :--- | :--- | :--- |
| **Label** | `Crypto.com USDC` | Address book label |
| **Select Asset** | `USDC` | Selected via asset search dropdown |
| **Network** | `Polygon` | Ensure network is Polygon |
| **Withdraw address** | `0x4761aD28A8A6b0F5F66E0825a03AA419376152aa` | Same Polygon EVM address receives USDC |

---

## 3. End-to-End Pipeline Summary

```mermaid
flowchart LR
    A["RTX 4090 Mining (310W)\nHeroMiners Stratum"] -->|Payout >= 1.0 PRL| B["Pearl Desktop Wallet\nprl1p5r4kv..."]
    B -->|Transfer PRL| C["SafeTrade Exchange\nprl1p8e3ar..."]
    C -->|Sell PRL -> USDT/USDC\nWithdraw via Polygon| D["Crypto.com App\n0x4761aD..."]
    D -->|Convert 1:1 USD\nStandard ACH ($0 fee)| E["Bank Checking Account\nDirect Deposit Cash"]
```

---

## 4. Current Telemetry Snapshot
- **Mining Rig:** Rig4090 active at 310W power cap, 5001 MHz locked memory.
- **HeroMiners Pool:** 687+ accepted shares; **0.4224 PRL** mature balance, **1.7510 PRL** pending rewards across 9 blocks.
- **Stratum Delivery:** Pool automatically broadcasts to desktop wallet upon reaching the 1.0000 PRL payout threshold.
