"""
AI-BS Game Trainer Suite: Concrete Sandbox Trainer Implementation
Demonstrates process attachment, multi-level pointer resolution, value freezing,
and global hotkeys targeting the Titan Arena mock sandbox.
"""

import sys
import os
import time
import argparse
from typing import Optional

# Ensure package root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from game_trainer.core.memory import MemoryManager
from game_trainer.core.hotkeys import (
    HotkeyManager, KEY_NAMES,
    VK_NUMPAD0, VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4, VK_NUMPAD5
)
from game_trainer.core.trainer import TrainerBase, CheatFeature


class SandboxTrainer(TrainerBase):
    """
    Concrete trainer targeting the Mock Game Sandbox.
    Demonstrates pointer-chain offsets and memory freeze loops.
    """

    def __init__(self, target_pid: Optional[int] = None, root_addr: Optional[int] = None):
        super().__init__(target_process="python.exe", poll_rate_ms=20)
        self.target_pid = target_pid
        self.root_addr = root_addr
        self.player_addr: int = 0

        # Memory Offsets within PlayerData
        self.OFFSET_HEALTH = 0x00       # int32
        self.OFFSET_SHIELD = 0x04       # int32
        self.OFFSET_AMMO = 0x08         # int32
        self.OFFSET_SCORE = 0x0C        # int32
        self.OFFSET_SPEED = 0x10        # float
        self.OFFSET_INVULNERABLE = 0x14 # bool
        self.OFFSET_NAME = 0x15         # char[32]

        self._register_features()

    def _register_features(self):
        # 1. Infinite Health (Freezes HP at 9999 every tick)
        self.add_feature(CheatFeature(
            name="Infinite Health (9999)",
            hotkey_vk=VK_NUMPAD1,
            description="Freezes player health to 9999 HP",
            is_toggle=True,
            on_toggle=lambda enabled: print(f"\n[!] Infinite Health: {'ENABLED' if enabled else 'DISABLED'}"),
            on_tick=self._tick_infinite_health
        ))

        # 2. Infinite Ammo (Freezes Ammo at 999)
        self.add_feature(CheatFeature(
            name="Infinite Ammo (999)",
            hotkey_vk=VK_NUMPAD2,
            description="Freezes weapon ammo count to 999",
            is_toggle=True,
            on_toggle=lambda enabled: print(f"\n[!] Infinite Ammo: {'ENABLED' if enabled else 'DISABLED'}"),
            on_tick=self._tick_infinite_ammo
        ))

        # 3. Add 50,000 Score (One-shot action)
        self.add_feature(CheatFeature(
            name="Add 50,000 Score",
            hotkey_vk=VK_NUMPAD3,
            description="Instantly increments player score by 50,000 points",
            is_toggle=False,
            on_trigger=self._trigger_add_score
        ))

        # 4. Super Shield (200)
        self.add_feature(CheatFeature(
            name="Max Overshield (200)",
            hotkey_vk=VK_NUMPAD4,
            description="Sets and locks energy shield to 200",
            is_toggle=True,
            on_toggle=lambda enabled: print(f"\n[!] Max Overshield: {'ENABLED' if enabled else 'DISABLED'}"),
            on_tick=self._tick_max_shield
        ))

        # 5. Native Invulnerability Flag
        self.add_feature(CheatFeature(
            name="Invulnerability Flag",
            hotkey_vk=VK_NUMPAD5,
            description="Toggles the game's internal is_invulnerable flag",
            is_toggle=True,
            on_toggle=self._toggle_invulnerability
        ))

        # 0. Emergency Restore / Reset
        self.add_feature(CheatFeature(
            name="Reset Normal Stats",
            hotkey_vk=VK_NUMPAD0,
            description="Disables all active cheats and sets HP=100, Ammo=30",
            is_toggle=False,
            on_trigger=self._trigger_reset_stats
        ))

    def setup_connection(self) -> bool:
        """Connects to target PID and resolves pointer chain."""
        if not self.target_pid:
            print("[Trainer] Scanning active processes for target PID...")
            # If no PID provided, user is prompted or fallback
            return False

        print(f"[Trainer] Attaching to PID {self.target_pid}...")
        self.mem.attach(self.target_pid)

        # If root_addr was provided, resolve pointer chain:
        # root -> [0x8: world_ptr] -> [0x8: active_entity_ptr] -> [0x8: player_ptr] -> [0x0: PlayerData]
        if self.root_addr and not self.player_addr:
            try:
                self.player_addr = self.mem.resolve_pointer_chain(
                    self.root_addr,
                    offsets=[0x8, 0x8, 0x8, 0x0]
                )
                print(f"[Trainer] Successfully resolved PlayerData address: {hex(self.player_addr)}")
            except Exception as e:
                print(f"[Trainer] Pointer chain resolution warning: {e}")
                self.player_addr = self.root_addr
        return True

    def set_player_address(self, addr: int):
        self.player_addr = addr

    # -------------------------------------------------------------------------
    # Cheat Action Handlers
    # -------------------------------------------------------------------------

    def _tick_infinite_health(self):
        if self.player_addr:
            self.mem.write_int32(self.player_addr + self.OFFSET_HEALTH, 9999)

    def _tick_infinite_ammo(self):
        if self.player_addr:
            self.mem.write_int32(self.player_addr + self.OFFSET_AMMO, 999)

    def _tick_max_shield(self):
        if self.player_addr:
            self.mem.write_int32(self.player_addr + self.OFFSET_SHIELD, 200)

    def _trigger_add_score(self):
        if self.player_addr:
            current = self.mem.read_int32(self.player_addr + self.OFFSET_SCORE)
            new_score = current + 50000
            self.mem.write_int32(self.player_addr + self.OFFSET_SCORE, new_score)
            print(f"\n[+] Added 50,000 Score! New Score: {new_score}")

    def _toggle_invulnerability(self, enabled: bool):
        if self.player_addr:
            self.mem.write_bool(self.player_addr + self.OFFSET_INVULNERABLE, enabled)

    def _trigger_reset_stats(self):
        for feat in self.features.values():
            if feat.is_toggle:
                feat.enabled = False
        if self.player_addr:
            self.mem.write_int32(self.player_addr + self.OFFSET_HEALTH, 100)
            self.mem.write_int32(self.player_addr + self.OFFSET_SHIELD, 50)
            self.mem.write_int32(self.player_addr + self.OFFSET_AMMO, 30)
            self.mem.write_bool(self.player_addr + self.OFFSET_INVULNERABLE, False)
        print("\n[*] All cheats disabled. Standard stats restored (HP=100, Shield=50, Ammo=30).")

    def read_live_stats(self) -> dict:
        if not self.player_addr or not self.mem.is_alive():
            return {}
        return {
            "health": self.mem.read_int32(self.player_addr + self.OFFSET_HEALTH),
            "shield": self.mem.read_int32(self.player_addr + self.OFFSET_SHIELD),
            "ammo": self.mem.read_int32(self.player_addr + self.OFFSET_AMMO),
            "score": self.mem.read_int32(self.player_addr + self.OFFSET_SCORE),
            "invulnerable": self.mem.read_bool(self.player_addr + self.OFFSET_INVULNERABLE),
            "name": self.mem.read_string(self.player_addr + self.OFFSET_NAME, 32)
        }


def main():
    parser = argparse.ArgumentParser(description="AI-BS Game Trainer (Mock Sandbox Target)")
    parser.add_argument("--pid", type=int, help="Target process ID of target_sandbox.py")
    parser.add_argument("--root", type=lambda x: int(x, 0), help="Hex/Int base root address (e.g. 0x0000021A4B0C23E0)")
    parser.add_argument("--player", type=lambda x: int(x, 0), help="Direct hex/int address of PlayerData struct")
    args = parser.parse_args()

    pid = args.pid
    if not pid:
        pid_input = input("Enter target process PID (from mock sandbox): ").strip()
        if pid_input:
            pid = int(pid_input)

    trainer = SandboxTrainer(target_pid=pid, root_addr=args.root)

    if args.player:
        trainer.set_player_address(args.player)

    if not trainer.setup_connection():
        print("Failed to initialize process attachment.")
        return

    trainer.start()
    trainer.print_dashboard()

    try:
        while True:
            time.sleep(1.0)
            if not trainer.mem.is_alive():
                print("\n[!] Target process terminated. Detaching trainer.")
                break
            stats = trainer.read_live_stats()
            if stats:
                print(f"\r[Live Memory Monitor] Name: {stats['name']} | HP: {stats['health']:<5} | Shield: {stats['shield']:<4} | Ammo: {stats['ammo']:<4} | Score: {stats['score']:<7} | Invulnerable: {stats['invulnerable']}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n[Trainer] Exiting cleanly...")
    finally:
        trainer.stop()
        print("[Trainer] Detached and shutdown complete.")


if __name__ == "__main__":
    main()
