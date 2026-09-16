# Implementation Plan: Authorize `rottierannajoy@gmail.com` & Deploy iPhone Access

Authorize Anna Joy Rottier (`rottierannajoy@gmail.com`) across the AI-BS ecosystem security perimeter, grant mobile/dashboard access, recompile the frontend, deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`), and provide Safari PWA home-screen installation instructions for iOS.

## User Review Required

> [!IMPORTANT]
> Adding `rottierannajoy@gmail.com` to `AUTHORIZED_EMAILS` and `ADMIN_EMAILS` grants full perimeter access to the dashboard and mobile chat interface (`MobileStehouwerChat.jsx`).
> Once approved, this plan will automatically trigger the production build and `firebase deploy --only hosting --non-interactive` to update `https://ai-bs-dashboard.web.app` so she can immediately log in from her iPhone.

## Proposed Changes

### Frontend Security Perimeter & Access Control Whitelist

#### [MODIFY] [LoginModal.jsx](file:///C:/AI-BS/frontend/src/components/LoginModal.jsx) & [LoginModal.jsx (mirror)](file:///C:/AI-BS/frontend/components/LoginModal.jsx)
- Append `'rottierannajoy@gmail.com'` to `AUTHORIZED_EMAILS` array.
- Ensures Google Sign-in on iPhone admits her account and populates `localStorage` credentials instead of displaying the *"Unauthorized Email"* lock screen.

#### [MODIFY] [accessControl.js](file:///C:/AI-BS/frontend/src/components/accessControl.js) (and all 3 mirrors)
- Append `'rottierannajoy@gmail.com'` to `ADMIN_EMAILS`.
- Grants authenticated tier status, allowing mobile chat, media viewing, and core hubs.

#### [MODIFY] [antiTamperGuard.js](file:///C:/AI-BS/frontend/utils/antiTamperGuard.js)
- Append `'rottierannajoy@gmail.com'` to `AUTHORIZED_ADMIN_EMAILS` to bypass DevTools and anti-tamper restrictions.

#### [MODIFY] [AdminSecurityMonitorTab.jsx](file:///C:/AI-BS/frontend/src/components/AdminSecurityMonitorTab.jsx) (and mirrors)
- Append `'rottierannajoy@gmail.com'` to `AUTHORIZED_ADMIN_EMAILS`.

#### [MODIFY] [ThoughtfulFrictionModal.jsx](file:///C:/AI-BS/frontend/src/components/ThoughtfulFrictionModal.jsx) (and mirrors)
- Append `'rottierannajoy@gmail.com'` to `ADMIN_EMAILS`.

---

### Backend Commercial Gateway & Telemetry Router

#### [MODIFY] [admin_telemetry_router.py](file:///C:/AI-BS/backend/commercial_gateway/admin_telemetry_router.py)
- Add `"rottierannajoy@gmail.com"` to `AUTHORIZED_ADMIN_EMAILS`.

---

### Production Build & Live Firebase Deployment

- Run `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` from `C:\AI-BS\frontend`.
- Synchronize compiled `dist` into `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
- Verify live deployment status on `https://ai-bs-dashboard.web.app`.

---

### iPhone Home Screen Installation Guide (For Anna Joy)

Once deployed, Anna Joy can install AI-BS onto her iPhone as a native app:

1. **Open Safari on iPhone:** Navigate to `https://ai-bs-dashboard.web.app`.
2. **Authenticate:** Tap **Sign in with Google** and select / sign in with `rottierannajoy@gmail.com`.
3. **Open Safari Share Menu:** Tap the **Share** button at the bottom center of Safari (the square icon with an arrow pointing upward).
4. **Add to Home Screen:** Scroll down the action sheet and tap **"Add to Home Screen"**.
5. **Confirm:** Verify the name (e.g. `AI-BS`) and tap **Add** in the top-right corner.
6. **Launch:** Tap the new **AI-BS** icon on the iPhone home screen. It will open in full-screen standalone app mode without Safari browser navigation bars, maintaining persistent session access to the mobile chat and tools.

---

## Verification Plan

### Automated Verification
- Run local script verifying `rottierannajoy@gmail.com` is present in all target whitelist files.
- Inspect `npm run build` exit code `0`.
- Verify Firebase Hosting deployment succeeds with HTTP 200 on `https://ai-bs-dashboard.web.app/version.json`.

### Manual Verification
- Brett / Anna Joy navigate to `https://ai-bs-dashboard.web.app` on iPhone Safari and verify Google Sign-In with `rottierannajoy@gmail.com` passes without perimeter error.
