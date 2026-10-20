import win32gui
import win32process
import win32con
import psutil
import ctypes
from ctypes import wintypes

print("=== 1. FindWindowEx on GetDesktopWindow() ===")
desktop = win32gui.GetDesktopWindow()
print(f"Desktop HWND: {desktop}")
hwnd = win32gui.FindWindowEx(desktop, 0, None, None)
count1 = 0
while hwnd:
    title = win32gui.GetWindowText(hwnd)
    if title:
        print(f"  - [{hwnd}] {title}")
        count1 += 1
    hwnd = win32gui.FindWindowEx(desktop, hwnd, None, None)
print(f"Count 1: {count1}")

print("\n=== 2. GetWindow(desktop, GW_CHILD) ===")
hwnd2 = win32gui.GetWindow(desktop, win32con.GW_CHILD)
count2 = 0
while hwnd2:
    title = win32gui.GetWindowText(hwnd2)
    if title:
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd2)
            pname = psutil.Process(pid).name()
            print(f"  - [{pname} / PID {pid}] HWND {hwnd2}: '{title}'")
        except Exception:
            print(f"  - [{hwnd2}] {title}")
        count2 += 1
    hwnd2 = win32gui.GetWindow(hwnd2, win32con.GW_HWNDNEXT)
print(f"Count 2: {count2}")
