# AI-BS Sovereign Mobile Studio (`mobile-app`)

Cross-platform React Native + Expo mobile application connecting directly to the AI-BS Sovereign Cognitive Cluster (RTX 4090 / Ryzen 9 9950X).

## System Specifications
- **Expo SDK:** 57 (v57.0.21)
- **React Native:** 0.86.3
- **React:** 19.2.3
- **TypeScript:** 6.0.3 (Strict types verified via `npx tsc --noEmit`)
- **Health:** 21/21 checks passed via `npx expo-doctor`
- **Tunnel Engine:** `@expo/ngrok` (worldwide internet tunneling)
- **API Routing:** `https://api.brettstehouwer.live` & `http://192.168.4.92:8080`
- **Multi-Tenancy:** Dynamic user profile tagging (`X-Client-ID`) for isolated sessions across multiple recipients.

---

## Universal Mobile App Sharing Guide (iPhone & Android)

You can share this native mobile application with **anyone** (friends, clients, collaborators, family) on an iPhone or Android phone without an Apple Developer account, Mac hardware, or local network pairing.

### Step 1: For the Recipient (One-Time Setup on Mobile)
1. Have the recipient open the **App Store** (iPhone) or **Google Play Store** (Android).
2. Search for **"Expo Go"** (published by *650 Industries*).
3. Download and open the 100% free app.

### Step 2: For You (On Your Windows Computer)
1. Double-click [Start_Mobile_Tunnel.bat](file:///C:/AI-BS/Start_Mobile_Tunnel.bat) in `C:\AI-BS\` or run:
   ```bash
   cd C:\AI-BS\mobile-app
   npm run tunnel
   ```
2. Expo will compile the Metro JavaScript bundle, initialize the encrypted ngrok tunnel, and display:
   - A scannable **QR Code** in your terminal.
   - An active tunnel URL: `exp://...ngrok-free.app`.

### Step 3: Connecting Any Recipient's Phone
- **Option A (Camera app):** Have the recipient open their native phone **Camera** and point it at the QR code on your screen (or a screenshot sent via text/Discord). Tap the prompt that says **"Open in Expo Go"**.
- **Option B (Direct Link):** Copy the `exp://...` URL from your terminal and text, message, or email it to the recipient. Tapping the link automatically launches the app inside Expo Go.

---

## Multi-User Personalization & Session Isolation
- When anyone opens the app, they can tap their profile tag (`👤 Guest`) in the top bar to set their custom name (e.g. "Alex", "Client", "Brett").
- The app tags all outgoing requests with `X-Client-ID`, guaranteeing that different friends chatting with the AI-BS host have isolated session contexts without message bleed.

---

## Live Over-The-Air (OTA) Reloading
- While any recipient has the app open, any changes made to `App.tsx` will automatically update on their phone screen over the internet in real time!
- Shaking the device opens the Expo developer menu (for manual reload, element inspection, and performance monitoring).

---

## Other Platform Testing Options

### Preview in Browser (Chrome / Edge)
```bash
npm run web
```
*(Or press `w` in the active Expo terminal)*

---

## Architecture & Communication Flow

```
[Any Recipient: Expo Go on iPhone / Android]
       │
       │ (Over-the-Air JS Bundle via @expo/ngrok)
       ▼
[Windows PC: Metro Bundler (C:\AI-BS\mobile-app)]
       │
       │ (AI Inference & System Status Requests with X-Client-ID)
       ▼
[AI-BS Cloudflare Tunnel (https://api.brettstehouwer.live)]
       │
       ▼
[AI-BS FastAPI Core (Port 8080 / RTX 4090 GPU)]
```
