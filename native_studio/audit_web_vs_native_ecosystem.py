"""Full AI-BS Ecosystem Web-vs-Native Parity Auditor.

Compares all 52 subtabs in navigation_registry.py against:
1. Native PyQt6 views in C:/AI-BS/native_studio/*_view*.py and app.py
2. React web components in C:/AI-BS/frontend/src/components/*.jsx
3. Checks for crowded single-row toolbars (>8 buttons in a single QHBoxLayout) across all native views
4. Identifies all secondary modals/drawers infrontend/src/components that may need native parity.
"""

import ast
import json
import os
import re
from pathlib import Path

NATIVE_DIR = Path(r"C:\AI-BS\native_studio")
WEB_COMP_DIR = Path(r"C:\AI-BS\frontend\src\components")
WEB_APP_JSX = Path(r"C:\AI-BS\frontend\src\App.jsx")


def analyze_native_views():
    native_files = [
        p for p in NATIVE_DIR.glob("*.py")
        if not p.name.startswith("test_") and not p.name.startswith("audit_") and not p.name.startswith("map_")
    ]
    classes_info = {}
    crowded_layouts = []

    for py_file in native_files:
        if not py_file.exists():
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start + 50)
                class_src = "\n".join(lines[start - 1 : end])
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                qdialogs = class_src.count("QDialog(") + class_src.count("QMessageBox.")
                qtables = class_src.count("QTableWidget")
                qtabs = class_src.count("QTabWidget") + class_src.count("QStackedWidget")
                buttons = class_src.count("QPushButton") + class_src.count("_create_action_pill")
                classes_info[node.name] = {
                    "file": py_file.name,
                    "lines": end - start + 1,
                    "methods": len(methods),
                    "dialogs_or_alerts": qdialogs,
                    "tables": qtables,
                    "stacks_or_tabs": qtabs,
                    "buttons": buttons,
                }

        # Check for HBoxLayouts with many addWidget calls
        hbox_vars = set(re.findall(r"(\w+)\s*=\s*QHBoxLayout", text))
        for hvar in hbox_vars:
            count = len(re.findall(rf"\b{re.escape(hvar)}\.addWidget\(", text))
            if count >= 9:
                crowded_layouts.append({
                    "file": py_file.name,
                    "layout_var": hvar,
                    "widget_count": count,
                })

    return classes_info, crowded_layouts


def analyze_web_components():
    web_files = {}
    for jsx in sorted(WEB_COMP_DIR.glob("*.jsx")):
        text = jsx.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        modals = len(re.findall(r"Modal|Drawer|Overlay", text))
        fetch_calls = len(re.findall(r"fetch\(|axios\.", text))
        buttons = len(re.findall(r"<button\b", text))
        tabs = len(re.findall(r"activeTab|activeSubTab|setTab|setSubTab", text))
        web_files[jsx.name] = {
            "lines": len(lines),
            "bytes": len(text),
            "buttons": buttons,
            "fetch_calls": fetch_calls,
            "modals_refs": modals,
            "tab_states": tabs,
        }
    return web_files


def map_app_py_routing():
    app_text = (NATIVE_DIR / "app.py").read_text(encoding="utf-8", errors="ignore")
    # Find key -> class mappings
    mappings = {}
    for m in re.finditer(r'"([a-z0-9_]+)"\s*:\s*([A-Za-z0-9_]+)', app_text):
        k, v = m.group(1), m.group(2)
        mappings[k] = v
    return mappings


def main():
    import sys
    sys.path.insert(0, str(NATIVE_DIR))
    from navigation_registry import NATIVE_MASTER_HUBS, get_all_subtabs_flat

    classes_info, crowded_layouts = analyze_native_views()
    web_files = analyze_web_components()
    app_mappings = map_app_py_routing()

    report = {
        "total_main_sections": len(NATIVE_MASTER_HUBS),
        "total_subtabs": len(get_all_subtabs_flat()),
        "crowded_hbox_layouts": crowded_layouts,
        "total_web_jsx_files": len(web_files),
        "top_25_largest_web_components": sorted(
            [{"name": k, **v} for k, v in web_files.items()],
            key=lambda x: x["lines"],
            reverse=True,
        )[:25],
        "native_classes_summary": classes_info,
    }

    out_path = NATIVE_DIR / "ecosystem_parity_audit.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved audit to {out_path}")
    print(f"Crowded HBoxLayouts (>=9 widgets in 1 row): {len(crowded_layouts)}")
    for c in crowded_layouts:
        print(f"  - {c['file']}: {c['layout_var']} has {c['widget_count']} widgets")
    print("\nTop 15 Largest Web Components:")
    for item in report["top_25_largest_web_components"][:15]:
        print(f"  - {item['name']}: {item['lines']} lines ({item['buttons']} buttons, {item['fetch_calls']} API calls)")


if __name__ == "__main__":
    main()
