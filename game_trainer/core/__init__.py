"""
AI-BS Game Trainer Engine Core Package
"""

from .memory import (
    MemoryManager,
    MemoryPatch,
    PROCESSENTRY32,
    MODULEENTRY32,
    MEMORY_BASIC_INFORMATION
)
from .hotkeys import (
    HotkeyManager,
    KEY_NAMES,
    VK_NUMPAD0, VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4,
    VK_NUMPAD5, VK_NUMPAD6, VK_NUMPAD7, VK_NUMPAD8, VK_NUMPAD9,
    VK_F1, VK_F2, VK_F3, VK_F4, VK_F5, VK_F6, VK_F7, VK_F8, VK_F9, VK_F10, VK_F11, VK_F12,
    VK_INSERT, VK_DELETE, VK_HOME, VK_END
)
from .trainer import (
    TrainerBase,
    CheatFeature
)

__all__ = [
    "MemoryManager",
    "MemoryPatch",
    "HotkeyManager",
    "TrainerBase",
    "CheatFeature",
    "KEY_NAMES",
    "VK_NUMPAD0", "VK_NUMPAD1", "VK_NUMPAD2", "VK_NUMPAD3", "VK_NUMPAD4",
    "VK_NUMPAD5", "VK_NUMPAD6", "VK_NUMPAD7", "VK_NUMPAD8", "VK_NUMPAD9",
    "VK_F1", "VK_F2", "VK_F3", "VK_F4", "VK_F5", "VK_F6", "VK_F7", "VK_F8", "VK_F9", "VK_F10", "VK_F11", "VK_F12",
    "VK_INSERT", "VK_DELETE", "VK_HOME", "VK_END"
]
