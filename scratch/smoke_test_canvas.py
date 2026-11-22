import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from native_studio.omni_broadcast_studio import (
    LiveBroadcastCanvas,
    ActiveGameDiscoveryWidget,
    get_desktop_capture_windows,
)

app = QApplication(sys.argv)
canvas = LiveBroadcastCanvas()
discovery = ActiveGameDiscoveryWidget()

discovery.game_selected.connect(lambda title, hwnd: canvas.set_active_source(title, hwnd))
discovery.fetch_active_windows()

count = discovery.combo_games.count()
print(f"Discovery combo populated with {count} items.")
for i in range(min(5, count)):
    print(f"  Item {i}: {discovery.combo_games.itemText(i)}")

# Test selecting item
if count > 1:
    discovery.combo_games.setCurrentIndex(1)
    print(f"Active source title on canvas: {canvas.active_source_title}")

canvas.shutdown()
discovery.shutdown()
print("Interactive pipeline smoke test PASSED!")
