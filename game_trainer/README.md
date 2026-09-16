# AI-BS Game Trainer Engine & Tooling Suite

An open-source, modular Win32 game trainer development suite and memory manipulation engine designed for offline and single-player game environments.

---

## 1. Directory Structure

```
game_trainer/
├── core/
│   ├── __init__.py           # Package exports
│   ├── memory.py             # Win32 memory engine (RPM, WPM, Pointer Chaser, AOB Scanner, NOP/Patch)
│   ├── hotkeys.py            # Global hotkey manager (GetAsyncKeyState background listener with debouncing)
│   └── trainer.py            # TrainerBase & CheatFeature abstractions (Watchdog, freeze tick loop, dashboard)
├── mock_game/
│   ├── __init__.py
│   └── target_sandbox.py     # Live mock game sandbox simulating dynamic player structs and pointer hierarchies
├── examples/
│   ├── __init__.py
│   └── sandbox_trainer.py    # Working trainer implementation targeting target_sandbox.py
├── templates/
│   └── game_profile_template.py # Boilerplate template for real-world single-player games
├── native_cpp/
│   └── MemoryEngine.hpp      # Header-only C++ Win32 memory engine for native trainer development
└── README.md                 # Technical manual and operational guide
```

---

## 2. Quickstart & Verification (End-to-End Demo)

You can run and test the complete trainer suite immediately without installing third-party games:

### Step 1: Launch the Mock Game Sandbox
Open a terminal in `C:\AI-BS`:
```powershell
python -m game_trainer.mock_game.target_sandbox
```
The sandbox displays:
- Process ID (PID)
- Allocated Memory Hierarchy (`Root Engine Base`, `World Context`, `Active Entity`, `Player Direct Addr`)
- Live simulated ticks with decreasing health and ammo.

### Step 2: Launch the Sandbox Trainer
Open a second terminal in `C:\AI-BS`:
```powershell
python -m game_trainer.examples.sandbox_trainer --pid <PID> --root <ROOT_ADDR>
```
*(Or specify `--player <PLAYER_DIRECT_ADDR>` directly).*

### Step 3: Trigger Trainer Hotkeys
- `NUMPAD 1`: Toggle **Infinite Health** (Freezes HP at 9999).
- `NUMPAD 2`: Toggle **Infinite Ammo** (Locks ammo at 999).
- `NUMPAD 3`: One-shot **Add 50,000 Score**.
- `NUMPAD 4`: Toggle **Max Overshield** (Sets shield to 200).
- `NUMPAD 5`: Toggle **Native Invulnerability Flag**.
- `NUMPAD 0`: **Reset Stats** (Restores normal 100 HP, 50 Shield, 30 Ammo).

---

## 3. Core Technical Primitives

### 3.1 Multi-Level Pointer Resolution
Dynamic memory allocation in modern game engines allocates player and entity objects on the heap:
```python
from game_trainer.core.memory import MemoryManager

mem = MemoryManager("game.exe")
module_base = mem.base_address

# Traverse pointer offsets: [Base + 0x10F4F4] -> [+ 0xF8] -> Final Health Address
health_addr = mem.resolve_pointer_chain(module_base + 0x10F4F4, [0xF8])
mem.write_int32(health_addr, 999)
```

### 3.2 AOB (Array of Bytes) Signature Scanning
Find dynamic functions or pointers across game updates using masked byte signatures:
```python
# '?' and '??' represent wildcards
matches = mem.aob_scan("48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ??")
if matches:
    # Resolve x86_64 RIP-relative addressing
    target_addr = mem.resolve_rip_relative(matches[0], instruction_length=7)
```

### 3.3 Instruction Patching & NOPing
Disable game mechanics (e.g., ammo decrement or health reduction instructions) and restore cleanly:
```python
# NOP 5 bytes of instruction (e.g. 'sub [rbx+0x18], eax')
patch = mem.nop_instruction(target_code_address, count=5)

# Later, restore original instruction bytes
patch.restore()
```

---

## 4. Reverse Engineering Workflow: Finding Offsets in Single-Player Games

1. **Attach Memory Scanner:** Open Cheat Engine and select the target single-player process.
2. **Find Value:** Search for 4-byte integer of current health (e.g., `100`).
3. **Filter Value:** In-game, take damage to change health to `85`. Execute 'Next Scan' for `85`. Repeat until 1-3 addresses remain.
4. **Identify Writing Instruction:** Right-click the address and choose **"Find out what writes to this address"**.
5. **Analyze Instruction:** Note the instruction (e.g., `mov [rax+0xEC], edx`).
   - The offset is `0xEC`.
   - The register `RAX` contains the base address of the player struct.
6. **Find Pointer to Player:**
   - Scan for 8-byte hexadecimal value of `RAX`.
   - Look for static green addresses (e.g., `game.exe + 0x2A4B80`).
   - If not static, repeat pointer scan to build a pointer map.
7. **Populate Profile Template:** Copy `game_trainer/templates/game_profile_template.py` and input the module name, static base offset, and pointer offsets.

---

## 5. Security & Operational Boundaries
- This suite is strictly intended for single-player, offline environments, modding, accessibility assistance, and reverse engineering research.
- All code runs locally without external network dependencies or telemetry.
