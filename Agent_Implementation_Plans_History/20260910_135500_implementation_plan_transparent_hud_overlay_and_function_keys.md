# Transparent On-Screen HUD Overlay & Function Keys Specification

## 1. Overview & Operational Goals
The operator requested:
1. **Function Key Integration:** Expanding cheat quick keys so that players without Numpads (e.g. laptop keyboards or compact TKL layouts) can use standard Function keys (`F1` through `F6`, `F10`) in dual-binding with the existing Numpad keys.
2. **Transparent On-Screen HUD Overlay:** Providing an on-screen translucent heads-up display (HUD) that floats over games in windowed/borderless mode, displaying live function key bindings and cheat toggle statuses without forcing the player to Alt-Tab.

---

## 2. Technical Architecture

### 2.1 Function Keys Dual-Binding Mapping Matrix
Every cheat feature in `game_trainer/profiles/btd6_profile.py` will accept primary and secondary hotkeys:

| Feature Name | Function Key | Numpad Key | VK Codes | Action / Memory Type | Status Color |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Unlimited Match Cash** | **`F1`** | **`NUMPAD 1`** | `0x70` / `0x61` | Freeze `double` at `$9,999,999.0` | Cyan / Neon Green |
| **Unlimited Match Lives** | **`F2`** | **`NUMPAD 2`** | `0x71` / `0x62` | Freeze `double` at `99,999.0` | Emerald Green |
| **Add $50,000 Match Cash** | **`F3`** | **`NUMPAD 3`** | `0x72` / `0x63` | Read + Add `50,000.0` (One-shot) | Amber / Gold |
| **Zero-Cost Placement** | **`F4`** | **`NUMPAD 4`** | `0x73` / `0x64` | NOP cash decrement instruction | Purple / Violet |
| **Instant Ability Cooldowns** | **`F5`** | **`NUMPAD 5`** | `0x74` / `0x65` | Zero active ability cooldown timers | Sky Blue |
| **Toggle On-Screen HUD** | **`F6`** | — | `0x75` | Hide / Show transparent HUD window | White / Blue |
| **Reset & Restore All** | **`F10`** | **`NUMPAD 0`** | `0x79` / `0x60` | Unfreeze values & rollback bytecode patches | Red / Gray |

---

### 2.2 Standalone Native Windows Transparent HUD (`game_trainer/core/overlay.py`)
Built using Python's standard library (`tkinter` + `ctypes` Win32 API) with **zero paid or third-party dependencies**:
1. **Window Characteristics:**
   - Frameless & borderless (`overrideredirect(True)`).
   - Alpha transparency (`-alpha 0.82`) for a sleek dark glassmorphic cyber HUD.
   - Always-on-top (`-topmost True`).
2. **Win32 Click-Through Pass-Through:**
   - Using `ctypes.windll.user32.SetWindowLongPtrW`:
     ```python
     WS_EX_LAYERED = 0x00080000
     WS_EX_TRANSPARENT = 0x00000020
     WS_EX_TOPMOST = 0x00000008
     ```
   - When **Click-Through Mode** is enabled, mouse clicks pass directly through the HUD into the game underneath (players can place towers and click balloons through the overlay without obstruction).
   - Includes a mini lock/unlock toggle so the operator can drag the HUD to any corner of their screen before locking it into click-through mode.
3. **Live State Synchronization:**
   - Subscribes to the trainer's active feature map.
   - Updates badges in real-time (e.g. `[F1] CASH: ACTIVE` glowing green vs `[F1] CASH: OFF` in muted slate).
4. **Lifecycle & Hotkey Control:**
   - Pressing **`F6`** instantly toggles HUD visibility on/off.
   - Runs in a lightweight daemon thread alongside the trainer CLI.

---

### 2.3 Standalone Launcher Integration
- Update [launch_btd6_trainer.py](file:///C:/AI-BS/game_trainer/launch_btd6_trainer.py) with `--overlay` / `--no-overlay` arguments (defaulting to starting the HUD overlay automatically).
- Update [Launch_BTD6_Trainer.bat](file:///C:/AI-BS/Launch_BTD6_Trainer.bat) to launch the trainer with the HUD overlay enabled.

---

### 2.4 AI-BS Web Dashboard Integration (`ProcessMemoryLabTab.jsx`)
1. **Function Key Dual Badges:**
   - Update all quick key cards in the Gaming Trainer Deck to display both the Function Key and Numpad badges (e.g., `F1` and `NUM 1`).
2. **In-Dashboard Floating Transparent HUD Widget:**
   - A pinnable, translucent glassmorphic HUD pill in the top-right corner of the tab with real-time toggle switches and active glow indicators.
3. **Pop-Out Standalone Web HUD:**
   - "Pop-Out Floating HUD" button that launches a minimal, frameless, compact browser popup (`window.open('', 'TrainerHUD', 'width=360,height=340')`) styled with the transparent cyberpunk theme, suitable for dual-monitor or picture-in-picture placement.

---

## 3. Verification Plan

### Automated Tests
1. `tests/test_game_trainer.py`:
   - Extend test suite to verify dual-binding hotkey registration (Function key + Numpad key triggering identical feature).
   - Verify toggle and state unfreezing via Function keys.
2. Overlay thread initialization and headless execution verification:
   - Run verification script confirming `overlay.py` instantiates and updates without blocking the main memory polling loop.

### Manual Verification
1. Launch `Launch_BTD6_Trainer.bat` & verify on-screen HUD appears with transparent glass styling.
2. Press `F1` - `F5` and observe both the HUD and terminal state toggling in real time.
3. Press `F6` to verify hide/show toggling.
4. Verify click-through behavior so mouse events reach the desktop/game window beneath.
5. In AI-BS web UI (`https://ai-bs-dashboard.web.app`), inspect the Gaming Lab tab, toggle features, and test the Pop-Out Floating HUD.
