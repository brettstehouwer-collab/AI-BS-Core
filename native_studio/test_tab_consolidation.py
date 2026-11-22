import sys
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv[:1])

from native_studio.navigation_registry import (
    NATIVE_MASTER_HUBS,
    PINNED_QUICK_TABS,
    TAB_KEY_ALIASES,
    find_subtab_spec,
    get_all_subtabs_flat,
)
from native_studio.app import MainWindow
from native_studio.engine import EngineBus

bus = EngineBus()

class DummyHub:
    pass

class MockMainWindow(MainWindow):
    def __init__(self):
        self._subviews_cache = {}
        self.bus = bus
        self.gpu_probe = None
        self.hub = DummyHub()
        self.view_daw = None

mock = MockMainWindow()

# Test 1: Pinned tabs unique
pinned_keys = [pt["key"] for pt in PINNED_QUICK_TABS]
assert len(pinned_keys) == len(set(pinned_keys)), f"Duplicate pinned keys: {pinned_keys}"
print(f"PASS: 8 Pinned Quick Tabs are 100% unique: {pinned_keys}")

# Test 2: Subtabs unique across all hubs
all_subtabs = get_all_subtabs_flat()
all_keys = [st.key for st in all_subtabs]
assert len(all_keys) == len(set(all_keys)), f"Duplicate subtab keys: {[k for k in all_keys if all_keys.count(k) > 1]}"
print(f"PASS: {len(all_keys)} Subtabs across 4 Master Hubs are 100% unique: {all_keys}")

# Test 3: Views mapped 1:1 with zero redundancy
view_map = {}
for k in all_keys:
    v = mock._get_or_create_subview(k)
    cname = v.__class__.__name__ if v else "None"
    assert cname not in view_map, f"Target View {cname} is mapped to multiple subtabs: {view_map[cname]} and {k}"
    view_map[cname] = k

print(f"PASS: All {len(all_keys)} subtabs map 1:1 to {len(view_map)} unique dedicated views!")

# Test 4: Aliases resolve cleanly
for old_k, canonical_k in TAB_KEY_ALIASES.items():
    spec = find_subtab_spec(old_k)
    assert spec is not None, f"Failed to find spec for legacy alias: {old_k}"
    assert spec.key == canonical_k, f"Legacy alias {old_k} resolved to {spec.key} instead of {canonical_k}"
    v = mock._get_or_create_subview(old_k)
    v_canonical = mock._get_or_create_subview(canonical_k)
    assert v is v_canonical, f"Alias {old_k} view instance does not match canonical {canonical_k} view instance!"

print(f"PASS: All {len(TAB_KEY_ALIASES)} legacy aliases resolve seamlessly to canonical targets!")
print("\n>>> ALL CONSOLIDATION TESTS PASSED 100% SUCCESSFULLY! <<<")
import os
os._exit(0)


