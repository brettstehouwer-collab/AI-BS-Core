# Implementation Plan: Universal AV Omni-Studio (v5.194.0) - Resilient Window & Screen Capture Engine

## Problem & Background
In Universal AV Omni-Studio (`BroadcastStudio.jsx`), clicking `🎮 Capture Game / Window` or selecting a running application failed to capture or display the window/program inside the viewer (both Preview staging viewport and Program master canvas remained on fallback/standby graphics).

## Root Cause Analysis
1. **`--use-fake-ui-for-media-stream` Blocker in Launcher**:
   - In Chromium/Edge, the command-line switch `--use-fake-ui-for-media-stream` applies globally to both `getUserMedia` AND `getDisplayMedia`.
   - When `getDisplayMedia` is called with this flag, Chromium attempts to bypass the window/screen selection picker, finds no default video source specified, and immediately aborts with `NotReadableError: Could not start video source`.
   - Permanent solution: Remove `--use-fake-ui-for-media-stream` from `Launch_Desktop_Studio.bat`. Audio/video permissions for Wave Studio and webcam are guaranteed via Windows Registry Enterprise Policies (`AudioCaptureAllowedUrls` and `VideoCaptureAllowedUrls` in `HKCU\Software\Policies\Microsoft\Edge` and `Google\Chrome`), allowing `getDisplayMedia` to cleanly present the native window/screen capture selector.
2. **Hidden `<video>` Compositor Stalling (`display: none`)**:
   - The offscreen `<video>` elements used to decode frames for the HTML5 Program canvas (`previewVideoRef` and `webcamVideoRef`) had `style={{ display: 'none' }}` and lacked `autoPlay`.
   - Chromium throttles decoding on elements with `display: 'none'`, causing `video.readyState` to stall below `2` (`HAVE_CURRENT_DATA`), preventing `ctx.drawImage` from painting the frames into the Program canvas.
   - Fix: Transition hidden `<video>` elements to active offscreen styles (`position: fixed`, `width: 1px`, `height: 1px`, `opacity: 0.01`, `autoPlay`).
3. **Rigid Constraints & Silent Catch**:
   - `handleToggleScreenCapture` applied strict constraints (`displaySurface: 'window'`, `surfaceSwitching`, `selfBrowserSurface`) which can fail on certain display adapters without fallback.
   - Fix: Implement a 3-tier fallback cascade (advanced -> standard 1080p60 -> minimal `{ video: true }`), descriptive `statusMessage` updates, and cancellation handling (`NotAllowedError`).
4. **Intuitive Interaction**:
   - Make the `PREVIEW STANDBY` monitor card clickable to trigger capture directly in addition to the top bar button.

## Proposed Changes

### 1. Launcher Hardening
#### [MODIFY] [Launch_Desktop_Studio.bat](file:///C:/AI-BS/installer/Launch_Desktop_Studio.bat)
#### [MODIFY] [Launch_Desktop_Studio.bat](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_Desktop_Studio.bat)
- Remove `--use-fake-ui-for-media-stream` from `MEDIA_FLAGS`.
- Retain `--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173`.

### 2. Frontend Broadcast Studio Engine
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/BroadcastStudio.jsx)
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/components/BroadcastStudio.jsx)
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/components/BroadcastStudio.jsx)
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/components/components/BroadcastStudio.jsx)
- Update `handleToggleScreenCapture` with 3-tier fallback cascade.
- Add `useEffect` bindings for `previewVideoRef` and `webcamVideoRef`.
- Replace `display: none` on offscreen video tags with `position: fixed` active decoders with `autoPlay`.
- Wire `onClick` on Preview Standby monitor card.

### 3. Registry & Profile Verification
- Confirm Windows Registry Enterprise Policies (`AudioCaptureAllowedUrls`, `VideoCaptureAllowedUrls`, `ScreenCaptureAllowed = 1`) remain active for Edge and Chrome.

### 4. Build, Distribution & Ledger Synchronization
- Bump system version across 24 files to `v5.194.0`.
- Execute `npm run build` in `frontend/`.
- Deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Sync `frontend/dist` into `C:\Program Files\AI-BS Sovereign Studio\frontend_dist` and `installer/frontend_dist`.
- Run `package_update_payload.ps1 -Version "5.194.0"`.
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, artifact history, and chronology ledgers.

## Verification Plan
### Automated Tests
- Test `getDisplayMedia` with edge runner test script without `--use-fake-ui-for-media-stream`.
- Verify production build finishes with zero syntax/type errors.

### Manual Verification
- In Desktop Studio window: Click `🎮 Capture Game / Window` or click the `PREVIEW STANDBY` monitor card.
- Confirm native OS Window / Entire Screen picker appears.
- Select running window or screen; observe immediate live video stream in Preview Staging viewport and Program Master canvas compositor at 60 FPS.
