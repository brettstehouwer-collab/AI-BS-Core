# Implementation Plan: Stehouwer Wave Studio (v5.193.0) - Live Recording Microphone Permissions & Resilient Audio Ingestion Engine

## Problem & Background
In Stehouwer Wave Studio (`StehouwerWaveStudio.jsx`), clicking 'Record Stem' in the desktop application environment (`http://127.0.0.1:5173`) triggered an alert dialog:
`Microphone access was denied or not supported by this browser.`

## Root Cause Analysis
1. **Edge/Chromium `--app` Window Mode Permission Trap**: In standalone app mode, the browser address bar and security lock icon are omitted. Once a site permission is denied or dismissed, Chromium persists `{"setting": 2}` (Blocked) in `C:\Users\footb\AppData\Local\AI_BS_Studio\DesktopProfile\Default\Preferences` under `profile.content_settings.exceptions.media_stream_mic`. Without the address bar, the user cannot manually click the lock icon to reset it.
2. **Missing Media Autogrant Launcher Flags**: `Launch_Desktop_Studio.bat` previously lacked `--use-fake-ui-for-media-stream` and `--unsafely-treat-insecure-origin-as-secure`.
3. **Generic UI Error Handling**: `StehouwerWaveStudio.jsx` bundled all capture rejections into a single generic alert without distinguishing between blocked permissions and absent hardware.

## Architecture & Implementation
1. **Profile Permissions Enforcer**:
   - Python script (`scratch/check_and_fix_prefs.py`) updates both `DesktopProfile` and `BroadcastProfile` `Preferences` to `setting: 1` (Allow) for `http://127.0.0.1:5173,*`, `http://localhost:5173,*`, and `https://ai-bs-dashboard.web.app,*`.
2. **Launcher Media Flags**:
   - Inject `set "MEDIA_FLAGS=--use-fake-ui-for-media-stream --unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173"` into `Launch_Desktop_Studio.bat` (source repository and `C:\Program Files\AI-BS Sovereign Studio\`).
3. **Resilient Wave Studio Recording Engine**:
   - Modern `navigator.mediaDevices.getUserMedia` with fallback to legacy `navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia`.
   - Actionable diagnostic error alerts distinguishing `NotAllowedError` vs `NotFoundError`.
   - Synchronize across all 4 frontend directory trees.
4. **App-Level In-Place Updater & Cloud Deployment**:
   - Bump system version across 24 files to `v5.193.0`.
   - Compile frontend production bundle (`npm run build`).
   - Deploy live to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
   - Package delta update archive (`aibs_update_payload.zip`) with ZIP64 support.
   - Synchronize Master Architectural Ledger, Ecosystem Manual, artifact history, and chronology ledgers.
