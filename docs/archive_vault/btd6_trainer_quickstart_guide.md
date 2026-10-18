# AI-BS Bloons TD 6 Memory Trainer: Operational Guide

## 1. How to Launch the Trainer

You have two primary launch options from your Desktop:

### Option A: Combined 1-Click Launch (Recommended)
- **Action**: Double-click the **`Play BTD6 (Monkey Trainer)`** shortcut on your Desktop (or run [Play_BTD6_With_Trainer.bat](file:///C:/AI-BS/Play_BTD6_With_Trainer.bat)).
- **Behavior**:
  1. Starts the game via Steam (`steam://rungameid/960090`).
  2. Simultaneously starts [Launch_BTD6_Trainer.bat](file:///C:/AI-BS/Launch_BTD6_Trainer.bat).
  3. The trainer continuously monitors for `BloonsTD6.exe`, attaches the instant it boots, loads memory hooks, and displays the transparent click-through HUD overlay over the running game.

### Option B: Independent Standalone Launch
- **Action**: Double-click **`AI-BS BTD6 Trainer`** on your Desktop (or run [Launch_BTD6_Trainer.bat](file:///C:/AI-BS/Launch_BTD6_Trainer.bat)).
- **Timing**: Can be opened **before** starting the game or **while** the game is already running.

---

## 2. Setting Commands: Start Menu vs. In-Game

- **Monkey Money (Coins)**: Managed globally on your profile and visible in the **start menu**. You calibrate this in the start menu (or anytime).
- **Match Cash ($) and Lives**: Allocated in memory **after** you start or load a match.

---

## 3. How to Activate Unlimited Match Cash ($99,999.0)

Match Cash is an IEEE 754 64-bit float (`double`) scoped to your active match:

1. Load into any single-player map. Note your cash (e.g. `$650`).
2. In the trainer console, enter:
   ```text
   scan 650
   ```
   *(Or whatever your current in-game cash displays).*
3. **The trainer locks memory and immediately engages the Unlimited Cash freeze loop at `$99,999.0`!**
4. You can also toggle the cash freeze loop ON or OFF at any time by pressing **`F1`** or **`NUMPAD 1`**.

---

## 4. How to Activate Unlimited Monkey Money (99,999 Coins Freeze)

Monkey Money is a 32-bit integer (`int32`) stored in profile heap memory:

1. In the game main menu (or store/hero menu), look at your current Monkey Money in the top-right corner (e.g. `1450`).
2. In the trainer console, enter:
   ```text
   coins 1450
   ```
   *(Or whatever your current coin number is).*
3. **The trainer locks memory, writes 99,999, and automatically engages the Unlimited Monkey Money freeze loop!**
4. The background freeze loop ticks every 25ms to rewrite 99,999, ensuring your coins never drop when unlocking heroes, buying monkey knowledge, powers, or map continues.
5. You can toggle the coins freeze loop ON or OFF at any time by pressing **`F7`** or **`NUMPAD 7`**.

---

## Quick Reference Summary Table

| Hotkey | Cheat Feature | Type | Target Value | Action / Description |
| :--- | :--- | :--- | :--- | :--- |
| **`F1` / `NUMPAD 1`** | **Unlimited Match Cash** | **Toggle Freeze** | **$99,999.0** | Ticks every 25ms writing 99,999.0 double. |
| **`F2` / `NUMPAD 2`** | **Unlimited Match Lives** | **Toggle Freeze** | **99,999.0** | Prevents match loss on balloon leaks. |
| **`F3` / `NUMPAD 3`** | **Add $50,000 Cash** | One-Shot | +$50,000.0 | One-time cash increment. |
| **`F4` / `NUMPAD 4`** | **Zero-Cost Placement** | Byte Patch | N/A | NOPs decrement opcode in `GameAssembly.dll`. |
| **`F5` / `NUMPAD 5`** | **Instant Cooldowns** | Toggle Loop | 0.0s | Resets hero and tower ability timers. |
| **`F6`** | **Toggle Transparent HUD** | Interface | N/A | Shows or hides transparent on-screen HUD. |
| **`F7` / `NUMPAD 7`** | **Unlimited Monkey Money** | **Toggle Freeze** | **99,999** | Ticks every 25ms writing 99,999 int32. |
| **`F10` / `NUMPAD 0`** | **Reset & Restore All** | Restore | Default | Disables all freezes and rolls back patches. |
