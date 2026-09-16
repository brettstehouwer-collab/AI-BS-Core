# Mission Specification: Permanent Suppression of pyppeteer_env Console Popups

## 1. Executive Summary
Eliminate recurring blank Windows Terminal console popups titled `C:\AI-BS\pyppeteer_env\` and establish 100% windowless, headless background daemon execution across the AI-BS ecosystem.

## 2. Root Cause Analysis
1. **Missing `CREATE_NO_WINDOW` in `DaemonManager`:**
   - In `backend/core/daemon_manager.py`, `_spawn()` executes `subprocess.Popen` with `creation_flags = (subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)`.
   - On Windows 11 with Windows Terminal set as default terminal application, any process launched without `subprocess.CREATE_NO_WINDOW` (`0x08000000`) causes Windows to allocate a console window hosted in Windows Terminal.
   - Because stdout and stderr are redirected to log files, the allocated window appears completely black with only a blinking cursor.

2. **Watchdog Duplicate Spawn & Collision Loop:**
   - `Launch_AI_BS.bat` launches `core\unified_crypto_pearl_watchdog.py`.
   - `backend/AI_BS_Backend.py` also registers `unified_crypto_pearl_watchdog.py` with `DaemonManager`.
   - `unified_crypto_pearl_watchdog.py` enforces a singleton lock. When `DaemonManager` attempts to spawn it, the second instance detects the active PID and cleanly exits.
   - `DaemonManager` detects that the process exited, interprets it as a crash, and re-spawns it on a loop, opening a new terminal window on each attempt.
   - `DaemonManager` failed to adopt the running watchdog because `unified_crypto_pearl_watchdog.py` writes its PID to `state/unified_crypto_pearl_watchdog.pid`, while `DaemonManager` looks in `backend/unified_crypto_pearl_watchdog.pid`.

3. **Console vs GUI Python Binary in Batch Launchers:**
   - `Launch_AI_BS.bat` launches background daemons using `pyppeteer_env\Scripts\python.exe` with `Start-Process -WindowStyle Hidden`.
   - On Windows 11, Windows Terminal's console broker often bypasses `WindowStyle Hidden` for console-subsystem executables (`python.exe`).
   - `pyppeteer_env\Scripts\pythonw.exe` is the native GUI subsystem binary (`IMAGE_SUBSYSTEM_WINDOWS_GUI`), which is inherently incapable of triggering console window allocations.

---

## 3. Locked Architectural Decisions (Grill Resolutions)

### Branch 1: Subprocess Windowless Guarantees
- In `backend/core/daemon_manager.py`, patch `_spawn()` to enforce:
  `creation_flags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)`
- In `Launch_AI_BS.bat` and satellite launchers, switch background daemon execution from `python.exe` to `pythonw.exe`.

### Branch 2: Process Ownership & Dynamic PID Adoption
- Harmonize `DaemonManager` to check running processes dynamically via `psutil` matching script filenames, adopting existing PIDs rather than attempting to spawn duplicate instances.
- Harmonize PID file paths to resolve both `backend/` and `state/`.

### Branch 3: Diagnostics & Crash Recovery
- For background processes launched via `pythonw.exe` in `Launch_AI_BS.bat`, redirect stdout and stderr to `logs/<service>.log` and `logs/<service>.err` to retain full silent diagnostic observability.

### Branch 4: Immediate Process Remediation
- Terminate the currently open blank terminal popup (`OpenConsole.exe` PID 38296) and execute `backend/zombie_node_cleaner.py` to clear duplicate daemon instances.
