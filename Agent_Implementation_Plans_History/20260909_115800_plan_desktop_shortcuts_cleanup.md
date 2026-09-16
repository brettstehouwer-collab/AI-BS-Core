# Implementation Plan: Desktop Shortcuts Consolidation & Obsolete Version Storage Reclamation

An audit of the 18 desktop shortcuts requested by the user and the installed versions in `C:\Program Files` was performed to identify redundant shortcuts, OneDrive sync collision duplicates, obsolete targets, and reclaimable disk storage.

---

## Audit Findings: Installed Versions & Storage Consumption

| Installation Directory | Version / Date | Size on Disk | Active Status & Rationale |
| :--- | :--- | :--- | :--- |
| **`C:\Program Files\AI-BS Sovereign Studio`** | **`v5.230.1`** (Sept 9, 2026) | **4.43 GB** | 🟢 **ACTIVE & PRIMARY**: Current sovereign full-stack desktop suite. Houses `serve_desktop.py`, `AI-BS Sovereign Studio.exe`, `frontend_dist` (v5.230.0), and core daemons. |
| **`C:\Program Files\BS-Studio`** | **`v5.148.0`** (Aug 30, 2026) | **3.10 GB** | 🟢 **ACTIVE**: Dedicated standalone Broadcast Studio & Music DAW workstation. |
| **`C:\Program Files\AI-BS Matrix`** | **`v5.133.0`** (Aug 29, 2026) | **3.03 GB** | 🔴 **OBSOLETE & REDUNDANT**: Legacy predecessor to Sovereign Studio. Completely superseded by `C:\Program Files\AI-BS Sovereign Studio`. Reclaiming this folder frees **3.03 GB** of storage on Drive C:. |

---

## Audit Findings: 18 Desktop Shortcuts Breakdown

On Windows 11 with OneDrive Desktop Backup enabled, the desktop displays the **union** of `C:\Users\Public\Desktop` and `C:\Users\footb\OneDrive\Desktop`. When identical shortcuts exist in both, or when OneDrive creates numbered `(2).lnk` sync duplicates, the desktop becomes severely cluttered with duplicate icons.

| # | Shortcut File Path | Target Executable / Script | Classification | Proposed Action |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `C:\Users\Public\Desktop\AI-BS Shutdown.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Shutdown_Desktop_Studio.bat` | Public / User Duplicate | 🗑️ **DELETE** (Keep #16 on OneDrive Desktop) |
| 2 | `C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` | Public / User Duplicate | 🗑️ **DELETE** (Keep #13 on OneDrive Desktop) |
| 3 | `C:\Users\Public\Desktop\BS-Studio.lnk` | `C:\Program Files\BS-Studio\BS-Studio.exe` | Public / User Duplicate | 🗑️ **DELETE** (Keep #9 on OneDrive Desktop) |
| 4 | `C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand.lnk` | `C:\AI-BS\Launch_Unreal_OnDemand.bat` | Valid Primary Launcher | ✅ **KEEP** (Clean rename to `AI-BS Unreal On-Demand.lnk`) |
| 5 | `C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut.lnk` | `C:\AI-BS\Launch_AI_BS.bat` | Primary Master Dev Launcher | ✅ **KEEP & STANDARDIZE** as `AI-BS Matrix Boot.lnk` |
| 6 | `C:\Users\footb\OneDrive\Desktop\Start Crypto Swarm.lnk` | `C:\AI-BS\Start_Crypto_Swarm.bat` | Valid Primary Launcher | ✅ **KEEP** |
| 7 | `C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk` | `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` | Public / User Duplicate | 🗑️ **DELETE** (Keep #14 on OneDrive Desktop) |
| 8 | `C:\Users\footb\OneDrive\Desktop\Stehouwer Publishing AI-BS Matrix.lnk` | `chrome_proxy.exe ... --enable-automation` | Stale PWA (Anti-Bot Flagged) | 🗑️ **DELETE** (Superseded by `AI-BS Developer Chrome.lnk`) |
| 9 | `C:\Users\footb\OneDrive\Desktop\BS-Studio.lnk` | `C:\Program Files\BS-Studio\BS-Studio.exe` | Active DAW Workstation | ✅ **KEEP** |
| 10 | `C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Launch_AI_BS.bat` | Public / User Duplicate | 🗑️ **DELETE** |
| 11 | `C:\Users\footb\OneDrive\Desktop\AI-BS Matrix Boot.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Launch_AI_BS.bat` | Installed Copy Target | 🔄 **RE-TARGET** to `C:\AI-BS\Launch_AI_BS.bat` |
| 12 | `C:\Users\footb\OneDrive\Desktop\AI-BS Matrix.lnk` | `C:\Program Files\AI-BS Matrix\AI-BS Matrix.exe` | Points to Obsolete 3.03 GB App | 🗑️ **DELETE** |
| 13 | `C:\Users\footb\OneDrive\Desktop\AI-BS Broadcast Studio.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` | Active Broadcast Workstation | ✅ **KEEP** |
| 14 | `C:\Users\footb\OneDrive\Desktop\AI-BS Sovereign Studio.lnk` | `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` | Primary Desktop Studio App | ✅ **KEEP** |
| 15 | `C:\Users\Public\Desktop\AI-BS Matrix.lnk` | `C:\Program Files\AI-BS Matrix\AI-BS Matrix.exe` | Duplicate Obsolete Shortcut | 🗑️ **DELETE** |
| 16 | `C:\Users\footb\OneDrive\Desktop\AI-BS Shutdown.lnk` | `C:\Program Files\AI-BS Sovereign Studio\Shutdown_Desktop_Studio.bat` | Active Studio Shutdown | ✅ **KEEP** |
| 17 | `C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand (2).lnk` | `C:\AI-BS\Launch_Unreal_OnDemand.bat` | Numbered Collision Copy | 🗑️ **DELETE** |
| 18 | `C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut (2).lnk` | `C:\AI-BS\Launch_AI_BS.bat` | Numbered Collision Copy | 🗑️ **DELETE** |

---

## Summary of Action: 18 Shortcuts Consolidated to 7 Clean Icons

### Retained & Cleaned Shortcuts (On User Desktop)
1. **`AI-BS Sovereign Studio.lnk`** -> `C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat` (or `.exe`) [Desktop Studio v5.230.1]
2. **`AI-BS Matrix Boot.lnk`** -> `C:\AI-BS\Launch_AI_BS.bat` [Master Matrix Boot with all Daemons & Ports]
3. **`AI-BS Shutdown.lnk`** -> `C:\AI-BS\Shutdown_AI_BS.bat` (or `Shutdown_Desktop_Studio.bat`) [Clean Process Shutdown]
4. **`AI-BS Broadcast Studio.lnk`** -> `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` [Broadcast Workstation]
5. **`BS-Studio.lnk`** -> `C:\Program Files\BS-Studio\BS-Studio.exe` [Music DAW Workstation]
6. **`Launch_Unreal_OnDemand.lnk`** -> `C:\AI-BS\Launch_Unreal_OnDemand.bat` [Unreal Engine 5 Engine]
7. **`Start Crypto Swarm.lnk`** -> `C:\AI-BS\Start_Crypto_Swarm.bat` [Autonomous Crypto Swarm]
*(Note: `AI-BS Developer Chrome.lnk` created today on Port 9222 remains active and untouched).*

### Shortcuts to Be Removed (11 Items)
- `C:\Users\Public\Desktop\AI-BS Shutdown.lnk`
- `C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk`
- `C:\Users\Public\Desktop\BS-Studio.lnk`
- `C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk`
- `C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk`
- `C:\Users\Public\Desktop\AI-BS Matrix.lnk`
- `C:\Users\footb\OneDrive\Desktop\AI-BS Matrix.lnk`
- `C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut (2).lnk`
- `C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut.lnk` (superseded by clean `AI-BS Matrix Boot.lnk`)
- `C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand (2).lnk`
- `C:\Users\footb\OneDrive\Desktop\Stehouwer Publishing AI-BS Matrix.lnk`

---

## Storage Reclamation Options

### Option 1: Desktop Shortcuts Cleanup Only
- Backs up all shortcuts to `C:\AI-BS\saved_data\desktop_shortcuts_backup_[timestamp]\`.
- Removes the 11 redundant shortcuts and standardizes the 7 primary icons.

### Option 2: Desktop Shortcuts Cleanup + 3.03 GB Obsolete Version Storage Reclamation
- Performs Option 1.
- Uninstalls or removes `C:\Program Files\AI-BS Matrix` (dated August 29, 2026), immediately reclaiming **3.03 GB** of storage on Drive C:.

---

## User Review Required

> [!IMPORTANT]
> - All removed `.lnk` files will be backed up to `C:\AI-BS\saved_data\desktop_shortcuts_backup\` before deletion, allowing instant 1-click rollback if ever desired.
> - Please specify if you would like **Option 1** (Shortcuts cleanup only) or **Option 2** (Shortcuts cleanup + 3.03 GB storage reclaim).
