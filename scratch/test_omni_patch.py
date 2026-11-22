from native_studio.omni_broadcast_studio import (
    LiveBroadcastCanvas,
    ActiveGameDiscoveryWidget,
    get_desktop_capture_windows,
)

wins = get_desktop_capture_windows()
print(f"Windows enumerated: {len(wins)}")
for w in wins:
    print(f" - [{w['hwnd']}] {w['title']} ({w['width']}x{w['height']})")

print("All classes and functions imported and verified successfully!")
