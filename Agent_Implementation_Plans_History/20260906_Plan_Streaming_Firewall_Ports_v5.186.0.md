# Implementation Plan: Windows Application Network Access & Streaming Firewall Configuration

Configure Windows Defender Firewall rules and network ports to guarantee unrestricted network connectivity when streaming from the standalone desktop application in `C:\AI-BS\frontend\desktop-build\win-unpacked`.

## Background & Problem Statement

The user is running the packaged Electron desktop application:
`C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe`
which manages live broadcast streaming (RTMP to Twitch, YouTube, Facebook, Kick, or local RTMP server), WebRTC guest video, and Unreal Engine 5.8 Pixel Streaming over WebRTC.

Currently:
1. Windows Defender Firewall has **no application filter rules** for `AI-BS Sovereign Studio.exe` or its packaged child binaries (`brain_backend.exe`, `aibs_engine.exe`, `ffmpeg-win-x86_64.exe`).
2. Existing firewall rules lack RTMP port 1935, desktop UI port 4173/5173/5174, and the dynamic WebRTC UDP port range (UDP 10000-20000) used for high-bandwidth WebRTC video/audio streaming.
3. The broadcast background daemons (ports 8005, 8006, 8013, 8088) must be guaranteed to run persistently so the desktop application never experiences connection timeouts when starting a broadcast stream.

## Proposed Changes

### Network & Firewall Layer

#### [NEW] [open_streaming_firewall_ports.ps1](file:///C:/AI-BS/scripts/open_streaming_firewall_ports.ps1)
PowerShell script executing with Administrator privileges to:
- Idempotently configure Inbound and Outbound application rules for:
  - `C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe`
  - `C:\AI-BS\frontend\desktop-build\win-unpacked\resources\brain_backend\brain_backend.exe`
  - `C:\AI-BS\frontend\desktop-build\win-unpacked\resources\go-core\aibs_engine.exe`
  - `C:\AI-BS\frontend\desktop-build\win-unpacked\resources\brain_backend\_internal\imageio_ffmpeg\binaries\ffmpeg-win-x86_64.exe`
- Idempotently configure Port rules for:
  - RTMP / RTMPS: Port 1935 (TCP Inbound/Outbound) and Port 443 (TCP Outbound)
  - Broadcast Engine & Kernel: Ports 8005, 8006, 8013, 8088 (TCP Inbound)
  - Unreal Engine Pixel Streaming: Port 8888 (TCP/UDP Inbound/Outbound)
  - WebRTC Dynamic Media Stream Range: UDP Ports 10000-20000 (Inbound/Outbound)
  - UI Server & Preview: Ports 4173, 5173, 5174 (TCP Inbound)
  - OBS WebSocket & Core APIs: Ports 4455, 8000, 8080 (TCP Inbound)
- Allow across Domain, Private, and Public profiles to prevent unexpected firewall drops on mobile/hotspot or public network profiles.

#### [NEW] [open_streaming_firewall_ports.bat](file:///C:/AI-BS/scripts/open_streaming_firewall_ports.bat)
Simple batch wrapper to run the PowerShell firewall script with execution policy bypass.

#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
Inject firewall rule verification at boot time before engine readiness checks so all ports and application binaries are guaranteed unblocked.

### Frontend UI & Version Synchronization

#### [MODIFY] Version Badges across UI Codebase
- Bump version from `v5.185.0` to `v5.186.0` in `TopNavbar.jsx`, `ChatTab.jsx`, `PhoneRepairGuideTab.jsx` and mirrors.
- Run `npm run build` and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).

### Master Ledger & Manual Synchronization
- Record entry in `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
- Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (bump to `5.186.0`).
- Persist artifact to `saved_data/artifacts/20260906_AI_BS_Master_Ecosystem_Manual_v5.186.0.md`.
- Log lineage in `NotebookLM_Records/artifact_history.md`.
- Update `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, `MASTER_HISTORICAL_INDEX.md`.

## Verification Plan

### Automated Tests
1. Execute `open_streaming_firewall_ports.ps1` via elevated PowerShell.
2. Query `Get-NetFirewallRule` and `Get-NetFirewallApplicationFilter` to verify all 8 application rules and port rules are active and enabled.
3. Test TCP connection handshakes on ports 8000, 8005, 8006, 8013, 8080, 8088, 8888, and 4173 using `Test-NetConnection`.
4. Run `npm run build` in `frontend/` to confirm zero compilation errors.
5. Deploy to Firebase Hosting and verify live deployment.
