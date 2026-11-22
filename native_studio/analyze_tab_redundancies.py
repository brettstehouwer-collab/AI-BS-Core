import sys
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv[:1])

from native_studio.navigation_registry import NATIVE_MASTER_HUBS, PINNED_QUICK_TABS
from native_studio.app import MainWindow

# Inspect how MainWindow routes each key
# We will create an instance or mock bus to call _get_or_create_subview for every single key
from native_studio.engine import EngineBus

bus = EngineBus()

class DummyHub:
    pass

class MockMainWindow(MainWindow):
    def __init__(self):
        # We only want to test _get_or_create_subview without full UI
        self._subviews_cache = {}
        self.bus = bus
        self.gpu_probe = None
        self.hub = DummyHub()
        self.view_daw = None

mock = MockMainWindow()

print("="*80)
print("PINNED QUICK TABS:")
print("="*80)
for pt in PINNED_QUICK_TABS:
    k = pt["key"]
    v = mock._get_or_create_subview(k)
    cls_name = v.__class__.__name__ if v else "None"
    print(f"[{pt['badge']}] {pt['label']:<30} (key: {k:<25}) -> {cls_name}")

print("\n" + "="*80)
print("MASTER HUBS & SUB-TABS ROUTING:")
print("="*80)
view_to_subtabs = {}
unmapped_keys = []

for hub in NATIVE_MASTER_HUBS:
    print(f"\n--- Hub: {hub.label} ({hub.key}) ---")
    for sub in hub.sub_tabs:
        k = sub.key
        v = mock._get_or_create_subview(k)
        cls_name = v.__class__.__name__ if v else "None"
        is_default_fallback = (cls_name == "ExecutiveCockpitFullView" and k not in ("executive_cockpit", "dashboard"))
        status = "⚠️ UNMAPPED FALLBACK" if is_default_fallback else "OK"
        if is_default_fallback:
            unmapped_keys.append((hub.label, sub.label, k))
        view_to_subtabs.setdefault(cls_name, []).append((hub.label, sub.label, k, sub.description))
        print(f"  [{status}] {sub.label:<32} (key: {k:<25}) -> {cls_name}")

print("\n" + "="*80)
print(f"ANALYSIS: UNMAPPED SUBTABS FALLING BACK TO ExecutiveCockpitFullView ({len(unmapped_keys)} total):")
print("="*80)
for h, lbl, k in unmapped_keys:
    print(f"  * [{h}] '{lbl}' (key: '{k}')")

print("\n" + "="*80)
print("ANALYSIS: VIEWS WITH MULTIPLE REDUNDANT TABS MAPPED TO THEM:")
print("="*80)
for v_name, items in view_to_subtabs.items():
    if len(items) > 1:
        print(f"\nTarget View: >>> {v_name} <<< (mapped by {len(items)} tabs):")
        for h, lbl, k, desc in items:
            print(f"   • [{h}] {lbl:<32} (key: '{k}')")
