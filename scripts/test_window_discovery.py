import subprocess
import json
import psutil
import ctypes

# Method 1: PowerShell Get-Process MainWindowTitle
print("=== Method 1: PowerShell MainWindowTitle ===")
ps_cmd = 'powershell -NoProfile -Command "Get-Process | Where-Object { $_.MainWindowTitle -ne \'\' } | Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"'
try:
    res = subprocess.run(ps_cmd, capture_output=True, text=True, shell=True)
    items = json.loads(res.stdout)
    if isinstance(items, dict):
        items = [items]
    for it in items:
        print(f"  - PID {it['Id']}: {it['ProcessName']} -> \"{it['MainWindowTitle']}\"")
except Exception as e:
    print(f"Error in PS: {e}")

# Method 2: ctypes EnumWindows with c_int
print("\n=== Method 2: ctypes EnumWindows ===")
user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            if title:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    pname = psutil.Process(pid.value).name()
                except Exception:
                    pname = "Unknown"
                print(f"  [HWND {hwnd}] PID {pid.value} ({pname}): \"{title}\"")
    return 1

cb = WNDENUMPROC(enum_cb)
user32.EnumWindows(cb, 0)
