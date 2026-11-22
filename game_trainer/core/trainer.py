"""
AI-BS Game Trainer Suite: Base Trainer Framework
Provides high-level abstraction for features, value freezing, auto-attach watchdogs,
and interactive console dashboards.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from .memory import MemoryManager, MemoryPatch
from .hotkeys import HotkeyManager, KEY_NAMES, VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4, VK_NUMPAD5


class TrainerVariable:
    """Represents an editable game variable (e.g., Cash, Lives, Coins, Speed)."""
    def __init__(
        self,
        key: str,
        name: str,
        var_type: str,
        get_val: Callable[[], Any],
        set_val: Callable[[Any], None],
        presets: Optional[List[Any]] = None,
        unit_prefix: str = "",
        unit_suffix: str = "",
        step: Optional[float] = None,
        description: str = ""
    ):
        self.key = key
        self.name = name
        self.var_type = var_type
        self.get_val = get_val
        self.set_val = set_val
        self.presets = presets or []
        self.unit_prefix = unit_prefix
        self.unit_suffix = unit_suffix
        self.step = step
        self.description = description


class CheatFeature:
    """Represents a single cheat or modification feature within a trainer."""
    def __init__(
        self,
        name: str,
        hotkey_vk: int,
        description: str,
        is_toggle: bool = True,
        on_toggle: Optional[Callable[[bool], None]] = None,
        on_trigger: Optional[Callable[[], None]] = None,
        on_tick: Optional[Callable[[], None]] = None,
        secondary_hotkey_vk: Optional[int] = None
    ):
        self.name = name
        self.hotkey_vk = hotkey_vk
        self.secondary_hotkey_vk = secondary_hotkey_vk
        self.description = description
        self.is_toggle = is_toggle
        self.enabled = False
        self.on_toggle = on_toggle
        self.on_trigger = on_trigger
        self.on_tick = on_tick
        self.associated_patch: Optional[MemoryPatch] = None

    def get_key_label(self) -> str:
        """Returns human-readable combination string (e.g. 'F1 / NUM 1')."""
        prim = KEY_NAMES.get(self.hotkey_vk, f"0x{self.hotkey_vk:02X}")
        if self.secondary_hotkey_vk is not None:
            sec = KEY_NAMES.get(self.secondary_hotkey_vk, f"0x{self.secondary_hotkey_vk:02X}")
            return f"{prim} / {sec}"
        return prim

    def toggle(self):
        """Toggles the feature state or executes one-shot trigger."""
        if self.is_toggle:
            self.enabled = not self.enabled
            if self.on_toggle:
                self.on_toggle(self.enabled)
        else:
            if self.on_trigger:
                self.on_trigger()

    def tick(self):
        """Called every frame/tick if enabled (for value freezing)."""
        if self.enabled and self.on_tick:
            self.on_tick()


class TrainerBase:
    """
    Base class for application-specific game trainers.
    Handles process attachment, watchdogs, freeze loops, and hotkey binding.
    """

    def __init__(self, target_process: str, poll_rate_ms: int = 20):
        self.target_process = target_process
        self.poll_rate = poll_rate_ms / 1000.0
        self.mem = MemoryManager()
        self.hotkeys = HotkeyManager()
        self.features: Dict[int, CheatFeature] = {}
        self.feature_list: List[CheatFeature] = []
        self.variables: Dict[str, TrainerVariable] = {}
        self.running = False
        self._freeze_thread: Optional[threading.Thread] = None

    def add_feature(self, feature: CheatFeature):
        """Adds a feature and binds its hotkey(s) to the hotkey dispatcher."""
        if feature not in self.feature_list:
            self.feature_list.append(feature)

        self.features[feature.hotkey_vk] = feature
        self.hotkeys.register(feature.hotkey_vk, feature.toggle)

        if feature.secondary_hotkey_vk is not None:
            self.features[feature.secondary_hotkey_vk] = feature
            self.hotkeys.register(feature.secondary_hotkey_vk, feature.toggle)

    def get_unique_features(self) -> List[CheatFeature]:
        """Returns list of distinct CheatFeature instances."""
        return list(self.feature_list)

    def add_variable(self, variable: TrainerVariable):
        """Registers an interactive game variable to the trainer profile."""
        self.variables[variable.key] = variable

    def get_variables(self) -> List[TrainerVariable]:
        """Returns list of registered interactive game variables."""
        return list(self.variables.values())

    def set_variable(self, key: str, val: Any) -> bool:
        """Sets a registered variable by key. Returns True if successful."""
        if key in self.variables:
            try:
                self.variables[key].set_val(val)
                return True
            except Exception as e:
                print(f"[Trainer] Failed to set variable {key}: {e}")
        return False

    def start(self):
        """Starts the trainer engine, hotkeys, and freeze tick loop."""
        self.running = True
        self.hotkeys.start()

        self._freeze_thread = threading.Thread(target=self._tick_loop, daemon=True, name="TrainerTickLoop")
        self._freeze_thread.start()

    def stop(self):
        """Stops the trainer, restores all memory modifications, and detaches."""
        self.running = False
        self.hotkeys.stop()
        if self._freeze_thread and self._freeze_thread.is_alive():
            self._freeze_thread.join(timeout=1.0)
        self.mem.detach()

    def try_attach(self) -> bool:
        """Attempts to attach to target process if not currently attached."""
        if self.mem.is_alive():
            return True

        try:
            self.mem.attach(self.target_process)
            return True
        except Exception:
            return False

    def _tick_loop(self):
        """Background loop executing continuous freeze actions for active cheats."""
        while self.running:
            if self.mem.is_alive():
                for feature in self.get_unique_features():
                    if feature.enabled and feature.on_tick:
                        try:
                            feature.tick()
                        except Exception as e:
                            print(f"[Trainer] Error ticking feature '{feature.name}': {e}")
            time.sleep(self.poll_rate)

    def print_dashboard(self):
        """Renders an ASCII status dashboard to the console."""
        attached = self.mem.is_alive()
        status_str = f"ATTACHED (PID {self.mem.pid}, Base: {hex(self.mem.base_address)})" if attached else "WAITING FOR PROCESS..."

        print("\n" + "=" * 70)
        print(f"       AI-BS GAME TRAINER: {self.target_process}")
        print("=" * 70)
        print(f" Status: {status_str}")
        print("-" * 70)
        print(f" {'HOTKEY':<18} | {'FEATURE':<22} | {'STATUS':<10} | {'DESCRIPTION'}")
        print("-" * 70)

        for feat in self.get_unique_features():
            key_name = feat.get_key_label()
            status = "ON" if feat.enabled else "OFF"
            if not feat.is_toggle:
                status = "TRIGGER"
            print(f" {key_name:<18} | {feat.name:<22} | {status:<10} | {feat.description}")

        print("=" * 70)
        print(" Press Ctrl+C in terminal to exit cleanly.\n")

