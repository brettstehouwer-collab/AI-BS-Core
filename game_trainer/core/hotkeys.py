"""
AI-BS Game Trainer Suite: Hotkey Management Engine
Background asynchronous hotkey polling via Win32 GetAsyncKeyState with debouncing.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable, Dict, Optional, Set

# Common Win32 Virtual Key Codes
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CANCEL = 0x03
VK_MBUTTON = 0x04
VK_BACK = 0x08
VK_TAB = 0x09
VK_CLEAR = 0x0C
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # ALT key
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21  # PAGE UP
VK_NEXT = 0x22   # PAGE DOWN
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_INSERT = 0x2D
VK_DELETE = 0x2E

# Number Pad Keys
VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69
VK_MULTIPLY = 0x6A
VK_ADD = 0x6B
VK_SEPARATOR = 0x6C
VK_SUBTRACT = 0x6D
VK_DECIMAL = 0x6E
VK_DIVIDE = 0x6F

# Function Keys
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

KEY_NAMES = {
    VK_NUMPAD0: "NUMPAD 0",
    VK_NUMPAD1: "NUMPAD 1",
    VK_NUMPAD2: "NUMPAD 2",
    VK_NUMPAD3: "NUMPAD 3",
    VK_NUMPAD4: "NUMPAD 4",
    VK_NUMPAD5: "NUMPAD 5",
    VK_NUMPAD6: "NUMPAD 6",
    VK_NUMPAD7: "NUMPAD 7",
    VK_NUMPAD8: "NUMPAD 8",
    VK_NUMPAD9: "NUMPAD 9",
    VK_F1: "F1",
    VK_F2: "F2",
    VK_F3: "F3",
    VK_F4: "F4",
    VK_F5: "F5",
    VK_F6: "F6",
    VK_F7: "F7",
    VK_F8: "F8",
    VK_F9: "F9",
    VK_F10: "F10",
    VK_F11: "F11",
    VK_F12: "F12",
    VK_INSERT: "INSERT",
    VK_DELETE: "DELETE",
    VK_HOME: "HOME",
    VK_END: "END",
}


class HotkeyManager:
    """
    Manages global keyboard hotkeys via background polling thread.
    Features automatic debouncing to prevent multiple rapid triggers.
    """

    def __init__(self, poll_interval_ms: int = 15, debounce_ms: int = 250):
        self.user32 = ctypes.windll.user32
        self.poll_interval = poll_interval_ms / 1000.0
        self.debounce_duration = debounce_ms / 1000.0

        self.callbacks: Dict[int, Callable[[], None]] = {}
        self.last_press_time: Dict[int, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, vk_code: int, callback: Callable[[], None]):
        """Registers a callback for a specific Virtual-Key code."""
        self.callbacks[vk_code] = callback
        self.last_press_time[vk_code] = 0.0

    def unregister(self, vk_code: int):
        """Unregisters a hotkey."""
        self.callbacks.pop(vk_code, None)
        self.last_press_time.pop(vk_code, None)

    def start(self):
        """Starts the background hotkey listener thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listener_loop, daemon=True, name="HotkeyListener")
        self._thread.start()

    def stop(self):
        """Stops the hotkey listener thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _listener_loop(self):
        while self._running:
            now = time.time()
            for vk_code, callback in list(self.callbacks.items()):
                # Most significant bit is set if the key is down
                state = self.user32.GetAsyncKeyState(vk_code)
                if state & 0x8000:
                    last_time = self.last_press_time.get(vk_code, 0.0)
                    if (now - last_time) >= self.debounce_duration:
                        self.last_press_time[vk_code] = now
                        try:
                            callback()
                        except Exception as e:
                            print(f"[HotkeyManager] Error in callback for key {hex(vk_code)}: {e}")
            time.sleep(self.poll_interval)
