"""
AI-BS Game Trainer Suite: Game Profile Template
Use this template to create an external trainer for any single-player / offline game.
Follow the offset finding guide in the comments below.
"""

import sys
import os
import time
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from game_trainer.core.memory import MemoryManager
from game_trainer.core.hotkeys import (
    HotkeyManager,
    VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4, VK_NUMPAD0
)
from game_trainer.core.trainer import TrainerBase, CheatFeature


class CustomGameTrainer(TrainerBase):
    """
    Template for building a custom game trainer.

    STEP 1: Find Static Base & Offsets
    - Open Cheat Engine and attach to your game (e.g. 'ac_client.exe').
    - Scan for current value (e.g., Health = 100).
    - Take damage, filter scan (e.g., Health = 85).
    - Right click address -> 'Find out what writes to this address'.
    - Record instruction (e.g., 'sub [eax+0xF8], ecx').
    - Offset is 0xF8. EAX contains player pointer.
    - Scan for value of EAX to find the pointer to player struct.
    - Identify static green pointer: 'ac_client.exe + 0x10F4F4'.

    STEP 2: Define Offsets
    """

    # Target executable name
    TARGET_PROCESS = "my_game.exe"

    # Static pointer base offset from main module
    STATIC_PLAYER_BASE = 0x10F4F4

    # Multi-level pointer chain offsets: [level1, level2, ... final_offset]
    OFFSETS_HEALTH = [0xF8]
    OFFSETS_ARMOR  = [0xFC]
    OFFSETS_AMMO   = [0x150, 0x14]  # Example nested pointer: player -> weapon -> ammo

    def __init__(self):
        super().__init__(target_process=self.TARGET_PROCESS, poll_rate_ms=25)
        self.player_base_addr = 0
        self.health_addr = 0
        self.ammo_addr = 0

        self._init_features()

    def _init_features(self):
        # Hotkey: NUMPAD 1 -> God Mode (Freeze Health at 999)
        self.add_feature(CheatFeature(
            name="God Mode",
            hotkey_vk=VK_NUMPAD1,
            description="Freezes health at 999 HP",
            is_toggle=True,
            on_toggle=self._on_godmode_toggle,
            on_tick=self._tick_godmode
        ))

        # Hotkey: NUMPAD 2 -> Unlimited Ammo
        self.add_feature(CheatFeature(
            name="Infinite Ammo",
            hotkey_vk=VK_NUMPAD2,
            description="Locks current weapon ammo count",
            is_toggle=True,
            on_tick=self._tick_infinite_ammo
        ))

        # Hotkey: NUMPAD 3 -> One-Hit Kill or Add Resource
        self.add_feature(CheatFeature(
            name="Add 10,000 Currency",
            hotkey_vk=VK_NUMPAD3,
            description="Increments in-game currency",
            is_toggle=False,
            on_trigger=self._trigger_add_currency
        ))

        # Hotkey: NUMPAD 0 -> Disable All
        self.add_feature(CheatFeature(
            name="Disable All Cheats",
            hotkey_vk=VK_NUMPAD0,
            description="Turns off all active toggles",
            is_toggle=False,
            on_trigger=self._trigger_disable_all
        ))

    def resolve_addresses(self) -> bool:
        """Resolves dynamic addresses using module base and pointer chains."""
        if not self.mem.is_alive():
            return False

        module_base = self.mem.base_address
        if not module_base:
            return False

        try:
            # Resolve static player base
            base_ptr = module_base + self.STATIC_PLAYER_BASE

            # Chasing pointers
            self.health_addr = self.mem.resolve_pointer_chain(base_ptr, self.OFFSETS_HEALTH)
            self.ammo_addr = self.mem.resolve_pointer_chain(base_ptr, self.OFFSETS_AMMO)
            return True
        except Exception as e:
            # Address may not be ready if game is in loading screen or main menu
            return False

    def _on_godmode_toggle(self, enabled: bool):
        print(f"[Trainer] God Mode: {'ACTIVE' if enabled else 'DISABLED'}")

    def _tick_godmode(self):
        if self.health_addr:
            self.mem.write_int32(self.health_addr, 999)

    def _tick_infinite_ammo(self):
        if self.ammo_addr:
            self.mem.write_int32(self.ammo_addr, 99)

    def _trigger_add_currency(self):
        # Example one-shot memory addition
        pass

    def _trigger_disable_all(self):
        for feat in self.features.values():
            if feat.is_toggle:
                feat.enabled = False
        print("[Trainer] All cheats disabled.")


if __name__ == "__main__":
    trainer = CustomGameTrainer()
    print(f"Waiting for {trainer.TARGET_PROCESS}...")
    while not trainer.try_attach():
        time.sleep(1.0)

    print(f"Attached to {trainer.TARGET_PROCESS} (PID: {trainer.mem.pid})")
    trainer.start()
    trainer.print_dashboard()

    try:
        while True:
            time.sleep(1.0)
            if not trainer.mem.is_alive():
                print("Target process exited.")
                break
            trainer.resolve_addresses()
    except KeyboardInterrupt:
        trainer.stop()
