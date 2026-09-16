# Task: Implement App-Level Downloader/Updater Engine

- [x] 1. Architect and compile native Go updater stub executable (`aibs_updater.exe`) in `go-core/cmd/aibs_updater/main.go` <!-- id: 1 -->
- [x] 2. Deploy `aibs_updater.exe` into `frontend/desktop-build/win-unpacked/`, `go-core/`, and `installer/` <!-- id: 2 -->
- [x] 3. Create static remote update manifest `frontend/public/updates/version.json` and payload packaging utility `scripts/package_update_payload.ps1` <!-- id: 3 -->
- [x] 4. Implement in-app updater manager and IPC handlers in `frontend/electron/main.js` and `frontend/electron/preload.js` <!-- id: 4 -->
- [x] 5. Implement REST API updater endpoints (`/api/v1/updater/*`) in FastAPI backend (`backend/routers/updater_router.py`) <!-- id: 5 -->
- [x] 6. Build interactive `SystemUpdateModal.jsx` UI and wire "Check for Updates" trigger into `TopNavbar.jsx` <!-- id: 6 -->
- [x] 7. Update firewall whitelist script `open_streaming_firewall_ports.ps1` to include `aibs_updater.exe` <!-- id: 7 -->
- [x] 8. Verify updater stub execution, PID termination, zip unpacking, and relaunch in test mode <!-- id: 8 -->
- [x] 9. Bump version to `v5.187.0`, compile frontend production bundle, and deploy to Firebase Hosting <!-- id: 9 -->
- [x] 10. Update Master Architectural Ledger, Ecosystem Manual, Artifact History, and Chronology files <!-- id: 10 -->
