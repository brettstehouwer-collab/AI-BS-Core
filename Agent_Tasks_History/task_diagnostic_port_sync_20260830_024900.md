# Task: Diagnostic & Port Synchronization Fix (v5.146.0)

- [ ] 1. Update `backend/aibs_social_daemon.py` with `/api/social/status` and `/status` endpoints <!-- id: 1 -->
- [ ] 2. Update `BroadcastStudioApp/src/App.jsx` with ChromaDB `/api/v2/heartbeat` and Port 8088 prober <!-- id: 2 -->
- [ ] 3. Update `Launch_AI_BS.bat` to launch `aibs_broadcast_kernel.py` on Port 8088 <!-- id: 3 -->
- [ ] 4. Update `scripts/verify_boot_health.py` with `/api/v2/heartbeat` and Port 8088/8006 probes <!-- id: 4 -->
- [ ] 5. Start background daemon `aibs_broadcast_kernel.py` and restart `aibs_social_daemon.py` <!-- id: 5 -->
- [ ] 6. Sweep UI version badges to `v5.146.0` across frontend and BroadcastStudioApp <!-- id: 6 -->
- [ ] 7. Build and deploy frontend to Firebase Hosting (`firebase deploy --only hosting --non-interactive`) <!-- id: 7 -->
- [ ] 8. Build `BroadcastStudioApp` production bundle <!-- id: 8 -->
- [ ] 9. Verify live REST endpoints and health probe <!-- id: 9 -->
- [ ] 10. Update master architectural ledgers, ecosystem manual, and historical chronologies <!-- id: 10 -->
