# Implementation Plan: Unlimited Match Cash & Unlimited Monkey Money Freeze Engine

Upgrade the Bloons TD 6 trainer profile, standalone launcher, backend memory router, and React Web Gaming Lab dashboard so both in-game Match Cash and global Monkey Money (Coins) operate with continuous value freeze loops (`99,999.0` double and `99,999` int32), guaranteeing unlimited currency.

## User Review Required

> [!NOTE]
> - **Match Cash ($99,999.0)**: Stored as IEEE 754 64-bit float (`double`) scoped to active single-player matches. Handled by continuous `_tick_cash()` freeze loop (F1 / NUMPAD 1).
> - **Monkey Money (99,999 Coins)**: Stored as 32-bit signed integer (`int32`) in global profile memory. Upgraded from one-shot trigger to continuous `_tick_coins()` freeze loop (F7 / NUMPAD 7).
> - **Zero-Effort Auto-Lock**: Scanning with `scan <val>` or `coins <val>` will automatically lock addresses, pre-fill `99999`, and engage the freeze loop immediately.

## Proposed Changes

### Game Trainer Suite

#### [MODIFY] [btd6_profile.py](file:///C:/AI-BS/game_trainer/profiles/btd6_profile.py)
- In `__init__`: Define `self.frozen_coins_val: int = 99999`.
- In `_init_quick_keys()`: Change Feature 7 to `name="Unlimited Monkey Money"`, `is_toggle=True`, `on_toggle=self._on_coins_toggle`, `on_tick=self._tick_coins`.
- Implement `_on_coins_toggle(enabled)`: Auto-scans or reports status, writes 99,999 immediately upon activation.
- Implement `_tick_coins()`: Writes `self.frozen_coins_val` across all `self.coins_addresses` on every tick.
- In `auto_scan_coins()`: Automatically sets `self.frozen_coins_val = 99999`, writes to all matches, and turns on `Unlimited Monkey Money` feature toggle.
- In `auto_scan_cash()`: Broaden candidate scan threshold to `0 < len(matches) <= 32` and auto-enable `Unlimited Match Cash` feature toggle on match.

#### [MODIFY] [launch_btd6_trainer.py](file:///C:/AI-BS/game_trainer/launch_btd6_trainer.py)
- Update banner to show both F1 and F7 as `[TOGGLE]`.
- Update `scan` command to auto-engage the cash freeze loop upon finding addresses.
- Update `coins` command: if no argument is passed, verify locked addresses or print guided prompt; if argument is passed, lock addresses and auto-engage the coins freeze loop.

#### [MODIFY] [Launch_BTD6_Trainer.bat](file:///C:/AI-BS/Launch_BTD6_Trainer.bat)
- Update line 14 legend: `echo F7 / NUMPAD 7 : Unlimited Monkey Money (99,999 Coins Freeze)`.

---

### Backend Memory Lab Router

#### [MODIFY] [memory_lab_router.py](file:///C:/AI-BS/backend/routers/memory_lab_router.py)
- In `/set-cash`: Update `frozen_cash_val` and auto-activate `Unlimited Match Cash` feature toggle.
- In `/set-coins`: Update `frozen_coins_val` and auto-activate `Unlimited Monkey Money` feature toggle.

---

### Frontend Web Gaming Lab

#### [MODIFY] [ProcessMemoryLabTab.jsx](file:///C:/AI-BS/frontend/src/components/ProcessMemoryLabTab.jsx) (and mirrors)
- Add `unlimitedCoins: false` to `quickKeys` state.
- Update Card 7 with toggle checkbox for `Unlimited Monkey Money` and direct `🪙 99,999` inject button.
- Update Floating Web HUD with `[F7] 99k Coins` lock toggle and direct button.
- Update Pop-Out Mini HUD with `[F7/NUM7]` lock toggle and direct button.

---

### Verification Plan

### Automated Tests
- `python tests/test_game_trainer.py`
- `python tests/test_e2e_trainer.py`

### Manual Verification
- Verify standalone trainer CLI output and toggle states.
- Verify frontend builds cleanly with `npm run build`.
- Deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
