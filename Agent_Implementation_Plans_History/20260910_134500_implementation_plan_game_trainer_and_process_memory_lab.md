# AI-BS Process Instrumentation & Gaming Lab Architecture

## 1. Compliance & Security Boundaries

> [!IMPORTANT]
> **Strict Operational Boundary: Offline / Single-Player Only**
> - **In-Game Match Cash vs. Server Store Coins:** In Bloons TD 6, match cash (used to buy and upgrade towers in single-player games) is stored locally in client memory as a 64-bit IEEE 754 floating-point number (`double`). Modifying this in offline single-player matches is local memory manipulation.
> - **Meta Store Coins (Monkey Money):** Persistent store coins are synchronized with Ninja Kiwi's cloud save servers. Client-side attempts to spoof cloud-backed store currencies in online modes lead to cloud desync and server-side profile flags. All trainer modifications are strictly scoped to offline, single-player matches.

---

## 2. Pre-Filled Quick Keys Specification (`BTD6Trainer`)

The Bloons TD 6 profile (`game_trainer/profiles/btd6_profile.py`) is pre-configured with the following default hotkeys:

| Quick Key | Win32 VK | Feature Name | Memory Operation | Description |
| :--- | :--- | :--- | :--- | :--- |
| **NUMPAD 1** | `0x61` | **Unlimited Match Cash** | Freeze `double` at `9,999,999.0` | Locks in-game match money for endless tower purchasing and upgrades. |
| **NUMPAD 2** | `0x62` | **Unlimited Match Lives** | Freeze `double` at `99,999.0` | Locks single-player player lives to prevent defeat. |
| **NUMPAD 3** | `0x63` | **Add $50,000 Match Cash** | Read + Add `50,000.0` | One-shot burst of cash whenever pressed. |
| **NUMPAD 4** | `0x64` | **Zero-Cost Placement** | Byte Patch / NOP instruction | Bypasses cash subtraction routine so towers place for free. |
| **NUMPAD 5** | `0x65` | **Instant Ability Cooldowns** | Pointer traverse + Zero timer | Instantly resets hero and tower ability cooldowns. |
| **NUMPAD 0** | `0x60` | **Reset & Restore** | Rollback patches & unfreeze | Restores normal game logic and unlocks memory. |

---

## 3. Subsystem Architecture

### 3.1 Standalone Tool Suite (`game_trainer/`)
- `game_trainer/profiles/btd6_profile.py`: Specific Unity IL2CPP memory profile targeting `BloonsTD6.exe` and `GameAssembly.dll`.
- `game_trainer/launch_btd6_trainer.py`: Standalone CLI runner with live terminal dashboard and hotkey dispatch.
- `Launch_BTD6_Trainer.bat`: One-click Windows batch launcher for standalone execution outside AI-BS.

### 3.2 AI-BS Backend Memory Bridge (`backend/routers/memory_lab_router.py`)
Provides REST API endpoints for the AI-BS dashboard:
- `GET /api/memory-lab/processes`: Enumerate running Windows processes with PID, architecture, and memory footprint.
- `POST /api/memory-lab/attach`: Attach to target process (e.g., `BloonsTD6.exe` or mock target).
- `GET /api/memory-lab/read`: Read memory address as int32, int64, float, double, or hex bytes.
- `POST /api/memory-lab/write`: Write values to arbitrary memory addresses.
- `GET /api/memory-lab/profiles`: Return available game and automation profiles.
- `POST /api/memory-lab/trigger`: Trigger or toggle profile quick keys via the web interface.

### 3.3 AI-BS Frontend "Gaming & Process Memory Lab" Tab
- `frontend/src/components/ProcessMemoryLabTab.jsx`:
  - **Quick Key Gaming Deck:** Visual cards for BTD6 hotkeys (`NUMPAD 1` - `NUMPAD 5`) with live toggle switches and status badges.
  - **Live Process Scanner & Inspector:** Select any Windows process to observe its memory pages, heap regions, and dynamic pointers.
  - **Application Automation Workbench:** Demonstrates how memory reading/writing concepts can monitor custom background daemons, audio buffers, and worker processes.
- **Navigation Integration:** Added to `Sidebar.jsx`, `TopNavbar.jsx`, and `navigationConfig.js` under `neural_intelligence` hub.

---

## 4. Execution & Verification Status: COMPLETED
1. Created `game_trainer/profiles/btd6_profile.py` with pre-filled hotkeys.
2. Created standalone CLI runner `game_trainer/launch_btd6_trainer.py` and `Launch_BTD6_Trainer.bat`.
3. Created `backend/routers/memory_lab_router.py` and registered it in `backend/AI_BS_Backend.py`.
4. Created `frontend/src/components/ProcessMemoryLabTab.jsx` and linked in navigation.
5. Rebuilt frontend bundle (`npm run build`) and deployed live to Firebase Hosting (`ai-bs-dashboard.web.app`).
6. Verified execution with automated integration tests (all passed).
7. Updated Master Architectural Ledger & Ecosystem Manual to v5.243.0.
