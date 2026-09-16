# Implementation Plan: Browser Runtime Resilience, Broadcast Studio TDZ Resolution, CSP Web Worker Hardening & Terminal Dimension Guards

- **Version:** `v5.182.0`
- **Timestamp:** 2026-09-05 14:05:00 EDT
- **Architect:** Brett Stehouwer

## 1. Problem Statement
Client console logs revealed 5 critical runtime exceptions:
1. `ReferenceError: Cannot access 'autoDetectGame' before initialization at BroadcastStudio.jsx:199`, crashing OmniStudioTab.
2. `Tone.js worker: Creating a worker from blob:... violates Content Security Policy: worker-src was not explicitly set`.
3. `Framing '<URL>' violates Content Security Policy: frame-src 'self'`.
4. `404 Not Found on 127.0.0.1:8006/api/v1/telemetry` in `CryptoSwarmMobileController.jsx`.
5. `TypeError: Cannot read properties of undefined (reading 'dimensions')` in `xterm.js`.
6. WebSocket premature closure notices in `useSHMTelemetry.js` and `VirtualMachineTab.jsx`.

## 2. Technical Architecture & Fixes
1. **BroadcastStudio.jsx:** Reorder sticky state declarations above `fetchWindows` and `useEffect([autoDetectGame, selectedGameSource])`.
2. **index.html:** Add `worker-src 'self' blob:;`, `child-src 'self' blob:;`, and broaden `frame-src` and `media-src`.
3. **CryptoSwarmMobileController.jsx & backend:** Reroute query to port 8080 `/api/crypto/swarm-status`, mount `/api/v1/telemetry` alias, suppress console spam.
4. **TerminalPanel.jsx:** Guard `fitAddon.fit()`, defer initial writeln with `requestAnimationFrame`, safeguard teardown.
5. **WebSockets:** Check `readyState === WebSocket.CONNECTING` and attach deferred `onopen` before closing on unmount.
6. **Deployment:** Build with Vite, update badges to `v5.182.0`, and deploy live to Firebase Hosting.
