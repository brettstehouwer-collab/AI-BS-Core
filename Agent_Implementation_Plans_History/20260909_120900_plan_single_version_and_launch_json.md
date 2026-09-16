# Implementation Plan: Single-Version Architecture Enforcement & VS Code launch.json Configuration

Enforce a single, unified, up-to-date version of AI-BS Sovereign Studio for all studio, live broadcast, and music DAW operations, eliminating duplicate standalone installations and configuring standard IDE debug targets.

---

## 1. Single-Version Architecture Enforcement
- **Primary Single Suite:** `C:\Program Files\AI-BS Sovereign Studio` (v5.230.1, 4.33 GB)
  - `Launch_Desktop_Studio.bat` -> Port 5173 (Full AI-BS Suite, Wave Studio Neural DAW).
  - `Launch_Broadcast_Studio.bat` -> Port 5174 (Dedicated Live Broadcast & DAW Workstation, Broadcast Kernel on Port 8088).
- **Decommissioned Predecessors:**
  - `C:\Program Files\AI-BS Matrix` (v5.133.0, August 29) -> Removed (3.03 GB freed).
  - `C:\Program Files\BS-Studio` (v5.151.0, August 30) -> Uninstalled (3.10 GB freed).
  - Total storage reclaimed across Drive C: **>6.13 GB**.

---

## 2. Desktop Topology Optimization
- Pruned `BS-Studio.lnk` and `AI-BS Matrix.lnk`.
- Retained 6 active, standardized launchers:
  1. `AI-BS Sovereign Studio.lnk`
  2. `AI-BS Broadcast Studio.lnk`
  3. `AI-BS Matrix Boot.lnk`
  4. `AI-BS Shutdown.lnk`
  5. `Launch_Unreal_OnDemand.lnk`
  6. `Start Crypto Swarm.lnk`
  *(Plus `AI-BS Developer Chrome.lnk` on Port 9222).*

---

## 3. VS Code / Antigravity IDE launch.json Integration
Added 6 debug targets to `.vscode/launch.json`:
1. `Python: AI-BS Core Backend (Port 8000)`
2. `Node: Gateway Server (Port 8080)`
3. `Chrome: Attach to Port 9222 (Developer Chrome)`
4. `Python: Desktop Studio Server (Port 5173)`
5. `Python: Broadcast Kernel (Port 8088)`
6. `PowerShell: Launch Current File`
