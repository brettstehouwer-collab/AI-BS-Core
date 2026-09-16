# Implementation Plan: Frontend Runtime Crash Remediation & CSP Hardening (v5.257.0)

Remediates two frontend runtime regressions reported in the browser console:
1. **Critical Component Crash in `ScreenwritingTab.jsx`:** `Uncaught ReferenceError: content is not defined at ScreenwritingTab.jsx:1588:23`. Caught by `TabErrorBoundary`, breaking the screenwriting workspace when the Production Breakdown or Stage Play Breakdown modals are triggered.
2. **Content Security Policy `connect-src` Violations:** `Connecting to 'http://192.168.4.92:8000/api/health'` and `'http://100.104.31.50:8000/api/health'` blocked by CSP directive in `frontend/index.html`.

---

## User Review & Proceed Option

> [!IMPORTANT]
> The proposed changes modify `frontend/index.html` to permit LAN and Tailscale connections, and update `ScreenwritingTab.jsx` and `useBackendHealth.js` across their respective mirror paths. In accordance with the **Strict Deployment Rule**, changes will trigger a production Vite compilation and live Firebase Hosting deployment (`ai-bs-dashboard.web.app`).
>
> Click the **'Proceed'** button in the artifact header or type confirmation in chat to authorize execution.

---

## Proposed Changes

### Component 1: ScreenwritingTab Runtime Crash Fix

In `ScreenwritingTab.jsx`, lines 1588 and 1596 pass `content` to `ProductionBreakdownModal` and `StagePlayBreakdownModal`:
```jsx
// Current buggy lines:
<ProductionBreakdownModal scriptText={content} onClose={() => setShowProductionBreakdown(false)} />
<StagePlayBreakdownModal scriptText={content} onClose={() => setShowStagePlayBreakdown(false)} />
```
The state variable managing the screenplay text in this component is `screenplay`. The variable `content` is undefined in this scope, throwing `ReferenceError: content is not defined`.

#### [MODIFY] [`frontend/src/components/ScreenwritingTab.jsx`](file:///c:/AI-BS/frontend/src/components/ScreenwritingTab.jsx)
- Replace `scriptText={content}` on lines 1588 and 1596 with `scriptText={screenplay || ''}`.

#### [MODIFY] [`frontend/src/components/components/ScreenwritingTab.jsx`](file:///c:/AI-BS/frontend/src/components/components/ScreenwritingTab.jsx)
- Mirror the replacement of `scriptText={content}` with `scriptText={screenplay || ''}`.

#### [MODIFY] [`frontend/components/ScreenwritingTab.jsx`](file:///c:/AI-BS/frontend/components/ScreenwritingTab.jsx)
- Mirror the replacement of `scriptText={content}` with `scriptText={screenplay || ''}`.

#### [MODIFY] [`frontend/components/components/ScreenwritingTab.jsx`](file:///c:/AI-BS/frontend/components/components/ScreenwritingTab.jsx)
- Mirror the replacement of `scriptText={content}` with `scriptText={screenplay || ''}`.

---

### Component 2: Content Security Policy (CSP) Whitelisting

In `frontend/index.html`, the `connect-src` CSP directive restricts fetch and WebSocket targets to `localhost`, `127.0.0.1`, Google, Firebase, PayPal, Archive.org, and `api.brettstehouwer.live`. When testing or running with LAN (`192.168.4.92:8000`) or Tailscale (`100.104.31.50:8000`), requests are blocked by the browser CSP.

#### [MODIFY] [`frontend/index.html`](file:///c:/AI-BS/frontend/index.html)
- Update `connect-src` to include:
  - `http://192.168.4.92:* ws://192.168.4.92:*`
  - `http://100.104.31.50:* ws://100.104.31.50:*`
  - `https://*.brettstehouwer.live wss://*.brettstehouwer.live`
- Update `media-src` and `frame-src` to include `http://192.168.4.92:*` and `http://100.104.31.50:*` for seamless local LAN asset streaming and iframe embedding.

---

### Component 3: useBackendHealth Mixed-Content & LAN Guarding

In `useBackendHealth.js`, when running on mobile or mobile emulation, `isCapacitor` evaluates to `true` (due to user-agent matching). The loop probes `['https://api.brettstehouwer.live', 'http://192.168.4.92:8000', 'http://100.104.31.50:8000']`. If the app is loaded over HTTPS, probing plain `http://` URLs triggers mixed-content rejections.

#### [MODIFY] [`frontend/src/components/useBackendHealth.js`](file:///c:/AI-BS/frontend/src/components/useBackendHealth.js)
- Guard LAN probing inside the `isCapacitor` loop: only attempt plain `http://` LAN/Tailscale IPs if `!isHttps`.
- Synchronize across all 3 mirror paths:
  - `frontend/src/components/components/useBackendHealth.js`
  - `frontend/components/useBackendHealth.js`
  - `frontend/components/components/useBackendHealth.js`

---

### Component 4: UI Version Parity, Master Ledgers & Deployment

#### [MODIFY] [`version.txt`](file:///c:/AI-BS/version.txt)
- Bump to `5.257.0`.

#### [MODIFY] Frontend Manifests & UI Version Badges
- Update version to `5.257.0` across `package.json`, `version.json`, `sw.js`, `App.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, and `ChatTab.jsx`.

#### [MODIFY] Master Ledgers
- Update [`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`](file:///c:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md) with `v5.257.0` entry.
- Update [`docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`](file:///c:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md) and save timestamped artifact to `saved_data/artifacts/`.
- Update [`MASTER_TASKS_CHRONOLOGY.md`](file:///c:/AI-BS/MASTER_TASKS_CHRONOLOGY.md), [`MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`](file:///c:/AI-BS/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md), and [`MASTER_HISTORICAL_INDEX.md`](file:///c:/AI-BS/MASTER_HISTORICAL_INDEX.md).

---

## Verification Plan

### Automated Verification
1. **Static Syntax Check:** Verify zero syntax errors across all 4 modified copies of `ScreenwritingTab.jsx` and `useBackendHealth.js`.
2. **Production Build:** Execute `npm run build` in `frontend/` to ensure zero compilation or bundling errors.
3. **Firebase Hosting Deploy:** Deploy to `ai-bs-dashboard.web.app` and confirm HTTP 200 on `/version.json`.

### Manual Verification
1. Verify `ScreenwritingTab` renders without crashing when opening the Production Breakdown or Stage Play Breakdown modals.
2. Verify browser console reports zero CSP violations for `192.168.4.92:8000` or `100.104.31.50:8000`.
