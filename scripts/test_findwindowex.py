import win32gui
import win32process
import win32con
import psutil

print("=== Testing FindWindowEx window traversal ===")
windows = []
hwnd = win32gui.FindWindowEx(0, 0, None, None)

while hwnd:
    try:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and len(title.strip()) > 0:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 50 and h > 50:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        pname = psutil.Process(pid).name()
                    except Exception:
                        pname = "Unknown"
                        pid = 0
                    
                    if title not in ["Program Manager", "Settings", "Windows Input Experience"]:
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "process_name": pname,
                            "pid": pid,
                            "width": w,
                            "height": h
                        })
    except Exception as e:
        pass
    hwnd = win32gui.FindWindowEx(0, hwnd, None, None)

print(f"Discovered {len(windows)} active application windows via FindWindowEx:")
for w in windows:
    print(f"  🎮 Window: '{w['title']}' | Process: '{w['process_name']}' (PID: {w['pid']}) | {w['width']}x{w['height']}")

# Check for games
print("\n--- Identified Game Windows ---")
for w in windows:
    pname = w['process_name'].lower()
    title = w['title'].lower()
    if any(g in pname or g in title for g in ['fortnite', 'cod', 'warzone', 'valorant', 'apex', 'roblox', 'minecraft', 'steam', 'overwatch', 'cyberpunk', 'shipping', 'game', 'unreal']):
        print(f"  >>> ACTIVE GAME HOOK: '{w['title']}' ({w['process_name']}, PID: {w['pid']})")
