# Implementation Plan: Migrate Chrome Browser Profile to Developer Chrome

Migrate user profile data (active logins, cookies, bookmarks, history, web storage, extensions, and sessions) from the primary Google Chrome installation to the automated developer Chrome instance used by the AI-BS ecosystem and `chrome_devtools` MCP server.

## User Review Required

> [!IMPORTANT]
> **Temporary Chrome Shutdown Required**: Chrome places exclusive OS-level file locks on `Network\Cookies`, `History`, `Web Data`, and `Login Data` while active. Both standard Google Chrome and any background developer Chrome processes must be closed for approximately 10–15 seconds during the copy operation to ensure zero file corruption and clean WAL commit.

> [!WARNING]
> **Profile Size Optimization (29 GB vs 150 MB)**:
> Your primary Chrome profile (`Default`) currently occupies **29.17 GB**. 
> - **23.8 GB** consists of temporary video blobs from `videoeditor.streamlabs.com` in `IndexedDB`.
> - **1.4 GB** consists of temporary video blobs from `app.visla.us`.
> - **~1.2 GB** consists of disposable network/code caches (`Cache`, `Code Cache`).
> 
> **Recommended Approach**: Transfer all authentication sessions, cookies, passwords, bookmarks, history, extensions, preferences, and local storage, while excluding disposable video editor caches and network caches. This transfers in **~3 seconds** and takes **~150 MB**.
> If you prefer a 100% raw byte-for-byte clone including the 25 GB video cache, that can be selected instead.

---

## Open Questions & Configuration

> [!NOTE]
> Select your preferences or click Proceed with the recommended defaults:
> 1. **Data Scope**:
>    - **Option A (Default / Recommended)**: Fast & lean migration (~150 MB, ~3 seconds) copying `Local State` (DPAPI keys), all cookies, saved logins, bookmarks, history, extensions, sessions, and web storage while filtering disposable caches and 25 GB video editor temp blobs.
>    - **Option B**: Full raw clone of the entire 29 GB tree (~5 minutes).
> 2. **Profile Inclusions**:
>    - **Both Profiles (Recommended)**: Personal (`Default` - `footballstar0325@gmail.com`) and Work (`Profile 1` - `brett.stehouwer@ubreakifix.com`).
>    - **Personal Only**: `Default` profile only.

---

## Proposed Changes

### Automation & Ecosystem Scripts

#### [NEW] [sync_chrome_to_developer_profile.ps1](file:///C:/AI-BS/scripts/sync_chrome_to_developer_profile.ps1)
- Reusable PowerShell script that:
  1. Checks for running Chrome instances (`chrome.exe`) and terminates/prompts cleanly.
  2. Creates a timestamped safety backup of `C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile`.
  3. Copies `Local State` (containing `os_crypt` DPAPI encryption keys required for decrypting passwords and cookies under the current Windows user).
  4. Copies `Default` and `Profile 1` profile directories.
  5. Strips source lock files (`lockfile`, `DevToolsActivePort`, `CrashpadMetrics-active.pma`) so the target profile boots cleanly in devtools without process collision errors.
  6. Supports `-Fast` switch (default) to bypass bloated transient caches and massive video editor blobs, or `-Full` for raw byte-for-byte copy.

---

### Master Ledgers & Documentation

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Log timestamped entry detailing developer Chrome profile migration, paths, DPAPI key preservation, and sync script specifications.

#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Update manual with operating instructions for syncing browser profile data to the developer Chrome instance.

---

## Verification Plan

### Automated Verification
- Verify backup directory exists in `C:\Users\footb\.cache\chrome-devtools-mcp\`.
- Verify key files exist in target:
  - `C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Local State`
  - `C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Network\Cookies`
  - `C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Bookmarks`
  - `C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile\Default\Login Data`
- Verify absence of stale `lockfile`.

### Manual Verification
- Launch developer Chrome via `chrome-devtools-mcp` or browser automation tool.
- Confirm browser opens with logged-in user state, bookmarks bar, and account profiles accessible.
