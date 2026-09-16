# Implementation Plan - Multi-RTMP Ingest Probe Stability & Dual-Engine Failover

## Overview
Resolve the `Status: Probe failed (Daemon offline)` condition in `BroadcastStudio.jsx` during stream target connectivity testing. The root cause was an unhandled Windows asyncio proactor assertion crash (`assert f is self._write_fut`) inside `aibs_broadcast_daemon.py` triggered by cross-thread websocket broadcasting, combined with a single point of failure in `BroadcastStudio.jsx` targeting only port 8005. The solution provides event loop stabilization, native async task migration, backend fallback probing on port 8080, and automatic dual-engine failover in the UI.

## Proposed Changes

### Broadcast Engine & Daemon Stabilization
#### [MODIFY] [aibs_broadcast_daemon.py](file:///C:/AI-BS/backend/aibs_broadcast_daemon.py)
- Set Windows asyncio event loop policy to `WindowsSelectorEventLoopPolicy` at startup to eliminate ProactorEventLoop pipe assertion crashes on Python 3.12.
- Remove thread-based `asyncio.run()` calls from `_telemetry_broadcast_loop` thread that attempted to write to sockets created in the main Uvicorn event loop.
- Implement native async coroutine `run_telemetry_loop_async()` bound to the FastAPI lifecycle via `@app.on_event("startup")` using `asyncio.create_task()`.

### Core Backend High-Availability Failover
#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Implement `/stream/probe` fallback endpoint directly on port 8080.
- Add `_probe_single_rtmp_endpoint()` method supporting direct socket TCP handshakes and round-trip latency calculation against Twitch (`live.twitch.tv:1935`), YouTube (`a.rtmp.youtube.com:1935`), Facebook Live (`live-api-s.facebook.com:443`), and Kick (`fa723fc1b171.global-contribute.live-video.net:443`).

### Frontend Dual-Engine Failover & UI Sync
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/BroadcastStudio.jsx)
- Update `handleTestConnections` to probe primary daemon (`http://127.0.0.1:8005/stream/probe`).
- If primary probe fails, times out, or reports daemon offline, seamlessly fall back to `${backendUrl}/stream/probe` (port 8080).
- Synchronize changes across all mirror locations in `frontend/components/` and subdirectories.

### UI Version Parity & Ledger Updates
#### [MODIFY] [package.json](file:///C:/AI-BS/frontend/package.json)
#### [MODIFY] [TopNavbar.jsx](file:///C:/AI-BS/frontend/src/components/TopNavbar.jsx)
#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx)
#### [MODIFY] [PhoneRepairGuideTab.jsx](file:///C:/AI-BS/frontend/src/components/PhoneRepairGuideTab.jsx)
#### [MODIFY] [SystemUpdateModal.jsx](file:///C:/AI-BS/frontend/src/components/SystemUpdateModal.jsx)
- Synchronize all version indicators and badges to `v5.188.0`.

## Verification Plan
### Automated & Script Tests
- Execute real socket connection probes against all 5 stream targets on port 8005 and port 8080.
- Verify status 200 OK, online reachability, and accurate latency metrics.

### Live Production Deployment
- Build Vite frontend bundle (`npm run build`).
- Deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
