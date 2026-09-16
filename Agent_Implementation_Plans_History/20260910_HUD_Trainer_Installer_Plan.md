# Interactive Click-to-Set Variables HUD Overlay

## Overview
Transform the AI-BS On-Screen Game Trainer HUD Overlay from a passive, read-only status window into a fully interactive, click-to-toggle cheat controller and live variable editor. Players will be able to click cheats directly to toggle or trigger them, click preset pills or enter custom numbers to modify game variables (Match Cash, Match Lives, Monkey Money, Add Step), and execute memory calibration directly from the floating overlay without needing to alt-tab to the terminal.

---

## User Review Required

> [!IMPORTANT]
> **Clicking Interactivity & Pass-Through Modes**:
> - By default, the overlay will run in **Interactive Mode (`🖱️ Interactive`)**, capturing mouse clicks so users can click cheat buttons, tabs, preset pills, and variable text boxes.
> - An on-screen mode toggle button `[🖱️ / 👻]` in the header will permit switching instantly into **Ghost Pass-Through Mode (`👻 Pass-Through`)** during intense gameplay so mouse clicks pass straight through into the game window beneath.

---

## Proposed Architectural Changes

### 1. Trainer Engine Variable Model (`game_trainer/core/trainer.py`)
Introduce a formalized `TrainerVariable` abstraction to allow any game profile to register editable runtime variables with custom types, units, live getters/setters, step sizes, and quick presets.

- **`TrainerVariable` Class**:
  - `key: str` (e.g. `"cash"`, `"lives"`, `"coins"`, `"add_amount"`)
  - `name: str` (e.g. `"Match Cash"`, `"Match Lives"`, `"Monkey Money"`)
  - `var_type: str` (`"float"`, `"int"`, `"str"`)
  - `get_val: Callable[[], Any]`
  - `set_val: Callable[[Any], None]`
  - `presets: List[Any]` (e.g. `[1000.0, 10000.0, 50000.0, 99999.0, 1000000.0]`)
  - `unit_prefix: str` (e.g. `"$"`)
  - `unit_suffix: str` (e.g. `" Coins"`)
  - `step: float` (e.g. `10000.0`)
- **`TrainerBase` Extensions**:
  - `add_variable(variable: TrainerVariable)`
  - `get_variables() -> List[TrainerVariable]`
  - `set_variable(key: str, val: Any) -> bool`

---

### 2. Bloons TD 6 Profile Variable Registration (`game_trainer/profiles/btd6_profile.py`)
Register variables and bind their setters to immediate memory write-backs across all locked addresses:

- **Match Cash (`cash`)**:
  - Live getter returns `frozen_cash_val`.
  - Setter updates `frozen_cash_val` and immediately writes double-precision float to all locked `cash_addresses`.
  - Quick presets: `[$1k]`, `[$10k]`, `[$50k]`, `[$99.9k]`, `[$500k]`, `[$1M]`.
- **Match Lives (`lives`)**:
  - Live getter returns `frozen_lives_val`.
  - Setter updates `frozen_lives_val` and immediately writes to all locked `lives_addresses`.
  - Quick presets: `[100]`, `[200]`, `[1,000]`, `[99,999]`.
- **Monkey Money (`coins`)**:
  - Live getter returns `frozen_coins_val`.
  - Setter updates `frozen_coins_val` and writes to all locked `coins_addresses`.
  - Quick presets: `[5,000]`, `[25,000]`, `[99,999]`, `[250,000]`.
- **One-Shot Cash Addition Step (`add_amount`)**:
  - Sets increment amount for Feature 3 (`F3` / Click to Add). Presets: `[+$10k]`, `[+$50k]`, `[+$100k]`.

---

### 3. Click-Interactive HUD Overlay Overhaul (`game_trainer/core/overlay.py`)
Upgrade the Tkinter overlay with modern styling, click event handling, tabbed views, and input controls:

- **Segmented Navigation Tabs**:
  - `[▶ Launch Game]`: Dedicated tab. If the game is not running, displays a prominent **"▶ START GAME"** button that launches the game directly via Steam URI `steam://rungameid/960090`.
  - `[⚡ Cheats]`: View and click all hotkey features.
    - **Top of the List - "Prepare"**: A dedicated **"Prepare (Enable Cheats)"** button at the very top of the list. Clicking this executes the initial auto-scan to hook the game's memory addresses. This step must be clicked to activate the further cheats below it.
  - `[🎛️ Variables]`: Interactive variable cards with value displays, preset buttons, and numeric input fields with `[Set]` actions.
  - `[🎯 Scanner]`: Advanced in-game memory calibration for dynamic targets (custom cash/coins).
- **Interactive Cheat Rows**:
  - Hover effects (`<Enter>` / `<Leave>`) with dynamic color highlighting and `cursor="hand2"`.
  - Click handler: Clicking anywhere on the row or status badge executes `feat.toggle()`. Toggles flip between `OFF` (slate) and `ACTIVE` (emerald green). One-shot triggers pulse cyan with temporary `TRIGGERED!` feedback.
- **Interactive Variable Cards**:
  - Live value indicator with currency/unit formatting.
  - Row of clickable preset pills (`[ $10k ]`, `[ $50k ]`, `[ $99.9k ]`, etc.). Clicking immediately applies the value.
  - Inline input box (`Entry`) with `[Set]` button and `[+]` / `[-]` step increments.
- **On-Screen Memory Calibration Widget**:
  - "Current In-Game Monkey Money" input + `[Calibrate & Freeze]` button.
  - "Current In-Game Cash" input + `[Scan & Lock]` button.
- **Window Controls**:
  - `[🖱️ / 👻]` Mode Switcher: Toggle between interactive clicks and click-through pass-through.
  - `[▲ / ▼]` Compact/Expanded toggle to shrink the overlay to a minimal status strip during gameplay.

---

### 4. Standalone Executable Compilation & NSIS Installer Packaging
- **PyInstaller Bundling**: Compile `launch_btd6_trainer.py` into a single standalone `AI-BS_BTD6_Trainer.exe` Windows binary. This ensures the app can run on target machines without Python installed. The build command will bundle the `game_trainer` module and enforce a UAC Administrator manifest (`--uac-admin`), allowing it to natively interface with `ReadProcessMemory`/`WriteProcessMemory` without access denied errors.
- **NSIS Installer Script (`build_trainer_installer.nsi`)**:
  - Author a Nullsoft Scriptable Install System (NSIS) script to package the compiled `.exe` into a professional setup wizard (`AI-BS_Trainer_Setup_v2.21.exe`).
  - The installer will deploy the binary to `C:\Program Files\AI-BS\Trainer`, create a Desktop Shortcut, and insert Start Menu items.
  - The installation package and application will execute at the Administrator level (Ring 3 User Mode) utilizing standard Windows Win32 memory APIs (it will not deploy Ring 0 kernel-level drivers `.sys`).

---

### 5. Standalone Launcher & Documentation (`launch_btd6_trainer.py`, `Launch_BTD6_Trainer.bat`)
- Update launcher console output with details on using the interactive overlay controls.
- Provide instructions for clicking variables, presets, and calibration.

---

## File Changes Summary

#### [MODIFY] [trainer.py](file:///c:/AI-BS/game_trainer/core/trainer.py)
- Add `TrainerVariable` dataclass/class.
- Add variable registration, retrieval, and mutation methods to `TrainerBase`.

#### [MODIFY] [btd6_profile.py](file:///c:/AI-BS/game_trainer/profiles/btd6_profile.py)
- Register `cash`, `lives`, `coins`, and `add_amount` variables.
- Connect setters to memory write-backs and auto-freeze loops.

#### [MODIFY] [overlay.py](file:///c:/AI-BS/game_trainer/core/overlay.py)
- Implement tab navigation, click-to-toggle cheat rows, variable cards with preset buttons and input fields, memory calibration widget, and click-through mode toggling.

#### [MODIFY] [launch_btd6_trainer.py](file:///c:/AI-BS/game_trainer/launch_btd6_trainer.py)
- Update launcher banner with interactive HUD guidance.

#### [MODIFY] [test_game_trainer.py](file:///c:/AI-BS/tests/test_game_trainer.py)
- Add unit tests for `TrainerVariable` registration, preset dispatch, and variable mutation.

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///c:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Log `v5.247.0` entry with full technical rationale and modified files.

#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///c:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Update manual documentation for Interactive Overlay and bump version to `v5.247.0`.

---

## Verification Plan

### Automated Tests
1. Run `python -m unittest tests/test_game_trainer.py` to verify:
   - Variable registration and dictionary extraction.
   - Setting variable updates live values and calls setter callbacks.
   - Preset button values dispatch correctly.
   - Dual-bound hotkeys and overlay instantiation remain 100% stable.
2. Run `python tests/test_e2e_trainer.py` to verify end-to-end sandbox compatibility.

### Manual Verification
1. Launch `Launch_BTD6_Trainer.bat` (or test run overlay via Python).
2. Verify that clicking on cheat rows toggles cheat states.
3. Verify that clicking preset buttons (`$50k`, `$99.9k`, `99999`) updates the variable display and calls trainer setters.
4. Verify typing a custom number in the entry box and clicking `[Set]` updates the variable value.
5. Verify tab switching between `Cheats`, `Variables`, and `Scanner`.
6. Verify dragging the HUD window remains smooth and responsive.
