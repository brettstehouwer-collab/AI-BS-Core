"""Generate 52-Subtab 1:1 Web-vs-Native Deep Comparison Matrix."""

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

NATIVE_DIR = Path(r"C:\AI-BS\native_studio")
WEB_COMP_DIR = Path(r"C:\AI-BS\frontend\src\components")

sys.path.insert(0, str(NATIVE_DIR))
from navigation_registry import NATIVE_MASTER_HUBS

audit_data = json.loads((NATIVE_DIR / "ecosystem_parity_audit.json").read_text(encoding="utf-8"))
native_classes = audit_data["native_classes_summary"]

# Parse app.py to map subtab key -> Native Class
app_py_text = (NATIVE_DIR / "app.py").read_text(encoding="utf-8", errors="ignore")
key_to_native_cls = {}
for m in re.finditer(r'if\s+key\s*==\s*"([a-z0-9_]+)"[^:]*:\s*\n\s*view\s*=\s*([A-Za-z0-9_]+)\(', app_py_text):
    key_to_native_cls[m.group(1)] = m.group(2)
for m in re.finditer(r'key\s+in\s*\(([^)]+)\):\s*\n\s*view\s*=\s*([A-Za-z0-9_]+)\(', app_py_text):
    cls_name = m.group(2)
    for k in re.findall(r'"([a-z0-9_]+)"', m.group(1)):
        key_to_native_cls[k] = cls_name
key_to_native_cls["music_daw"] = "MusicDawView"

# Parse all JSX files in frontend/src to map subtab key -> Web Component
key_to_web_comp = {}
for jsx_path in list(Path(r"C:\AI-BS\frontend\src").rglob("*.jsx")):
    t = jsx_path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"activeTab\s*===\s*['\"]([a-z0-9_]+)['\"][^<]*<([A-Za-z0-9_]+)", t):
        key_to_web_comp[m.group(1)] = m.group(2)
    for m in re.finditer(r"case\s+['\"]([a-z0-9_]+)['\"]:\s*return\s*<([A-Za-z0-9_]+)", t):
        key_to_web_comp[m.group(1)] = m.group(2)

# Manual known aliases in web Dashboard.jsx
web_manual = {
    "unified_creation": "UniversalCreationSuiteTab",
    "bv_media_creator": "BsMediaCreatorTab",
    "comfy_workspace": "ComfyUIStudioTab",
    "theatrical_teleprompter": "TheatricalTeleprompterTab",
    "neon_lounge_studio": "NeonLoungeStudioTab",
    "screen_mirror": "WirelessScreenMirrorTab",
    "master_accounting": "MasterAccountingTab",
    "notos_enterprise": "NotoEnterpriseTab",
    "steam_gaming": "SteamGamingHubTab",
    "nutrition_subsystem": "NutritionDetoxTab",
    "cluster_engine": "ClusterEngineTab",
}
for k, v in web_manual.items():
    if k not in key_to_web_comp:
        key_to_web_comp[k] = v

rows = []
for hub in NATIVE_MASTER_HUBS:
    print(f"\n=== {hub.icon} {hub.label} ({len(hub.sub_tabs)} tabs) ===")
    for st in hub.sub_tabs:
        n_cls = key_to_native_cls.get(st.key, "Unknown")
        n_info = native_classes.get(n_cls, {})
        w_comp = key_to_web_comp.get(st.key, "")
        w_lines = 0
        if w_comp and (WEB_COMP_DIR / f"{w_comp}.jsx").exists():
            w_lines = len((WEB_COMP_DIR / f"{w_comp}.jsx").read_text(encoding="utf-8", errors="ignore").splitlines())
        n_lines = n_info.get("lines", 0)
        ratio = round(n_lines / w_lines, 2) if w_lines > 0 else 1.0
        rows.append({
            "hub": hub.label,
            "key": st.key,
            "label": st.label,
            "native_class": n_cls,
            "native_file": n_info.get("file", ""),
            "native_lines": n_lines,
            "native_buttons": n_info.get("buttons", 0),
            "web_comp": w_comp,
            "web_lines": w_lines,
            "parity_ratio": ratio,
        })
        print(
            f"  [{st.key:24s}] Native: {n_cls:34s} ({n_lines:4d}L, {n_info.get('buttons', 0):2d} btns) | Web: {w_comp:28s} ({w_lines:4d}L)"
        )

(NATIVE_DIR / "subtabs_52_parity_matrix.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
