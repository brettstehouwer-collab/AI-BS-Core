# Task: Verify & Open Network Access Ports for Windows Application & Streaming Suite

- [x] 1. Audit current Windows Firewall rules and port filters for `C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe` and child binaries <!-- id: 1 -->
- [x] 2. Provision explicit Inbound and Outbound Windows Defender Firewall application rules for: <!-- id: 2 -->
  - `AI-BS Sovereign Studio.exe` (`C:\AI-BS\frontend\desktop-build\win-unpacked\AI-BS Sovereign Studio.exe`)
  - `brain_backend.exe` (`C:\AI-BS\frontend\desktop-build\win-unpacked\resources\brain_backend\brain_backend.exe`)
  - `aibs_engine.exe` (`C:\AI-BS\frontend\desktop-build\win-unpacked\resources\go-core\aibs_engine.exe`)
  - `ffmpeg-win-x86_64.exe` (`resources\brain_backend\_internal\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`)
- [x] 3. Provision and expand Streaming Protocol Firewall port rules (TCP & UDP): <!-- id: 3 -->
  - RTMP / RTMPS: Port 1935 (TCP Inbound/Outbound) and Port 443 (TCP Outbound)
  - Unreal Engine Pixel Streaming: Port 8888 (TCP/UDP Inbound/Outbound)
  - WebRTC Dynamic Media Stream Range: UDP Ports 10000-20000 (Inbound/Outbound)
  - Broadcast Engine & Kernel: Ports 8005, 8006, 8013, 8088 (TCP Inbound)
  - Desktop UI Server & Dev Preview: Ports 4173, 5173, 5174 (TCP Inbound)
  - OBS WebSocket & Core APIs: Ports 4455, 8000, 8080 (TCP Inbound)
- [x] 4. Create automated standalone script `C:\AI-BS\scripts\open_streaming_firewall_ports.ps1` and batch launcher `open_streaming_firewall_ports.bat` <!-- id: 4 -->
- [x] 5. Integrate automated firewall verification into `C:\AI-BS\Launch_AI_BS.bat` <!-- id: 5 -->
- [x] 6. Ensure background daemons (Broadcast Kernel 8088, Broadcast Daemon 8005, Social Daemon 8006, VST Daemon 8013) remain active and stable <!-- id: 6 -->
- [x] 7. Update UI version badges to `v5.186.0`, build frontend, deploy to Firebase Hosting <!-- id: 7 -->
- [x] 8. Update Master Ledgers, Ecosystem Manual, Artifact History, and Chronology archives <!-- id: 8 -->
