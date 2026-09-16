# Implementation Plan: 16-Layer Deep Web Traffic Telemetry & Intelligence Engine

Expand the web traffic collection pipeline across `stehouwer-publishing.com`, Cloudflare edge ingress, AI-BS FastAPI backend ingestion (`site_analytics_router.py`), and the AI-BS Studio Dashboard (`BetaAnalyticsTab.jsx`).

## User Review Required
> [!NOTE]
> All telemetry expansion adheres strictly to the **Ethical Product Design & User Autonomy Standard**: no intrusive fingerprinting or manipulative behavioral dwell profiling. Focus is strictly on infrastructure health, network performance, system capabilities, campaign attribution, media streaming readiness, and client-side error diagnostics.

## Scope of Telemetry Layers to Add

| Layer # | Category | Captured Data Fields |
| :--- | :--- | :--- |
| **Layer 1** | **Network & Bandwidth** | Connection Type (`effectiveType`: 4G, 5G, 3G, WiFi), Downlink Throughput (`downlink` Mbps), RTT (`rtt` ms), Save-Data flag (`saveData`) |
| **Layer 2** | **Navigation & Edge Timing** | TTFB (`responseStart - requestStart`), DNS lookup time, TCP/TLS handshake latency, DOM ready time, Total load time, Transfer size (bytes) |
| **Layer 3** | **Screen & Hardware Depth** | Viewport dimensions (`innerWidth` x `innerHeight`), Device Pixel Ratio (Retina/High-DPI), Color Depth, HDR/P3 gamut, Orientation, Touch Points |
| **Layer 4** | **Accessibility & Display** | Dark Mode preference (`prefers-color-scheme: dark`), High Contrast preference (`prefers-contrast`), Reduced Motion preference |
| **Layer 5** | **Localization & Regional** | IANA Timezone (e.g. `America/Detroit`), Timezone UTC offset minutes, Browser languages array |
| **Layer 6** | **Campaign & Attribution** | UTM Parameters (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`), Ad Click IDs (`gclid`, `fbclid`, `ttclid`, `msclkid`) |
| **Layer 7** | **Streaming & Media Readiness** | Native HLS support (`video.canPlayType`), MediaSource Extensions (MSE), WebCodecs support, WebAudio context support |
| **Layer 8** | **Live Stream Player Telemetry** | `/live` player state events (`stream_play`, `stream_pause`, `stream_buffering`, `stream_quality_change`, `stream_error`) |
| **Layer 9** | **Client Error Diagnostics** | Global JS error catcher (`window.onerror`), Unhandled Promise rejections (`unhandledrejection`), Resource load failures |
| **Layer 10** | **Engagement & Conversions** | Outbound link clicks (Amazon, Goodreads, Socials), Sample book/PDF downloads, Text copy events (quotes, titles), Tab visibility duration |
| **Layer 11** | **Cloudflare Edge Telemetry** | `CF-Ray` request ID, `CF-IPCountry`, `CF-Visitor` (TLS / HTTP version), `Sec-CH-UA` client hints (OS, architecture, model) |

---

## Proposed Changes

### 1. Client-Side Telemetry Engine
#### [MODIFY] [public/analytics.js](file:///C:/StehouwerPublishing.com/website-rebuild/public/analytics.js)
#### [MODIFY] [dist/analytics.js](file:///C:/StehouwerPublishing.com/website-rebuild/dist/analytics.js)
- Upgrade tracking script from 10-layer to 16-layer architecture.
- Instrument `PerformanceObserver` and `PerformanceNavigationTiming` to capture TTFB, DNS, and load milestones.
- Add Network Information API telemetry (`navigator.connection`).
- Parse UTM parameters and referrer strings into normalized attribution objects.
- Probe media engine capabilities (HLS, MSE, WebAudio).
- Register global listeners for JS errors, unhandled rejections, file downloads, outbound link clicks, and copy events.
- Hook into `/live` video elements to capture live playback health.

### 2. Backend Gateway & Database Schema
#### [MODIFY] [site_analytics_router.py](file:///C:/AI-BS/backend/commercial_gateway/site_analytics_router.py)
- Expand `site_traffic_events` table in `site_analytics.db` with non-destructive `ALTER TABLE` migrations:
  - `network_type TEXT`, `downlink_mbps REAL`, `rtt_ms INTEGER`, `ttfb_ms INTEGER`, `dns_ms INTEGER`, `dom_load_ms INTEGER`, `page_load_ms INTEGER`, `device_pixel_ratio REAL`, `color_depth INTEGER`, `dark_mode INTEGER`, `timezone TEXT`, `language TEXT`, `utm_source TEXT`, `utm_medium TEXT`, `utm_campaign TEXT`, `hls_supported INTEGER`, `cf_ray TEXT`, `cf_country TEXT`, `cf_proto TEXT`, `error_message TEXT`.
- Extract Cloudflare headers (`CF-Ray`, `CF-IPCountry`, `CF-Visitor`, `Sec-CH-UA`) from incoming requests.
- Expand `/api/analytics/traffic-summary` response payload to aggregate:
  - `network_metrics` (average TTFB, RTT, connection type distribution)
  - `attribution_metrics` (top UTM campaigns, sources, mediums)
  - `streaming_readiness` (percentage of HLS/MSE capable viewers)
  - `client_diagnostics` (dark mode percentage, Retina percentage, top timezones)
  - `recent_errors` (recent frontend exceptions)

### 3. AI-BS Studio Frontend Dashboard
#### [MODIFY] [BetaAnalyticsTab.jsx](file:///C:/AI-BS/frontend/components/BetaAnalyticsTab.jsx) (and mirrored copies in `frontend/src/components/`, `frontend/components/components/`)
- Add visualization sub-cards to the Web Analytics Tab:
  - **Network & Edge Latency Meter**: Gauges for TTFB, RTT, and Network Type (4G/5G/WiFi).
  - **Campaign & Attribution Matrix**: Table of active UTM sources, mediums, and campaigns.
  - **Media & Live Streaming Readiness**: HLS compatibility percentage and playback events.
  - **Environment & Accessibility**: Dark mode %, Retina display %, Timezone distribution.
  - **Live Client Error Log**: Real-time ticker of JavaScript errors or media playback stalls.

### 4. Version Bump & System Deployment
- Increment system version from `v5.190.0` to `v5.191.0`.
- Sweep all frontend UI files and update version badges.
- Rebuild StehouwerPublishing static website (`npm run build`).
- Build frontend production bundle (`npm run build` in `C:\AI-BS\frontend`).
- Deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.

---

## Verification Plan

### Automated Tests
1. Direct Python synthetic beacon verification sending complete 16-layer JSON payload to `https://api.brettstehouwer.live/api/analytics/track`.
2. Inspect `site_analytics.db` to verify all 16 new columns are correctly populated.
3. Validate `/api/analytics/traffic-summary` endpoint returns the new aggregated telemetry blocks.

### Manual Verification
1. Load `https://stehouwer-publishing.com/` in a browser and verify HTTP 200 OK.
2. Load `https://stehouwer-publishing.com/live` and verify player events and media telemetry trigger beacons.
3. Open AI-BS Dashboard (`https://ai-bs-dashboard.web.app` or `http://localhost:5173`) and verify the updated Web Analytics tab renders all new telemetry cards.
