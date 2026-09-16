# Implementation Plan: Synchronize Sovereign Studio (Program Files) & Launch Desktop Studio (Port 5173)

Synchronize the production-compiled frontend SPA bundle from `C:\AI-BS\frontend\dist` directly into the installed desktop location `C:\Program Files\AI-BS Sovereign Studio\frontend_dist` (updating the physical files from `v5.214.0` to `v5.230.0`), and launch `Launch_Desktop_Studio.bat` to spin up `serve_desktop.py` on `127.0.0.1:5173` and open the dedicated application window.

## User Review Required

> [!IMPORTANT]
> - Synchronization will mirror `C:\AI-BS\frontend\dist` into `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`. Obsolete hashed JS chunks from `v5.214.0` will be pruned to establish 100% byte-for-byte parity.
> - `Launch_Desktop_Studio.bat` will start the background Python HTTP static server on port 5173 and launch the dedicated application window.

## Proposed Changes

### Desktop Installation (`C:\Program Files\AI-BS Sovereign Studio`)

#### [MODIFY] [frontend_dist](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/frontend_dist)
- Mirror all 1,084 compiled files from `C:\AI-BS\frontend\dist` into `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
- Update `version.json` from `5.214.0` to `5.230.0`.
- Update all vendor chunks, CSS bundles, audio assets, and SPA route definitions.

### Process Execution

#### [EXECUTE] [Launch_Desktop_Studio.bat](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_Desktop_Studio.bat)
- Run `Launch_Desktop_Studio.bat` from `C:\Program Files\AI-BS Sovereign Studio`.
- Starts `serve_desktop.py 5173` if port 5173 is inactive.
- Launches Edge/Chrome in dedicated application mode `--app=http://127.0.0.1:5173`.

---

## Verification Plan

### Automated Checks
- Verify file synchronization status:
  ```powershell
  Get-Content 'C:\Program Files\AI-BS Sovereign Studio\frontend_dist\version.json'
  ```
- Test TCP connectivity to port 5173:
  ```powershell
  Test-NetConnection -ComputerName 127.0.0.1 -Port 5173
  ```
- Fetch index page from localhost:5173:
  ```powershell
  Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing | Select-Object StatusCode
  ```

### Manual Verification
- Confirm dedicated application window opens and displays the AI-BS interface at `v5.230.0` with full tab navigation.
