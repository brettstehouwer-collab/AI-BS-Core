# Implementation Plan - YouTube Live Studio Ingestion, Push Multi-Casting Relay, OBS Pre-Configuration & Dedicated Launcher (v5.190.0)

## Overview
Connect the user's YouTube Live account (`rtmp://a.rtmp.youtube.com/live2`, Stream Key: `je5p-8zxu-d7rj-d73s-cvu6`) across the AI-BS ecosystem. The implementation enables direct streaming, automated duplex relaying via local Nginx RTMP (rebroadcasting to YouTube Live and StehouwerPublishing.com simultaneously), automated OBS Studio profile configuration, and an interactive desktop batch launcher.

## Proposed Changes

### WSL2 Nginx Upstream RTMP Push Relay
#### [MODIFY] `/etc/nginx/nginx.conf` (WSL2)
- Added `push rtmp://a.rtmp.youtube.com/live2/je5p-8zxu-d7rj-d73s-cvu6;` under `application live`.
- Enables single-stream multi-casting: any stream sent to `rtmp://127.0.0.1:1935/live/stehouwer` is automatically sliced into HLS for `http://localhost/live` and duplicated upstream to YouTube Live in real-time.

### OBS Studio Profile Configuration
#### [NEW] `C:\Users\footb\AppData\Roaming\obs-studio\basic\profiles\Untitled\service.json`
- Pre-configured service: `YouTube - RTMPS`.
- Pre-configured server: `rtmp://a.rtmp.youtube.com/live2`.
- Pre-configured key: `je5p-8zxu-d7rj-d73s-cvu6`.

### AI-BS Broadcast Kernel
#### [MODIFY] [aibs_broadcast_kernel.py](file:///C:/AI-BS/backend/aibs_broadcast_kernel.py)
- Set `stream_key: "je5p-8zxu-d7rj-d73s-cvu6"` in `self.stream_settings`.

### Interactive YouTube Live Stream Launcher
#### [NEW] [Launch_YouTube_Live_Stream.bat](file:///C:/AI-BS/Launch_YouTube_Live_Stream.bat)
- Created desktop utility offering 4 operational modes:
  1. Direct Desktop NVENC broadcast to YouTube Live
  2. Multi-Stream Ingest (Local Nginx Relay -> YouTube + StehouwerPublishing.com)
  3. Send 60-Second 1080p60 Test Pattern & Audio Tone
  4. Launch OBS Studio

### UI Version Parity & Deployment
- Bumped ecosystem version to `v5.190.0`.
- Synchronized all UI badges and ledgers.
- Compiled frontend production bundle (`npm run build`).
- Deployed live to Firebase Hosting (`ai-bs-dashboard.web.app`).

## Verification Plan
- Tested 720p30 and 1080p60 live stream ingestion to `rtmp://a.rtmp.youtube.com/live2/je5p-8zxu-d7rj-d73s-cvu6`.
- Verified 0 dropped frames and HTTP/RTMP 200 OK handshakes.
- Verified Nginx service restart in WSL2 and OBS service.json creation.
