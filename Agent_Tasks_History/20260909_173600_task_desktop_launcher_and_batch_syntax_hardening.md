# Task: Decommission Outdated v5.185.0 Binary, Fix Crypto Swarm Port 8007 Collision & Ampersand Batch Syntax

- [x] Forensic inspection of `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` and process tree <!-- id: 0 -->
- [x] Forensic diagnosis of `'Vault)' is not recognized` syntax error and Port 8007 socket collision <!-- id: 1 -->
- [x] Create Implementation Plan detailing all fixes and await manual user review and approval <!-- id: 2 -->
- [x] Terminate running obsolete `AI-BS Sovereign Studio.exe` (PID 43520) <!-- id: 3 -->
- [x] Update `C:\AI-BS\Launch_AI_BS.bat` and `C:\Program Files\AI-BS Sovereign Studio\Launch_AI_BS.bat` (lines 90-100) to launch `Launch_Desktop_Studio.vbs` / `.bat` instead of the obsolete `.exe` <!-- id: 4 -->
- [x] Update desktop shortcut `AI-BS Main Workstation (Full Suite & DAW).lnk` target to `Launch_Desktop_Studio.vbs` with `app_icon.ico` <!-- id: 5 -->
- [x] Decommission obsolete `AI-BS Sovereign Studio.exe` and `resources\` folder in `C:\Program Files\AI-BS Sovereign Studio\` (reclaiming ~2.92 GB) <!-- id: 6 -->
- [x] Patch `Start_Crypto_Swarm.bat` to escape `^&` and add pre-flight check for active Port 8007 to prevent WinError 10048 socket collisions <!-- id: 7 -->
- [x] Patch `installer\Launch_Broadcast_Studio.bat` and `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` to escape `^&` in window title and echo statements <!-- id: 8 -->
- [x] Verify clean execution of `Launch_Desktop_Studio.bat` loading up-to-date UI (`v5.231.0`) on Port 5173 <!-- id: 9 -->
- [x] Bump version to `v5.232.0`, update Master Architectural Ledger, Ecosystem Manual, artifact history, and chronology indexes <!-- id: 10 -->
