# Project Directive: Native Windows Desktop Architecture Enforcement (October 7 Vocal Studio)

## 1. Zero Browser Engines (Strict Prohibition)
- **NEVER** use Chromium, Chrome, Electron, CEF, Edge WebView2, Tauri, or browser tabs.
- **NEVER** wrap HTML/CSS/JavaScript in a desktop window or webview container.
- The DAW must remain a pure, native Windows desktop application with zero browser-induced latency.

## 2. Zero Local Web Servers
- **NEVER** spin up local web servers (Flask, FastAPI, Node.js, Express) serving `localhost` ports to power the DAW.
- Audio and control data must reside in direct shared memory, not HTTP/WebSocket IPC.

## 3. Native Win32 / PyQt6 GUI
- Render the DAW interface directly using **PyQt6 (`QtWidgets`)** via Windows OS window handles (`HWND`) and Direct2D / GDI+.
- Preserve all master headers, 5-card modular FX strips, 4-stem vocal tracks, synced prompter lyrics with breath cues, pitch strobe centering, and performance diagnostics.

## 4. Hardware Audio & MMCSS Threading
- Route live audio directly via **WASAPI Exclusive / ASIO** at 128 frames ($2.67\text{ ms}$ @ 48 kHz).
- Elevate callback thread priority to **MMCSS "Pro Audio" (Priority 15)**.
- Use pre-allocated, lock-free Single-Producer Single-Consumer (SPSC) circular ring buffers.

## 5. VST3 Host Integration
- Host 64-bit VST3 plugins natively in-process via Spotify `pedalboard` (C++ JUCE backend).
- Render plugin manufacturer editor GUIs directly using `plugin.show_editor()` as native Windows frames.

## 6. Standalone Executable Deployment
- Deploy releases as standalone, signed Windows binaries: `October7_VocalStudio_Native.exe` in `C:\Program Files\October7_VocalStudio_DAW\`.
