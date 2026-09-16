# Implementation Plan: Fix On-Chain Treasury Card & Active Deposit Address Display

Replace the deprecated hot wallet address and expose the verified working Crypto.com Polygon deposit address directly within the `Server On-Chain Treasury` card in [GpuNetworkTab.jsx](file:///C:/AI-BS/frontend/src/components/GpuNetworkTab.jsx) with 1-click copy controls and block explorer links.

## User Review Required

> [!IMPORTANT]
> **Active Working Address for Transfers:**
> - **Primary Exchange Deposit Address (Crypto.com App via Polygon):**
>   `0x4761aD28A8A6b0F5F66E0825a03AA419376152aa`
>   - **Supported Assets:** USDC (Native/Bridged) and POL (MATIC).
>   - **Network:** Polygon Mainnet.
>   - **Destination:** Your linked Crypto.com retail account (ready for instant $0 ACH direct deposit to SoFi Bank).
> - **Native USDC Token Contract (Polygon):**
>   `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
> - **Server Hot Wallet Treasury Replacement:**
>   - Legacy deprecated address: `0xD6277C501465CFc329D8dd429908769718aa49FA` (0 transactions, unmonitored).
>   - Fresh active hot wallet address: `0xd269c1CE398397b441F1D4573Bd630bDd6c1e56b` (generated and encrypted via vault master key in `backend/.env`).

## Proposed Changes

### Backend Configuration

#### [MODIFY] [backend/.env](file:///C:/AI-BS/backend/.env)
- Update `PAYOUT_WALLET_PRIVATE_KEY` with the Fernet-encrypted private key for the fresh active hot wallet (`0xd269c1CE398397b441F1D4573Bd630bDd6c1e56b`), fully retiring `0xD6277C...`.
- Confirm `USDC_DESTINATION_ADDRESS=0x4761aD28A8A6b0F5F66E0825a03AA419376152aa`.

---

### Frontend UI Components

#### [MODIFY] [GpuNetworkTab.jsx](file:///C:/AI-BS/frontend/src/components/GpuNetworkTab.jsx)
- In `DESTINATION WALLET (CRYPTO.COM)`:
  - Add missing address display row: `0x4761aD28...52aa`.
  - Add **[📋 Copy Address]** button with 2-second visual feedback toast.
  - Add **[Explorer ↗]** link to Polygonscan.
  - Add green badge: `Active Off-Ramp Destination`.
- In `SERVER HOT WALLET TREASURY`:
  - Add **[📋 Copy Address]** button and updated active address display.
- In `USDC TOKEN CONTRACT`:
  - Add contract box with `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` and 1-click copy button.
- Synchronize across all 4 mirror files:
  - `frontend/src/components/GpuNetworkTab.jsx`
  - `frontend/src/components/components/GpuNetworkTab.jsx`
  - `frontend/components/GpuNetworkTab.jsx`
  - `frontend/components/components/GpuNetworkTab.jsx`

---

### Build, Deployment & Documentation

- Rebuild frontend bundle with Vite (`npm run build`).
- Deploy live to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Sync `frontend/dist` to `installer/frontend_dist`.
- Bump ecosystem manual and master architectural ledger to `v5.221.3`.

## Verification Plan

### Automated Verification
- Query `GET /v1/network/treasury-status` on backend Port 8080 to verify that both `hot_wallet.address` and `dest_wallet.address` return active addresses with live RPC balances.
- Verify that `dest_wallet.address` matches `0x4761aD28A8A6b0F5F66E0825a03AA419376152aa`.

### Manual Verification
- Inspect the updated `Server On-Chain Treasury` card in the browser or mobile view:
  - Verify `DESTINATION WALLET (CRYPTO.COM)` shows the full address `0x4761aD28A8A6b0F5F66E0825a03AA419376152aa`.
  - Click **[📋 Copy Address]** and verify the address is copied to clipboard.
  - Click **[Explorer ↗]** to open Polygonscan.
  - Click copy on the USDC token contract box.
