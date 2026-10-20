import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

windows = []

def enum_windows_callback(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            
            if title and w > 100 and h > 100:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pname = "Unknown"
                try:
                    pname = psutil.Process(pid.value).name()
                except Exception:
                    pass
                
                # Filter out shell tray and hidden manager windows
                if title not in ["Program Manager", "Settings", "Windows Input Experience"]:
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "process_name": pname,
                        "pid": pid.value,
                        "width": w,
                        "height": h
                    })
    return True

cb = WNDENUMPROC(enum_windows_callback)
user32.EnumWindows(cb, 0)

print(f"Discovered {len(windows)} active application windows:")
for w in windows:
    print(f"  🎮 Window: '{w['title']}' | Process: '{w['process_name']}' (PID: {w['pid']}) | {w['width']}x{w['height']}")

# Game process detector
print("\n--- Detected Games ---")
for w in windows:
    pname = w['process_name'].lower()
    title = w['title'].lower()
    if 'fortnite' in pname or 'fortnite' in title or 'cod' in pname or 'warzone' in pname or 'apex' in pname or 'valorant' in pname or 'overwatch' in pname or 'minecraft' in pname or 'roblox' in pname or 'shipping' in pname:
        print(f"  >>> ACTIVE GAME HOOK FOUND: '{w['title']}' ({w['process_name']})")
