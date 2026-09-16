# Implementation Plan: Unified Chrome Profile & DevTools Protocol Anti-Bot Authentication

Architecture plan and technical design for unifying operator Google Chrome profile data with automated tools (`chrome-devtools-mcp` / Puppeteer), eliminating Google OAuth anti-bot blocks ("This browser or app may not be secure"), and establishing seamless hybrid auto-attach.

## Architectural Root Causes Addressed

1. **Anti-Bot Automation Detection**:
   - Google's OAuth endpoints (`accounts.google.com/v3/signin/rejected`) inspect `navigator.webdriver` and browser automation command-line switches.
   - Puppeteer's default launch flags unconditionally inject `--enable-automation`, `--disable-sync`, `--password-store=basic`, and `--use-mock-keychain`.
   - `--enable-automation` sets `navigator.webdriver = true` and shows the automation banner.
   - `--disable-sync` wipes account identities in memory and disables Google account sync.
   - `--password-store=basic` and `--use-mock-keychain` prevent Chrome from accessing the Windows DPAPI master key, causing saved passwords and cookies to fail decryption.

2. **SQLite / DPAPI Session Locking**:
   - When Chrome runs daily on Windows, SQLite WAL mode and Chrome place exclusive locks (`ERROR_SHARING_VIOLATION` / Error 32) on `Network\Cookies`, `Login Data`, and `Web Data`.
   - Modern Chrome 127+ utilizes Windows App-Bound Encryption (`elevation_service.exe`), binding cookies to user data paths. Launching directly against an active locked directory causes process collision or database corruption.

---

## Technical Solutions Implemented

### 1. Zero-Automation Stealth Protocol (`tools/chrome-devtools-mcp`)
- Patched `src/browser.ts` and `build/src/browser.js` to unconditionally suppress `--enable-automation`, `--disable-sync`, `--password-store=basic`, and `--use-mock-keychain`.
- Injected stealth switch `--disable-blink-features=AutomationControlled` and `--profile-directory=Default`.
- Verified that `navigator.webdriver` evaluates to `false` and Google Sign-in loads cleanly with `Is Google Sign-in blocked?: false`.

### 2. Hybrid Port 9222 Auto-Attach Engine (`tools/chrome-devtools-mcp`)
- Patched `src/index.ts` and `build/src/index.js` with an automated port probe on `http://127.0.0.1:9222/json/version` (500ms timeout).
- **Mode A (Live Operator Attachment)**: When the operator launches Chrome via the desktop shortcut `AI-BS Developer Chrome.lnk`, it runs on Port 9222 with the operator's profile and accounts. The MCP server automatically detects and bridges directly to that running window without spawning child processes.
- **Mode B (Autonomous Stealth Launch)**: If Port 9222 is inactive, the MCP server automatically launches the developer profile autonomously using the sanitized stealth switches.

### 3. Unified Desktop Launchers & Remote Debugging
- Updated `scripts/open_developer_chrome.bat`, `scripts/open_developer_chrome.ps1`, and `AI-BS Developer Chrome.lnk` (on both OneDrive Desktop and local Desktop) to launch:
  ```powershell
  chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile" --profile-directory="Default" --no-first-run --no-default-browser-check --disable-blink-features=AutomationControlled
  ```

### 4. Full Profile & 3,358 Cookie Migration
- Executed `scripts/sync_chrome_to_developer_profile.ps1` while Chrome was closed, copying all 3,358 cookies, DPAPI master keys in `Local State`, and personal/work accounts (`Default` and `Profile 1`).

---

## Verification Plan

### Automated Verification
- Headless verification test (`C:\AI-BS\scripts\test_dev_chrome_launch.js`): Passed (`navigator.webdriver: false`, `Is Google Sign-in blocked?: false`).
- Cookie integrity check (`C:\AI-BS\scripts\check_cookies.py`): Verified 3,358 cookies in SQLite database with all 5 Google auth tokens (`SID`, `SSID`, `HSID`, `SAPISID`, `__Secure-1PSID`).
- Port 9222 probe test (`C:\AI-BS\scripts\test_remote_port.py`): Verified WebSocket debugger URL extraction on Port 9222.

### Manual Verification
- Double-click `AI-BS Developer Chrome.lnk` on the desktop.
- Verify browser opens to `Default` profile (`footballstar0325@gmail.com`) without automation banners.
- Navigate to `accounts.google.com` and verify that sign-in/passkey authentication completes without security warnings.
