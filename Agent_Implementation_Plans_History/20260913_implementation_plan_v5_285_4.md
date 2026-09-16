# Implementation Plan: Unified Crypto Suite Real-Time Telemetry Parity & Profit Compounding Engine (v5.285.4)

Hardening the Unified Crypto Suite (`UnifiedCryptoHub.jsx`) across all 6 tabs to maintain active real-time data feeds and resilient WebSocket/REST fallback proxying, coupled with Option B portfolio rebalancing and pure-profit vault compounding on Crypto.com Exchange.

---

## User Review Required

> [!IMPORTANT]
> **Cloudflare Tunnel Wildcard Proxy Routing (/api/proxy/8007):**
> Browsers accessing `https://ai-bs-dashboard.web.app` block direct connections to `http://127.0.0.1:8007` and `ws://127.0.0.1:8007` due to mixed-content security policies. Routing Port 8007 through FastAPI's wildcard reverse proxy (`/api/proxy/8007/...`) allows Cloudflare Tunnel (`https://api.brettstehouwer.live`) to serve 1s telemetry and depth streaming securely anywhere.

> [!NOTE]
> **Zero-Mock Real Money Rule Compliance:**
> All portfolio figures, balances ($9.02 total portfolio, 154.0 CRO position, $0.0805 USD free cash), and HeroMiners pool metrics (5.18 B hashes, 0.3688 mature PRL) represent authentic live on-chain and exchange data.

---

## Proposed Architectural Changes

### 1. Crypto Scalp Engine Rebalancing & Profit Compounding
- `backend/crypto_trader_bot.py`:
  - Executed Option B rebalance liberating USD cash via market sell of 35 CRO at $0.05738.
  - Deployed liberated cash into dip buys (26 CRO @ $0.05739, 19 CRO @ $0.05745), expanding bag to 154.0 CRO and lowering cost basis to $0.05821 with Take Profit at $0.05871.
  - Normalized profit compounding: patched `MIN_COMPOUND_USD = 1.05` to meet Crypto.com's $1.00 notional minimum, removed artificial trade count requirements, and directed profit compounding into `long_term_vault`.

### 2. Unified Crypto Hub 6-Tab Real-Time Hardening
- `frontend/src/components/CryptoLiveStreamTab.jsx` (Tab 1):
  - Added protocol-aware proxy resolvers (`getEffectiveApiBase()`, `getBotBase()`).
  - Added dual fallback: direct WebSocket on localhost (`ws://127.0.0.1:8007`), wildcard proxy (`/api/proxy/8007`) on remote/HTTPS origins.
  - Added 1s telemetry and 1s orderbook depth polling.
  - Upgraded status badge (`● WS STREAM ONLINE (Port 8007)` / `● RADAR LIVE (Cloud Proxy 1s)`).
- `frontend/src/components/PearlMiningHubTab.jsx` (Tab 2):
  - Verified 5s polling of HeroMiners pool data and local RTX 4090 GPU metrics.
- `frontend/src/components/CryptoSwarmMobileController.jsx` (Tab 3):
  - Updated `getDaemonHost()` and `getApiHost()` with Cloudflare Tunnel proxy resolution.
- `frontend/src/components/CryptoAccountingTab.jsx` (Tab 4):
  - Added 10s auto-refresh polling and live SQLite ledger synchronization.
- `frontend/src/components/MiningDashboardTab.jsx` (Tab 5):
  - Fixed fatal `ReferenceError: getApiBase is not defined` with `getEffectiveApiBase()`.
  - Removed daemon unmount stops so background daemons remain running on tab switch.
- `frontend/src/components/GpuNetworkTab.jsx` (Tab 6):
  - Added 10s earnings polling and 15s Polygon Mainnet treasury polling.

### 3. Multi-Mirror Parity & Build Deployment
- Synchronized all 6 components across all 4 mirror trees (`frontend/src/components/`, `frontend/components/`, `frontend/src/components/components/`, `frontend/components/components/`).
- Verified 100% SHA256 parity across 426 files with `sync_mirrors.py`.
- Swept version authority `v5.285.4` across manifests and UI badges.
- Compiled Vite production bundle in 31.56s and deployed live to Firebase Hosting.

---

## Verification Plan

### Automated Verification
- `frontend/scripts/sync_mirrors.py`: 100% SHA256 parity verified across all 426 files.
- `npm run build`: Vite compiled cleanly in 31.56s with 0 errors.
- `firebase deploy --only hosting --non-interactive`: Live deployment verified on `https://ai-bs-dashboard.web.app`.

### Manual & Browser Verification
- Navigated Chrome DevTools to `http://localhost:5173/?tab=unified_crypto`.
- Verified all 6 tabs render live data without console exceptions or mixed-content blocks.
