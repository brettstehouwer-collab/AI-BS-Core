import os
import sys
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'C:\AI-BS')

from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
from native_studio.engine import EngineBus
from native_studio.navigation_registry import get_all_subtabs_flat, NATIVE_MASTER_HUBS
from native_studio.app import MainWindow

app = QApplication.instance() or QApplication(sys.argv)
win = MainWindow()

all_subtabs = get_all_subtabs_flat()
print(f'Total subtabs in registry: {len(all_subtabs)}')

report = {}
total_buttons = 0
unconnected_total = 0

for item in all_subtabs:
    k = item.key
    view = win._get_or_create_subview(k)
    if not view:
        continue
    btns = view.findChildren((QPushButton, QToolButton))
    view_unconnected = []
    
    for b in btns:
        r = b.receivers(b.clicked)
        t = b.text() or b.toolTip() or b.objectName() or 'unnamed'
        if r == 0:
            view_unconnected.append(t)
            
    report[k] = {
        'hub': '',
        'label': item.label,
        'total': len(btns),
        'unconnected': len(view_unconnected),
        'unconnected_list': view_unconnected,
    }
    total_buttons += len(btns)
    unconnected_total += len(view_unconnected)

print(f'\n=== AUDIT ACROSS ALL {len(all_subtabs)} SUBTABS ===')
print(f'Total buttons found across all subtabs: {total_buttons}')
print(f'Total buttons with 0 receivers: {unconnected_total}')
for k, data in report.items():
    if data['unconnected'] > 0:
        print(f"  [SUBTAB {k} - {data['label']}]: {data['unconnected']} / {data['total']} buttons have 0 receivers")
        for u in data['unconnected_list'][:10]:
            safe_u = u.encode('ascii', 'replace').decode('ascii')
            print(f"      - {safe_u!r}")

print("\n=== DUMMY [UI_ACTION] PRINT CALLBACKS AUDIT ===")
import re
studio_dir = Path(r"C:\AI-BS\native_studio")
dummy_pattern = re.compile(r"print\([fF]?[\'\"]\[UI_ACTION\]")

total_dummy = 0
files_with_dummy = {}

for py_file in studio_dir.glob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    matches = dummy_pattern.findall(text)
    if matches:
        files_with_dummy[py_file.name] = len(matches)
        total_dummy += len(matches)

print(f"Total dummy print callbacks found: {total_dummy}")
for f, c in sorted(files_with_dummy.items(), key=lambda x: -x[1]):
    print(f"  {f:35s}: {c} dummy callback(s)")
