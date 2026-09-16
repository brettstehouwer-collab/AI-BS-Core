# Implementation Plan: Broadcast Studio Window Lock Resolver, Scene/Source Sync & Bitrate Verification (v5.80.0)

Address the reported issue where window capturing was defaulting to full desktop screen share rather than locking strictly to specified program windows (e.g., Call of Duty / `cod.exe`), verify Scene/Source sync across the composite pipeline, confirm Bitrate persistence across settings and scene changes, bump ecosystem version to `v5.80.0`, update master ledgers and manuals, save checkpoint, and deploy live to Firebase.

## Proposed Changes

1. **Window Lock Engine Enhancement (`backend/aibs_broadcast_daemon.py`)**:
   - Extract `.exe` process hints (e.g., `cod.exe`, `fl64.exe`, `cyberpunk2077.exe`) using regex from target strings like `"Call of Duty: Warzone (cod.exe)"`.
   - Perform bidirectional process name matching (`pname in target_lower` or `target_clean in pname`).
   - Match HWND visible windows using `win32gui.EnumWindows` to capture exact window coordinates `(offset_x, offset_y, video_size)`.

2. **Frontend Settings & Bitrate Verification (`frontend/src/components/BroadcastStudio.jsx`)**:
   - Ensure `selectedGameSource` updates cleanly pass game/window target hints.
   - Confirm `videoBitrate` and `audioBitrate` state variables remain unchanged when switching between Scene presets (`[MAIN] Game Capture`, `[CAM] Studio`, `[GAME] Split`, `[POD] 3-Way`).

3. **Ecosystem Parity & Version Bump (`v5.80.0`)**:
   - Update version badges in `App.jsx`, `Sidebar.jsx`, `TopNavbar.jsx`, `ChatTab.jsx`, `BroadcastStudio.jsx`.
   - Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
   - Save versioned manual artifact `saved_data/artifacts/20260825_AI_BS_Master_Ecosystem_Manual.md` and update `artifact_history.md`.
   - Update `SAVED_CHECKPOINT.md` with keyword `RESUME_AIBS_WINDOW_LOCK_BITRATE_SYNC_V580`.
   - Update master chronologies and top-level index.

4. **Live Deployment**:
   - Re-build Vite frontend (`npm run build`) and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
