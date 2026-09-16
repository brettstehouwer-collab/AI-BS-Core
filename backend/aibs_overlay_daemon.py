import webview
import ctypes
import time
import threading
import sys
import os

def make_click_through(window):
    # Wait for the window to actually render
    time.sleep(2)
    # Get HWND using ctypes by finding the window title
    hwnd = ctypes.windll.user32.FindWindowW(None, window.title)
    if hwnd:
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # Apply the layered and transparent (click-through) styles
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        print("Overlay set to click-through!")
    else:
        print("Could not find HWND for the overlay window.")

if __name__ == '__main__':
    print("Starting AI-BS Hardware-Accelerated Overlay Engine...")
    url = "http://localhost:5173/overlay"
    
    # Create a full-screen transparent frameless window
    # We use a specific title to find it easily in the Win32 API
    window = webview.create_window(
        'AI_BS_WIDGET_OVERLAY', 
        url, 
        transparent=True, 
        frameless=True, 
        on_top=True,
        fullscreen=True
    )
    
    # Start the thread that hooks into Win32 to make it click-through
    threading.Thread(target=make_click_through, args=(window,), daemon=True).start()
    
    # Start the PyWebView UI loop
    webview.start()
