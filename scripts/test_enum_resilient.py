import win32gui
import win32process
import psutil

windows = []

def callback(hwnd, extra):
    try:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        title = title.strip()
        if not title or title in ["Program Manager", "Settings", "Windows Input Experience"]:
            return True
            
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w < 50 or h < 50:
            return True
            
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pname = psutil.Process(pid).name()
        except Exception:
            pname = "Unknown"
            pid = 0
            
        windows.append({
            "hwnd": hwnd,
            "title": title,
            "process_name": pname,
            "pid": pid,
            "width": w,
            "height": h
        })
    except Exception as e:
        # Ignore individual window errors
        pass
    return True

# In pywin32, EnumWindows passes (callback, extra)
try:
    win32gui.EnumWindows(callback, None)
except Exception as e:
    print(f"Top-level EnumWindows error: {e}")

print(f"Total windows found: {len(windows)}")
for w in windows:
    print(f"  - [{w['process_name']}] PID {w['pid']}: '{w['title']}' ({w['width']}x{w['height']})")
