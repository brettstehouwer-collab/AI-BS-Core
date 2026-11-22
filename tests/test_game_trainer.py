"""
AI-BS Game Trainer Suite: Verification Test Suite
Tests memory reading, writing, pointer resolution, byte patching, and signature scanning.
"""

import sys
import os
import ctypes
import unittest
import time

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_trainer.core.memory import MemoryManager, MemoryPatch
from game_trainer.core.hotkeys import HotkeyManager, VK_F12
from game_trainer.core.trainer import TrainerBase, CheatFeature, TrainerVariable
from game_trainer.mock_game.target_sandbox import PlayerData, EntityNode, WorldContext, GameEngineRoot


class TestGameTrainer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Attach to own process for deterministic memory testing
        cls.current_pid = os.getpid()
        cls.mem = MemoryManager(cls.current_pid)

    @classmethod
    def tearDownClass(cls):
        cls.mem.detach()

    def test_01_primitive_read_write(self):
        """Tests reading and writing integers, floats, and strings in process memory."""
        test_int = ctypes.c_int32(1337)
        addr = ctypes.addressof(test_int)

        # Read
        val = self.mem.read_int32(addr)
        self.assertEqual(val, 1337)

        # Write
        self.mem.write_int32(addr, 9999)
        self.assertEqual(test_int.value, 9999)

        # Float
        test_float = ctypes.c_float(3.14159)
        f_addr = ctypes.addressof(test_float)
        self.assertAlmostEqual(self.mem.read_float(f_addr), 3.14159, places=4)
        self.mem.write_float(f_addr, 42.5)
        self.assertAlmostEqual(test_float.value, 42.5, places=4)

        # String
        test_str = ctypes.create_string_buffer(b"AI-BS Trainer Active")
        str_addr = ctypes.addressof(test_str)
        self.assertEqual(self.mem.read_string(str_addr, 32), "AI-BS Trainer Active")

    def test_02_multi_level_pointer_resolution(self):
        """Tests traversing multi-level dynamic pointer hierarchy."""
        player = PlayerData(
            health=250,
            shield=100,
            ammo=45,
            score=5000,
            speed=2.5,
            is_invulnerable=False,
            player_name=b"TestCommander"
        )
        entity = EntityNode(
            entity_id=99,
            padding=0,
            player_ptr=ctypes.pointer(player)
        )
        world = WorldContext(
            world_id=7,
            padding=0,
            active_entity_ptr=ctypes.pointer(entity)
        )
        root = GameEngineRoot(
            magic_marker=0xDEADBEEF,
            padding=0,
            world_ptr=ctypes.pointer(world)
        )

        root_addr = ctypes.addressof(root)
        player_addr = ctypes.addressof(player)

        # Offsets: root -> [world_ptr: 0x8] -> [entity_ptr: 0x8] -> [player_ptr: 0x8] -> [health: 0x0]
        # In our struct:
        # GameEngineRoot: magic_marker(4), padding(4) => world_ptr is at offset 0x8
        # WorldContext: world_id(4), padding(4) => active_entity_ptr is at offset 0x8
        # EntityNode: entity_id(4), padding(4) => player_ptr is at offset 0x8
        resolved_player_addr = self.mem.resolve_pointer_chain(
            root_addr,
            offsets=[0x8, 0x8, 0x8, 0x0]
        )
        self.assertEqual(resolved_player_addr, player_addr)

        # Read health through resolved pointer
        hp = self.mem.read_int32(resolved_player_addr)
        self.assertEqual(hp, 250)

        # Modify health through resolved pointer
        self.mem.write_int32(resolved_player_addr, 10000)
        self.assertEqual(player.health, 10000)

    def test_03_memory_patch_and_restore(self):
        """Tests applying byte patches and restoring original data."""
        test_buf = ctypes.create_string_buffer(b"\x55\x8B\xEC\x83\xEC\x10") # Sample prologue
        addr = ctypes.addressof(test_buf)

        # NOP first 3 bytes
        patch = self.mem.nop_instruction(addr, count=3)
        self.assertEqual(self.mem.read_bytes(addr, 6), b"\x90\x90\x90\x83\xEC\x10")

        # Restore
        patch.restore()
        self.assertEqual(self.mem.read_bytes(addr, 6), b"\x55\x8B\xEC\x83\xEC\x10")

    def test_04_aob_signature_scan(self):
        """Tests signature scanning with wildcard bytes."""
        # Create unique pattern in memory
        unique_sig = ctypes.create_string_buffer(b"\x48\x8B\x05\x77\x88\x99\xAA\x48\x85\xC0")
        sig_addr = ctypes.addressof(unique_sig)

        # Scan for pattern with wildcards
        pattern = "48 8B 05 ?? ?? ?? ?? 48 85 C0"
        results = self.mem.aob_scan(pattern)
        self.assertIn(sig_addr, results)

    def test_05_cheat_feature_toggle(self):
        """Tests CheatFeature toggle and trigger dispatch."""
        toggled = False
        def toggle_cb(state):
            nonlocal toggled
            toggled = state

        feat = CheatFeature(
            name="Test Cheat",
            hotkey_vk=VK_F12,
            description="Toggle test",
            is_toggle=True,
            on_toggle=toggle_cb
        )

    def test_06_dual_binding_hotkeys(self):
        """Tests dual-binding hotkeys (F-keys + Numpad) in TrainerBase."""
        from game_trainer.core.hotkeys import VK_F1, VK_NUMPAD1

        toggled = False
        def toggle_cb(state):
            nonlocal toggled
            toggled = state

        feat = CheatFeature(
            name="Dual-Bound Cash",
            hotkey_vk=VK_F1,
            secondary_hotkey_vk=VK_NUMPAD1,
            description="Dual key test",
            is_toggle=True,
            on_toggle=toggle_cb
        )

        self.assertEqual(feat.get_key_label(), "F1 / NUMPAD 1")

        trainer = TrainerBase(target_process="python.exe")
        trainer.add_feature(feat)

        # Both keys should be registered in features dict
        self.assertIn(VK_F1, trainer.features)
        self.assertIn(VK_NUMPAD1, trainer.features)
        self.assertEqual(trainer.features[VK_F1], feat)
        self.assertEqual(trainer.features[VK_NUMPAD1], feat)

        # Unique features should only contain one instance
        self.assertEqual(len(trainer.get_unique_features()), 1)

        # Toggling via one key toggles the feature
        trainer.features[VK_NUMPAD1].toggle()
        self.assertTrue(feat.enabled)
        self.assertTrue(toggled)

        trainer.features[VK_F1].toggle()
        self.assertFalse(feat.enabled)
        self.assertFalse(toggled)

    def test_07_overlay_instantiation(self):
        """Tests TrainerOverlay instantiation and state synchronization."""
        from game_trainer.core.overlay import TrainerOverlay

        trainer = TrainerBase(target_process="python.exe")
        overlay = TrainerOverlay(trainer, title="Test HUD")
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay.visible)
        self.assertFalse(overlay.click_through)

        overlay.toggle_visibility()
        self.assertFalse(overlay.visible)
        overlay.toggle_visibility()
        self.assertTrue(overlay.visible)

    def test_08_scan_exact_value(self):
        """Tests scan_exact_value and filter_scan across heap memory."""
        test_val = ctypes.c_double(123456.789)
        test_addr = ctypes.addressof(test_val)

        # Scan for the exact double
        matches = self.mem.scan_exact_value(123456.789, "double")
        self.assertIn(test_addr, matches)

        # Filter scan with matching value
        filtered = self.mem.filter_scan(matches, 123456.789, "double")
        self.assertIn(test_addr, filtered)

        # Modify value and verify filter_scan tracks it
        test_val.value = 987654.321
        filtered_new = self.mem.filter_scan(matches, 987654.321, "double")
        self.assertIn(test_addr, filtered_new)

    def test_09_trainer_variable_registration(self):
        """Tests TrainerVariable registration and setters."""
        trainer = TrainerBase(target_process="python.exe")
        
        called_with = None
        def mock_setter(val):
            nonlocal called_with
            called_with = val
            
        var = TrainerVariable(
            key="cash",
            name="Match Cash",
            var_type="float",
            get_val=lambda: 123.45,
            set_val=mock_setter
        )
        trainer.add_variable(var)
        
        self.assertIn("cash", trainer.variables)
        self.assertEqual(trainer.variables["cash"].get_val(), 123.45)
        
        trainer.variables["cash"].set_val(999.99)
        self.assertEqual(called_with, 999.99)

    def test_10_alignment_and_filter_scan(self):
        """Tests that scan_exact_value discards unaligned false matches."""
        # 1. Properly aligned c_double
        aligned_double = ctypes.c_double(88888.5)
        aligned_addr = ctypes.addressof(aligned_double)

        # 2. Intentionally unaligned byte placement (offset 3)
        raw_buf = ctypes.create_string_buffer(32)
        import struct
        packed = struct.pack("<d", 88888.5)
        raw_buf.raw = b"ABC" + packed + b"\x00" * (29 - len(packed))
        unaligned_addr = ctypes.addressof(raw_buf) + 3

        self.assertNotEqual(unaligned_addr % 8, 0)

        # Scan with default natural alignment (alignment=8 for double)
        matches = self.mem.scan_exact_value(88888.5, "double", alignment=8)
        self.assertIn(aligned_addr, matches)
        self.assertNotIn(unaligned_addr, matches)

    def test_11_btd6_profile_candidate_pipeline(self):
        """Tests BTD6Trainer first_scan_cash and next_scan_cash narrowing pipeline."""
        from game_trainer.profiles.btd6_profile import BTD6Trainer

        btd6 = BTD6Trainer(target_pid=self.current_pid)
        self.assertTrue(btd6.setup())

        # Seed test in-game cash
        live_cash = ctypes.c_double(650.0)
        cash_addr = ctypes.addressof(live_cash)

        # First scan
        candidates = btd6.first_scan_cash(650.0)
        self.assertIn(cash_addr, candidates)
        self.assertIn(cash_addr, btd6.cash_candidates)

        # Simulate in-game cash delta (buy tower)
        live_cash.value = 435.0

        # Next scan (filters down)
        narrowed = btd6.next_scan_cash(435.0)
        self.assertIn(cash_addr, narrowed)
        self.assertIn(cash_addr, btd6.cash_addresses)
        self.assertEqual(btd6.cash_address, cash_addr)

        # Verify get_status_dict serialization
        st = btd6.get_status_dict()
        self.assertIn("cash_candidates_count", st)
        self.assertGreaterEqual(st["cash_candidates_count"], 1)
        self.assertIn(hex(cash_addr), st["cash_addresses"])

        btd6.stop()

if __name__ == "__main__":
    unittest.main()

