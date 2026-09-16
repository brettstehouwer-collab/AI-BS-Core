# 🤖 AGENT & DEVELOPER DIRECTIVE: Android Studio Build & Release

**Project Name:** Stehouwer Digital Storefront & Micro-SaaS Native Android App  
**Package Name:** `com.stehouwerpublishing.digitalstorefront`  
**Target Root Directory:** `C:\AI-BS\frontend\android`  
**Parent Workspace:** `C:\AI-BS`  

---

## 🎯 Primary Directive & Objective

You are inspecting or building the **Stehouwer Digital Storefront** native Android application generated via Capacitor v6. 

Your objective is to:
1. Ensure all Gradle dependencies and Android SDK components sync cleanly.
2. Compile the debug APK for local hardware testing.
3. Generate the signed production release Android App Bundle (`.aab`) for Google Play Console submission.

---

## 📂 Critical Repository File Paths

| File / Component | Absolute Local Path | Function |
| :--- | :--- | :--- |
| **Android Manifest** | `app/src/main/AndroidManifest.xml` | Application permissions, package identity, and main entry activity (`BridgeActivity`). |
| **App Build Script** | `app/build.gradle` | Specifies `minSdkVersion 22`, `targetSdkVersion 34`, `versionCode`, and `versionName`. |
| **Web Production Assets** | `app/src/main/assets/public` | Contains Vite-compiled production distribution HTML/JS/CSS (`dist`). |
| **Capacitor Configuration** | `app/src/main/assets/capacitor.config.json` | Specifies Capacitor webDir, scheme (`https`), and appId. |
| **Debug APK Output** | `app/build/outputs/apk/debug/app-debug.apk` | Target output path for test `.apk`. |
| **Release AAB Output** | `app/build/outputs/bundle/release/app-release.aab` | Target output path for Google Play Console submission `.aab`. |

---

## ⚡ Step-by-Step Execution Protocol

### Directive Step 1: Open Project & Execute Gradle Sync
* Open `C:\AI-BS\frontend\android` in Android Studio.
* Run Gradle Sync (`File -> Sync Project with Gradle Files`).

### Directive Step 2: Compile Debug APK
* Select **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
* Output binary location: `app/build/outputs/apk/debug/app-debug.apk`.

### Directive Step 3: Compile Signed Release Bundle (.aab)
* Select **Build -> Generate Signed Bundle / APK...**.
* Select **Android App Bundle**.
* Load or generate KeyStore at `C:\AI-BS\stehouwer_play_store_key.jks`.
* Build Variant: `release`.
* Output bundle location: `app/build/outputs/bundle/release/app-release.aab`.

### Directive Step 4: Sync Web Code Updates (If Web Frontend Changes)
If changes are made to `C:\AI-BS\frontend\src` or `components/`, execute from `C:\AI-BS\frontend`:
```powershell
npm run build
npx cap copy android
```
This updates `app/src/main/assets/public` instantly before compiling the next APK!
