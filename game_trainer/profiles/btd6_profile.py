"""
AI-BS Game Trainer Suite: Bloons TD 6 Profile
Specialized profile for BloonsTD6.exe (Unity IL2CPP architecture).
Features pre-filled quick keys for single-player / offline match cash, lives, and cooldowns.
"""

import sys
import os
import time
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from game_trainer.core.memory import MemoryManager, MemoryPatch
from game_trainer.core.hotkeys import (
    HotkeyManager, KEY_NAMES,
    VK_NUMPAD0, VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4, VK_NUMPAD5, VK_NUMPAD7,
    VK_F1, VK_F2, VK_F3, VK_F4, VK_F5, VK_F6, VK_F7, VK_F10
)
from game_trainer.core.trainer import TrainerBase, CheatFeature, TrainerVariable


class BTD6Trainer(TrainerBase):
    """
    Offline single-player trainer profile targeting BloonsTD6.exe.
    Handles GameAssembly.dll module base offsets, double-precision float match cash,
    and single-player life pools.
    """

    TARGET_EXE = "BloonsTD6.exe"
    MODULE_NAME = "GameAssembly.dll"

    def __init__(self, target_pid: Optional[int] = None):
        super().__init__(target_process=self.TARGET_EXE, poll_rate_ms=25)
        self.target_pid = target_pid
        self.game_assembly_base: int = 0

        # Dynamic runtime addresses (resolved via memory auto-scans or presets)
        self.cash_address: int = 0
        self.cash_addresses: list[int] = []
        self.cash_candidates: list[int] = []
        self.lives_address: int = 0
        self.lives_addresses: list[int] = []
        self.lives_candidates: list[int] = []
        self.coins_addresses: list[int] = []
        self.coins_candidates: list[int] = []
        self.active_cash_patch: Optional[MemoryPatch] = None
        self.overlay: Optional[Any] = None

        # Desired target frozen values
        self.frozen_cash_val: float = 99999.0
        self.frozen_lives_val: float = 99999.0
        self.frozen_coins_val: int = 99999
        self.add_amount_val: float = 50000.0

        self._init_quick_keys()
        self._init_variables()

    def set_overlay(self, overlay_instance):
        """Attaches an on-screen HUD overlay to this trainer."""
        self.overlay = overlay_instance

    def _init_quick_keys(self):
        """Pre-fills default hotkeys for in-game match currency, lives, and coins."""

        # 0. Prepare (Enable Cheats) - Placed at the top
        self.add_feature(CheatFeature(
            name="Prepare (Enable Cheats)",
            hotkey_vk=0x0,
            description="Required step. Scans and hooks base memory addresses.",
            is_toggle=False,
            on_trigger=self._trigger_prepare
        ))

        # 1. F1 / NUMPAD 1: Unlimited Match Cash ($99,999.0)
        self.add_feature(CheatFeature(
            name="Unlimited Match Cash",
            hotkey_vk=VK_F1,
            secondary_hotkey_vk=VK_NUMPAD1,
            description="Locks current match cash to a frozen amount",
            is_toggle=True,
            on_toggle=self._on_cash_toggle,
            on_tick=self._tick_cash
        ))

        # 2. F2 / NUMPAD 2: Unlimited Match Lives (99,999)
        self.add_feature(CheatFeature(
            name="Unlimited Match Lives",
            hotkey_vk=VK_F2,
            secondary_hotkey_vk=VK_NUMPAD2,
            description="Locks single-player match lives to 99,999.0",
            is_toggle=True,
            on_toggle=self._on_lives_toggle,
            on_tick=self._tick_lives
        ))

        # 3. F3 / NUMPAD 3: Quick Add Cash
        self.add_feature(CheatFeature(
            name="Quick Add Match Cash",
            hotkey_vk=VK_F3,
            secondary_hotkey_vk=VK_NUMPAD3,
            description="Instantly increments match cash by custom amount",
            is_toggle=False,
            on_trigger=self._trigger_add_cash
        ))

        # 4. F4 / NUMPAD 4: Zero-Cost Tower Placement
        self.add_feature(CheatFeature(
            name="Zero-Cost Placement",
            hotkey_vk=VK_F4,
            secondary_hotkey_vk=VK_NUMPAD4,
            description="Patches cash decrement instruction in GameAssembly.dll",
            is_toggle=True,
            on_toggle=self._on_zero_cost_toggle
        ))

        # 5. F5 / NUMPAD 5: Instant Ability Cooldowns
        self.add_feature(CheatFeature(
            name="Instant Ability Cooldowns",
            hotkey_vk=VK_F5,
            secondary_hotkey_vk=VK_NUMPAD5,
            description="Resets active tower and hero ability timers",
            is_toggle=True,
            on_toggle=self._on_cooldown_toggle
        ))

        # 6. F6: Toggle On-Screen Transparent HUD Overlay
        self.add_feature(CheatFeature(
            name="Toggle On-Screen HUD",
            hotkey_vk=VK_F6,
            description="Toggles visibility of transparent on-screen HUD",
            is_toggle=False,
            on_trigger=self._trigger_toggle_overlay
        ))

        # 7. F7 / NUMPAD 7: Unlimited Monkey Money (99,999 Coins Freeze)
        self.add_feature(CheatFeature(
            name="Unlimited Monkey Money",
            hotkey_vk=VK_F7,
            secondary_hotkey_vk=VK_NUMPAD7,
            description="Locks Monkey Money (Coins) to 99,999 (int32 freeze loop)",
            is_toggle=True,
            on_toggle=self._on_coins_toggle,
            on_tick=self._tick_coins
        ))

        # 0. F10 / NUMPAD 0: Reset & Restore All
        self.add_feature(CheatFeature(
            name="Reset & Restore Normal",
            hotkey_vk=VK_F10,
            secondary_hotkey_vk=VK_NUMPAD0,
            description="Disables all active freezes and restores original instructions",
            is_toggle=False,
            on_trigger=self._trigger_reset_all
        ))

    def _init_variables(self):
        """Registers interactive TrainerVariables for the HUD Overlay."""
        self.add_variable(TrainerVariable(
            key="cash",
            name="Match Cash",
            var_type="float",
            get_val=lambda: self.frozen_cash_val,
            set_val=self.set_frozen_cash,
            presets=[1000.0, 10000.0, 50000.0, 99999.0, 500000.0, 1000000.0],
            unit_prefix="$",
            step=10000.0,
            description="Target value for Unlimited Match Cash freeze"
        ))

        self.add_variable(TrainerVariable(
            key="lives",
            name="Match Lives",
            var_type="float",
            get_val=lambda: self.frozen_lives_val,
            set_val=self.set_frozen_lives,
            presets=[100.0, 200.0, 1000.0, 99999.0],
            step=100.0,
            description="Target value for Unlimited Match Lives freeze"
        ))

        self.add_variable(TrainerVariable(
            key="coins",
            name="Monkey Money",
            var_type="int",
            get_val=lambda: self.frozen_coins_val,
            set_val=self.set_frozen_coins,
            presets=[5000, 25000, 99999, 250000],
            unit_suffix=" Coins",
            step=5000.0,
            description="Target value for Monkey Money freeze"
        ))

        self.add_variable(TrainerVariable(
            key="add_amount",
            name="Add Amount Step",
            var_type="float",
            get_val=lambda: self.add_amount_val,
            set_val=self.set_add_amount,
            presets=[10000.0, 50000.0, 100000.0],
            unit_prefix="+$",
            step=10000.0,
            description="Amount injected when using Quick Add Match Cash"
        ))

    # -------------------------------------------------------------------------
    # Variable Setters with Memory Write-Back
    # -------------------------------------------------------------------------

    def set_frozen_cash(self, val: float):
        self.frozen_cash_val = float(val)
        if self.cash_addresses and self.mem.is_alive():
            for addr in self.cash_addresses:
                try:
                    self.mem.write_double(addr, self.frozen_cash_val)
                except Exception:
                    pass

    def set_frozen_lives(self, val: float):
        self.frozen_lives_val = float(val)
        if self.lives_addresses and self.mem.is_alive():
            for addr in self.lives_addresses:
                try:
                    self.mem.write_double(addr, self.frozen_lives_val)
                except Exception:
                    pass

    def set_frozen_coins(self, val: int):
        self.frozen_coins_val = int(val)
        if self.coins_addresses and self.mem.is_alive():
            for addr in self.coins_addresses:
                try:
                    self.mem.write_int32(addr, self.frozen_coins_val)
                except Exception:
                    pass

    def set_add_amount(self, val: float):
        self.add_amount_val = float(val)

    def setup(self) -> bool:
        """Attaches to BloonsTD6.exe and retrieves GameAssembly.dll base."""
        if self.target_pid:
            self.mem.attach(self.target_pid)
        else:
            if not self.try_attach():
                return False

        # Resolve GameAssembly.dll base
        self.game_assembly_base = self.mem.get_module_base(self.MODULE_NAME)
        if not self.game_assembly_base:
            self.game_assembly_base = self.mem.base_address

        return True



    def set_cash_address(self, address: int):
        """Sets the resolved memory address for match cash."""
        self.cash_address = address
        if address not in self.cash_addresses:
            self.cash_addresses.append(address)

    def set_lives_address(self, address: int):
        """Sets the resolved memory address for match lives."""
        self.lives_address = address
        if address not in self.lives_addresses:
            self.lives_addresses.append(address)

    def first_scan_cash(self, target_cash: float) -> list[int]:
        """
        Executes First Scan for match cash (IEEE 754 double, 8-byte aligned).
        Populates cash_candidates. If <= 4 matches are found, locks them automatically.
        """
        if not self.mem.is_alive():
            return []

        val = float(target_cash)
        matches = self.mem.scan_exact_value(val, value_type="double", alignment=8)
        if not matches:
            matches = self.mem.scan_exact_value(val, value_type="double", alignment=4)

        self.cash_candidates = list(matches)
        print(f"\n[+] First Scan: Found {len(matches)} candidate(s) for ${val:,.2f}.")

        if 0 < len(matches) <= 4:
            self.cash_addresses = list(matches)
            self.cash_address = matches[0]
            print(f"[+] Automatically locked {len(matches)} cash address(es): {[hex(a) for a in matches]}")
        elif len(matches) > 4:
            print(f"[*] Change cash in-game (buy a tower or pop balloons), then run Next Scan to isolate.")

        return matches

    def next_scan_cash(self, new_cash: float) -> list[int]:
        """
        Filters existing cash_candidates against the new in-game value in <1 millisecond.
        When candidates drop to <= 8, locks them to cash_addresses.
        """
        if not self.mem.is_alive():
            return []

        val = float(new_cash)
        if not self.cash_candidates:
            if self.cash_addresses:
                self.cash_candidates = list(self.cash_addresses)
            else:
                return self.first_scan_cash(val)

        remaining = self.mem.filter_scan(self.cash_candidates, val, value_type="double", alignment=4)
        self.cash_candidates = list(remaining)
        print(f"\n[+] Next Scan: Filtered down to {len(remaining)} candidate(s) for ${val:,.2f}.")

        if 0 < len(remaining) <= 8:
            self.cash_addresses = list(remaining)
            self.cash_address = remaining[0]
            print(f"[+] Successfully locked {len(remaining)} cash address(es): {[hex(a) for a in remaining]}")
            for feat in self.features.values():
                if feat.hotkey_vk == VK_F1 and feat.enabled:
                    for addr in self.cash_addresses:
                        try:
                            self.mem.write_double(addr, self.frozen_cash_val)
                        except Exception:
                            pass
                    print(f"[+] Unlimited Match Cash freeze loop ACTIVE (${self.frozen_cash_val:,.2f}).")
                    break

        return remaining

    def auto_scan_cash(self, target_cash: Optional[float] = None) -> list[int]:
        """
        Scans game memory for match cash (IEEE 754 double).
        If target_cash is provided, performs first_scan_cash.
        Otherwise probes common starting amounts:
        [650.0, 850.0, 450.0, 1000.0, 200.0, 1750.0, 99999.0, 999999.0].
        """
        if not self.mem.is_alive():
            return []

        if target_cash is not None:
            return self.first_scan_cash(target_cash)

        candidates = [650.0, 850.0, 450.0, 1000.0, 200.0, 1750.0, 99999.0, 999999.0]
        for val in candidates:
            matches = self.mem.scan_exact_value(val, value_type="double", alignment=8)
            if not matches:
                matches = self.mem.scan_exact_value(val, value_type="double", alignment=4)
            if 0 < len(matches) <= 16:
                self.cash_candidates = list(matches)
                self.cash_addresses = list(matches)
                self.cash_address = matches[0]
                print(f"\n[+] Auto-Scan: Automatically locked {len(matches)} cash address(es) matching ${val:,.2f}: {[hex(a) for a in matches]}")
                return matches

        print("\n[*] Auto-Scan: No default starting cash matched. Use First Scan with your exact displayed cash.")
        return []

    def first_scan_coins(self, current_coins: int) -> list[int]:
        """Scans game memory for Monkey Money / coins (int32, 4-byte aligned)."""
        if not self.mem.is_alive() or current_coins <= 0:
            return []

        matches = self.mem.scan_exact_value(int(current_coins), value_type="int32", alignment=4)
        self.coins_candidates = list(matches)
        print(f"\n[+] First Scan: Found {len(matches)} Monkey Money candidate(s) for {current_coins}.")

        if 0 < len(matches) <= 8:
            self.coins_addresses = list(matches)
            for addr in matches:
                try:
                    self.mem.write_int32(addr, self.frozen_coins_val)
                except Exception:
                    pass
            print(f"[+] Locked {len(matches)} Monkey Money address(es): {[hex(a) for a in matches[:8]]}")

        return matches

    def next_scan_coins(self, new_coins: int) -> list[int]:
        """Filters Monkey Money candidates against updated count."""
        if not self.mem.is_alive() or new_coins <= 0:
            return []

        if not self.coins_candidates:
            return self.first_scan_coins(new_coins)

        remaining = self.mem.filter_scan(self.coins_candidates, int(new_coins), value_type="int32", alignment=4)
        self.coins_candidates = list(remaining)
        print(f"\n[+] Next Scan: Filtered down to {len(remaining)} Monkey Money candidate(s).")

        if 0 < len(remaining) <= 8:
            self.coins_addresses = list(remaining)
            for addr in remaining:
                try:
                    self.mem.write_int32(addr, self.frozen_coins_val)
                except Exception:
                    pass
            print(f"[+] Successfully locked {len(remaining)} Monkey Money address(es): {[hex(a) for a in remaining]}")

        return remaining

    def auto_scan_coins(self, current_coins: int) -> list[int]:
        """Scans and locks Monkey Money (int32)."""
        matches = self.first_scan_coins(current_coins)
        if matches:
            for feat in self.features.values():
                if feat.hotkey_vk == VK_F7:
                    feat.enabled = True
                    break
            print(f"[+] Unlimited Monkey Money freeze loop ACTIVE ({self.frozen_coins_val:,} Coins).")
        return matches

    def auto_scan_lives(self, target_lives: Optional[float] = None) -> list[int]:
        """Scans game memory for single-player match lives (double)."""
        if not self.mem.is_alive():
            return []

        if target_lives is not None:
            matches = self.mem.scan_exact_value(float(target_lives), value_type="double", alignment=8)
            if not matches:
                matches = self.mem.scan_exact_value(float(target_lives), value_type="double", alignment=4)
            if matches:
                self.lives_candidates = list(matches)
                self.lives_addresses = list(matches)
                self.lives_address = matches[0]
                print(f"\n[+] Auto-Scan: Locked {len(matches)} lives address(es) for {target_lives}: {[hex(a) for a in matches]}")
                return matches

        candidates = [200.0, 150.0, 100.0, 250.0, 1.0]
        for val in candidates:
            matches = self.mem.scan_exact_value(val, value_type="double", alignment=8)
            if not matches:
                matches = self.mem.scan_exact_value(val, value_type="double", alignment=4)
            if 0 < len(matches) <= 16:
                self.lives_candidates = list(matches)
                self.lives_addresses = list(matches)
                self.lives_address = matches[0]
                print(f"\n[+] Auto-Scan: Automatically locked {len(matches)} lives address(es) matching {val}: {[hex(a) for a in matches]}")
                return matches

        return []

    # -------------------------------------------------------------------------
    # Feature Callbacks
    # -------------------------------------------------------------------------

    def _trigger_prepare(self):
        """Scans and hooks base memory addresses for standard starting cash and lives."""
        print("\n[BTD6 Trainer] Running Preparation Scan...")
        cash_count = 0
        lives_count = 0

        if not self.cash_addresses:
            matches = self.auto_scan_cash(650.0)
            cash_count = len(matches)
        else:
            cash_count = len(self.cash_addresses)

        if not self.lives_addresses:
            matches = self.auto_scan_lives(200.0)
            lives_count = len(matches)
        else:
            lives_count = len(self.lives_addresses)

        if cash_count > 0:
            print(f"[+] Preparation: Hooked {cash_count} cash address(es).")
        else:
            print("[*] Preparation: Match cash not yet locked. Use the HUD Scanner or type 'scan <current_cash>' in console.")

        if lives_count > 0:
            print(f"[+] Preparation: Hooked {lives_count} lives address(es).")
        else:
            print("[*] Preparation: Lives will auto-hook upon starting a map.")

    def _on_cash_toggle(self, enabled: bool):
        print(f"\n[BTD6 Trainer] Unlimited Match Cash: {'ACTIVE' if enabled else 'DISABLED'}")
        if enabled and not self.cash_addresses and self.mem.is_alive():
            self.auto_scan_cash()

    def _tick_cash(self):
        if not self.cash_addresses and self.cash_address:
            self.cash_addresses = [self.cash_address]

        if self.cash_addresses and self.mem.is_alive():
            for addr in self.cash_addresses:
                try:
                    self.mem.write_double(addr, self.frozen_cash_val)
                except Exception:
                    pass

    def _on_lives_toggle(self, enabled: bool):
        print(f"\n[BTD6 Trainer] Unlimited Match Lives: {'ACTIVE' if enabled else 'DISABLED'}")
        if enabled and not self.lives_addresses and self.mem.is_alive():
            self.auto_scan_lives()

    def _tick_lives(self):
        if not self.lives_addresses and self.lives_address:
            self.lives_addresses = [self.lives_address]

        if self.lives_addresses and self.mem.is_alive():
            for addr in self.lives_addresses:
                try:
                    self.mem.write_double(addr, self.frozen_lives_val)
                except Exception:
                    pass

    def _trigger_add_cash(self):
        if not self.cash_addresses and self.cash_address:
            self.cash_addresses = [self.cash_address]

        if self.cash_addresses and self.mem.is_alive():
            updated_any = False
            for addr in self.cash_addresses:
                current = self.mem.read_double(addr)
                if current > 0:
                    new_cash = current + self.add_amount_val
                    self.mem.write_double(addr, new_cash)
                    updated_any = True
                elif current <= 0:
                    current_int = self.mem.read_int32(addr)
                    if current_int > 0:
                        self.mem.write_int32(addr, current_int + int(self.add_amount_val))
                        updated_any = True
            if updated_any:
                print(f"\n[+] Added ${self.add_amount_val:,.2f} cash across {len(self.cash_addresses)} locked addresses.")
            else:
                self.mem.write_double(self.cash_addresses[0], self.add_amount_val)
                print(f"\n[+] Injected ${self.add_amount_val:,.2f} cash into address {hex(self.cash_addresses[0])}.")
        else:
            print("\n[!] Cash address not yet locked. Use Scanner tab or type 'scan <current_cash>' in console to lock.")

    def _on_coins_toggle(self, enabled: bool):
        print(f"\n[BTD6 Trainer] Unlimited Monkey Money: {'ACTIVE' if enabled else 'DISABLED'}")
        if enabled:
            if not self.coins_addresses and self.mem.is_alive():
                # Attempt to probe if address already holds target
                matches = self.mem.scan_exact_value(self.frozen_coins_val, "int32")
                if matches and len(matches) <= 32:
                    self.coins_addresses = matches
                    print(f"[+] Found {len(matches)} address(es) already holding {self.frozen_coins_val}: {[hex(a) for a in matches[:8]]}")
                else:
                    print("\n" + "="*62)
                    print(" [!] MONKEY MONEY (COINS) MEMORY CALIBRATION REQUIRED")
                    print("="*62)
                    print(" To lock your Monkey Money continuously to 99,999:")
                    print(" 1. Check your current Monkey Money count (top-right of screen).")
                    print(" 2. In this console, type: coins <your_current_number>")
                    print("    (e.g. if you currently have 1,450 coins, type: coins 1450)")
                    print(" 3. The trainer will lock memory and freeze at 99,999 permanently!")
                    print("="*62 + "\n")
            elif self.coins_addresses and self.mem.is_alive():
                for addr in self.coins_addresses:
                    try:
                        self.mem.write_int32(addr, self.frozen_coins_val)
                    except Exception:
                        pass
                print(f"[+] Locked {len(self.coins_addresses)} Monkey Money address(es) to {self.frozen_coins_val:,}!")

    def _tick_coins(self):
        if self.coins_addresses and self.mem.is_alive():
            for addr in self.coins_addresses:
                try:
                    self.mem.write_int32(addr, self.frozen_coins_val)
                except Exception:
                    pass

    def _on_zero_cost_toggle(self, enabled: bool):
        print(f"\n[BTD6 Trainer] Zero-Cost Placement: {'ENABLED' if enabled else 'DISABLED'}")

    def _on_cooldown_toggle(self, enabled: bool):
        print(f"\n[BTD6 Trainer] Instant Cooldowns: {'ENABLED' if enabled else 'DISABLED'}")

    def _trigger_toggle_overlay(self):
        """Toggles visibility of the on-screen transparent HUD overlay."""
        if self.overlay:
            self.overlay.toggle_visibility()
            print("\n[BTD6 Trainer] Toggled On-Screen HUD Visibility.")
        else:
            print("\n[BTD6 Trainer] HUD Overlay is not attached or active.")

    def _trigger_reset_all(self):
        for feat in self.get_unique_features():
            if feat.is_toggle:
                feat.enabled = False
        if self.active_cash_patch:
            self.active_cash_patch.restore()
            self.active_cash_patch = None
        print("\n[*] All BTD6 cheats disabled. Normal game memory restored.")

    def get_status_dict(self) -> dict[str, Any]:
        """Serializes current trainer status for AI-BS web UI."""
        attached = self.mem.is_alive()
        return {
            "target": self.TARGET_EXE,
            "pid": self.mem.pid,
            "attached": attached,
            "game_assembly_base": hex(self.game_assembly_base) if self.game_assembly_base else "0x0",
            "cash_address": hex(self.cash_address) if self.cash_address else ("Multiple" if self.cash_addresses else "Not Set"),
            "cash_addresses": [hex(a) for a in self.cash_addresses],
            "cash_candidates_count": len(self.cash_candidates),
            "lives_address": hex(self.lives_address) if self.lives_address else ("Multiple" if self.lives_addresses else "Not Set"),
            "lives_addresses": [hex(a) for a in self.lives_addresses],
            "coins_addresses": [hex(a) for a in self.coins_addresses],
            "coins_candidates_count": len(self.coins_candidates),
            "features": [
                {
                    "name": feat.name,
                    "hotkey": feat.get_key_label(),
                    "vk_code": feat.hotkey_vk,
                    "secondary_vk_code": feat.secondary_hotkey_vk,
                    "enabled": feat.enabled,
                    "is_toggle": feat.is_toggle,
                    "description": feat.description
                }
                for feat in self.get_unique_features()
            ]
        }

