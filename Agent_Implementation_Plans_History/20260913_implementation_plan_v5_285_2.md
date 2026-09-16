# Implementation Plan: Apply Stehouwer Publishing 16-Layer Web Analytics & Telemetry Suite to The Simple Chef

Instrument John Barr's e-commerce storefront with the exact 16-layer deep web analytics and telemetry suite powering `stehouwer-publishing.com`, upgrade the backend ingestion engine to support multi-site routing (`stehouwer_publishing` vs `thesimplechef`), expand the **Web Analytics & Telemetry Suite** (`BetaAnalyticsTab.jsx`) with a sovereign site selector, and wire live e-commerce telemetry into John Barr's client dashboard (`JohnBarr.jsx`).

---

## User Review Required
> [!IMPORTANT]
> - **100% Free & Sovereign:** Just like Stehouwer Publishing, this analytics suite runs on your local host SQLite database (`site_analytics.db`), local FastAPI backend (Port 8080), and local ChromaDB embeddings (`thesimplechef_analytics_bin`). Zero Google Analytics or third-party tracking cookies required.
> - **16 Telemetry Layers Captured:**
>   1. Network & Bandwidth (4G/5G/WiFi, downlink Mbps, RTT latency)
>   2. Navigation & Edge Timings (TTFB, DNS, DOM load, Page load)
>   3. Hardware Depth (WebGL unmasked GPU model, CPU concurrency, Device memory, Retina DPR)
>   4. Display & Accessibility (Dark mode, Reduced motion, Viewport & Screen resolution)
>   5. Localization (IANA timezone, browser language)
>   6. Campaign & Attribution (UTM source/medium/campaign, organic referrers)
>   7. Streaming & Media Codecs (HLS, MSE, WebAudio support)
>   8. Bot vs Human Heuristics (velocity checks, headless/crawler detection)
>   9. Core Web Vitals (LCP, CLS)
>   10. Active Dwell Time (1-second precision tick while tab is visible)
>   11. Scroll Depth Milestones (25%, 50%, 75%, 100%)
>   12. Form Field Abandonment (partial checkout entries, contact leads)
>   13. Outbound Clicks, File Downloads (print PDF), and Copy Events
>   14. Client JavaScript Error & Promise Rejection Logger
>   15. Heatmap Click Coordinates (normalized `click_x`, `click_y`)
>   16. E-Commerce Telemetry (add to cart, drawer opens, checkout initiated, payment method selected, orders completed)

---

## Open Questions
None. The architecture directly mirrors `C:/StehouwerPublishing.com/website-rebuild/public/analytics.js` and `backend/commercial_gateway/site_analytics_router.py`.

---

## Proposed Changes

### 1. Storefront Client Telemetry Engine
#### [NEW] [E:\thesimplechef\public\analytics.js](file:///E:/thesimplechef/public/analytics.js)
- Adapt the complete 16-layer telemetry engine from Stehouwer Publishing.
- Configured for `site_id: "thesimplechef"`, default title `"The Simple Chef"`, and smart endpoint resolution (relative `/api/analytics/track` with fallback to `https://api.brettstehouwer.live/api/analytics/track` and `http://localhost:8080/api/analytics/track`).
- Expose global `window.ChefAnalytics.trackEvent(eventType, eventData)` for custom interaction tracking.

#### [MODIFY] [E:\thesimplechef\public\index.html](file:///E:/thesimplechef/public/index.html)
- Include `<script src="/analytics.js" defer></script>`.
- Instrument e-commerce interaction hooks:
  - `addToCart(name, price)`: triggers `add_to_cart` beacon with product name and price.
  - `toggleCart(open)`: triggers `cart_drawer_opened` with item count and subtotal.
  - `openCheckoutModal()`: triggers `checkout_modal_opened` with grand total.
  - `selectPayment(method)`: triggers `payment_method_swapped` (Venmo, Square, Pickup).
  - `submitOrder()`: triggers `order_submitted` beacon.
  - Koozie color swatch switches: triggers `koozie_color_selected`.
  - Masterclass video clicks: triggers `masterclass_series_clicked`.
  - Print PDF download: triggers `brand_pdf_downloaded`.

---

### 2. Backend Gateway & Ingestion Multi-Site Routing
#### [MODIFY] [backend/commercial_gateway/site_analytics_router.py](file:///c:/AI-BS/backend/commercial_gateway/site_analytics_router.py)
- Expand `site_traffic_events` schema with `site_id TEXT DEFAULT 'stehouwer_publishing'` and `domain TEXT`.
- Update `TrafficBeaconPayload` model to accept optional `site_id` and `domain`.
- Auto-detect `site_id` based on incoming `Host`, `Origin`, or payload (mapping `thesimplechef.web.app`, `thesimplecheff.com`, `thesimplechef.com`, and localhost port 8055 to `thesimplechef`).
- Update `/traffic-summary` to support filtering by `site_id`:
  - `GET /api/analytics/traffic-summary?site_id=thesimplechef`
  - `GET /api/analytics/traffic-summary?site_id=stehouwer_publishing`
  - `GET /api/analytics/traffic-summary?site_id=ALL`
- Dual-dispatch: when `site_id == "thesimplechef"`, simultaneously ingest into ChromaDB partition `thesimplechef_analytics_bin` via `chef_analytics_router` for vector semantic querying.

---

### 3. AI-BS Studio Dashboard: Web Analytics & Telemetry Suite
#### [MODIFY] [frontend/src/components/BetaAnalyticsTab.jsx](file:///c:/AI-BS/frontend/src/components/BetaAnalyticsTab.jsx)
- Add a sovereign **Site Selector Toggle** right in the header next to the title:
  - Button 1: `📚 Stehouwer Publishing`
  - Button 2: `👨‍🍳 The Simple Chef (John Barr)`
- Add dedicated sub-tabs:
  - `🌐 Stehouwer-Publishing.com Web Traffic`
  - `🌶️ TheSimpleChef.com Web Traffic (John Barr)`
- Dynamically pass `site_id` into `fetchTrafficData(selectedSiteId)`.
- Synchronize across all 4 mirror trees per Multi-Mirror Law (Rule 1).

---

### 4. Client Hub Dashboard: John Barr Analytics Integration
#### [MODIFY] [frontend/src/components/clients/JohnBarr.jsx](file:///c:/AI-BS/frontend/src/components/clients/JohnBarr.jsx)
- Enhance the **📊 Sovereign AI Analytics** tab:
  - Display the live 16-layer telemetry summary (Pageviews, Unique Visitors, Avg Dwell Time, Scroll Completion %, Web Vitals LCP/CLS, Top GPU Renderers, Heatmap coordinates) filtered specifically for `thesimplechef`.
  - Display ChromaDB Semantic Vector Query alongside the 16-layer telemetry suite.
- Synchronize across all 5 mirror locations with 100% SHA256 parity.

---

### 5. Production Build, Deployment & Parity Verification
- Deploy storefront to Firebase Hosting target `thesimplechef` (`https://thesimplechef.web.app`).
- Sync WSL2 Ubuntu Nginx `/var/www/thesimplechef/public`.
- Build Vite bundle and deploy dashboard to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
- Update `SAVED_CHECKPOINT.md` and `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.

---

## Verification Plan

### Automated Tests
1. Python test script (`scratch/test_chef_16layer_telemetry.py`):
   - Transmit synthetic 16-layer beacon with `site_id: "thesimplechef"`, WebGL GPU, TTFB, dwell time, and e-commerce `add_to_cart` event to `/api/analytics/track`.
   - Verify 200 OK and database persistence in `site_analytics.db` with `site_id = 'thesimplechef'`.
   - Query `/api/analytics/traffic-summary?site_id=thesimplechef` and assert metrics reflect the ingested event.
   - Verify ChromaDB partition receives the event.
2. Mirror parity verification:
   - Run `python frontend/scripts/sync_mirrors.py` and PowerShell `Get-FileHash` across all mirrors.

### Manual Verification
1. Load `https://thesimplechef.web.app` in Chrome DevTools / headless browser.
2. Click "Add to Cart" for Gringo Curry, open cart drawer, open checkout modal.
3. Open AI-BS Dashboard `BetaAnalyticsTab` and switch to "The Simple Chef" to verify live metrics, dwell time, and events.
