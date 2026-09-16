# Implementation Plan - Live Broadcast Studio Pipeline, WSL2 Mirrored Port Collision Resolution & Web Player Delivery (v5.189.0)

## Overview
Enable real-time broadcast ingestion and web playback for `http://localhost/live` on StehouwerPublishing.com streaming from the AI-BS Sovereign Studio. The pipeline resolves WSL2 mirrored networking port collisions, fixes Windows Nginx worker process exhaustion, adds persistent keep-alive to WSL2, modernizes the React web player with cybernetic standby signal detection, and validates live RTMP stream ingest to HLS chunk generation.

## Proposed Changes

### WSL2 Nginx RTMP & HLS Ingest Architecture
#### [MODIFY] `/etc/nginx/nginx.conf` (WSL2 Ubuntu)
- Change HTTP HLS listener from `listen 8088;` to `listen 8089;` to resolve port collision with Windows host `aibs_broadcast_kernel.py` (which listens on 8088 in mirrored mode).
- Maintain RTMP ingestion on `rtmp://127.0.0.1:1935/live`.
- Ensure directory `/tmp/hls` exists with permissions `777` for dynamic segment creation.

### Windows Host Reverse Proxy
#### [MODIFY] [nginx.conf](file:///C:/StehouwerPublishing.com/nginx.conf)
- Update `/hls/` reverse proxy block to target `http://127.0.0.1:8089/hls/` with CORS and unbuffered streaming.
- Throttle `worker_processes` from `auto` to `2` to prevent exhausting the Windows Nginx process cap (60 workers) on 32-thread AMD Ryzen 9 9950X.

### StehouwerPublishing.com Live Player Modernization
#### [MODIFY] [LiveStream.jsx](file:///C:/StehouwerPublishing.com/website-rebuild/src/pages/LiveStream.jsx)
- Implement 5-second automatic HLS manifest poller (`HEAD /hls/stehouwer.m3u8`).
- Build cybernetic Standby HUD with pulsing radar dish, live check controls, and RTMP ingest parameters when stream is offline.
- Enable automatic live transition and error recovery when RTMP ingestion commences.
- Build production bundle (`website-rebuild/dist`).

### WSL2 Lifecycle & System Launcher
#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
- Update line 53 to execute `systemctl start nginx; sleep infinity` in detached background mode to prevent WSL2 VM auto-shutdown.
- Add startup port checks for Port 1935 (RTMP) and Port 8089 (HLS).

### Ecosystem Version Parity & Ledger Updates
#### [MODIFY] [package.json](file:///C:/AI-BS/frontend/package.json)
#### [MODIFY] [TopNavbar.jsx](file:///C:/AI-BS/frontend/src/components/TopNavbar.jsx)
#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx)
#### [MODIFY] [PhoneRepairGuideTab.jsx](file:///C:/AI-BS/frontend/src/components/PhoneRepairGuideTab.jsx)
#### [MODIFY] [SystemUpdateModal.jsx](file:///C:/AI-BS/frontend/src/components/SystemUpdateModal.jsx)
#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Synchronize all version indicators and badges to `v5.189.0`.

## Verification Plan
### Live RTMP & HLS Pipeline Test
- Ingest live audio/video test stream into `rtmp://127.0.0.1:1935/live/stehouwer` via FFmpeg.
- Confirm creation of `/tmp/hls/stehouwer.m3u8` and `.ts` chunk files.
- Fetch `http://localhost/hls/stehouwer.m3u8` through Windows Nginx and verify HTTP 200 OK.
- Build frontend and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`).

