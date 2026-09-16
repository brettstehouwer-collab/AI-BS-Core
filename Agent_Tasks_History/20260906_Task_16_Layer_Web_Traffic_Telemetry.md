# Task: Deep Web Traffic Telemetry Expansion (16-Layer Suite)

## Objectives
1. Expand web traffic capture on `https://stehouwer-publishing.com/` from basic pageviews to 16-layer comprehensive diagnostic, performance, network, media, attribution, and error telemetry.
2. Upgrade `analytics.js` in `public` and `dist` of `C:\StehouwerPublishing.com\website-rebuild`.
3. Expand backend ingestion schema in `site_analytics_router.py` and `site_analytics.db` to log network speed, TTFB, UTM campaigns, screen/hardware specs, timezones, streaming codecs, and JS errors.
4. Enhance `BetaAnalyticsTab.jsx` with visualization cards for Network Quality, UTM Attribution, Live Stream Player Readiness, and Error Telemetry.
5. Bump version to `v5.191.0`, synchronize master architectural ledgers, build frontend, and deploy to Firebase Hosting.

## Status: COMPLETED

## Todo List
- [x] Research & draft Implementation Plan <!-- id: 0 -->
- [x] Update `analytics.js` with 16-layer telemetry capture <!-- id: 1 -->
- [x] Migrate `site_analytics.db` schema and update `site_analytics_router.py` <!-- id: 2 -->
- [x] Update `BetaAnalyticsTab.jsx` with new telemetry telemetry visualizations <!-- id: 3 -->
- [x] Build website `dist` and verify local Nginx serving <!-- id: 4 -->
- [x] Test end-to-end telemetry ingestion via live HTTP/HTTPS test beacons <!-- id: 5 -->
- [x] Sync UI version badges to `v5.191.0` and compile frontend bundle <!-- id: 6 -->
- [x] Deploy to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 7 -->
- [x] Update Master Architectural Ledger & Ecosystem Manual <!-- id: 8 -->
- [x] Archive Task & Implementation Plan into historical directories <!-- id: 9 -->
