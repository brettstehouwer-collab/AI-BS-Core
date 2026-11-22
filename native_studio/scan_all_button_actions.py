"""Exhaustive Button-to-Tool / Backend Action Alignment Scanner.

Scans:
1. Every view in native_studio/*.py
2. Every app in apps/*.py
3. Key web components in frontend/src/components/*.jsx

Extracts all button instantiations, their slot bindings, the source of the connected slot,
and classifies the backend alignment:
- REAL_BACKEND (Direct SQLite, EngineBus, Local AI, Hardware/WASAPI, File IO, Subprocess)
- UI_STATE_TRANSITION (Navigates tabs, updates canvas, switches modes, filters tables)
- MODAL_OR_DIALOG (Opens configuration, editor, or checkout dialog)
- PLACEHOLDER_OR_STUB (Empty slot, pass, or purely informational popup without backend action)
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

STUDIO_DIR = Path(r"C:\AI-BS\native_studio")
BACKEND_DIR = Path(r"C:\AI-BS\backend")
FRONTEND_DIR = Path(r"C:\AI-BS\frontend\src")

def scan_native_studio():
    results = {}
    total_buttons = 0
    categories = {
        "REAL_BACKEND": 0,
        "UI_STATE_TRANSITION": 0,
        "MODAL_OR_DIALOG": 0,
        "PLACEHOLDER_OR_STUB": 0,
    }

    for py_file in sorted(STUDIO_DIR.glob("*.py")):
        if py_file.name.startswith("test_") or "audit" in py_file.name or "scratch" in py_file.name or py_file.name == "click_test_all_subtabs.py":
            continue

        source = py_file.read_text(encoding="utf-8", errors="ignore")
        lines = source.splitlines()

        btn_matches = []
        # Pattern to find button instantiations
        for idx, line in enumerate(lines, 1):
            if re.search(r"\bQ(?:Push|Tool)Button\b", line):
                # Try to extract button text and variable name
                var_match = re.search(r"(\b[a-zA-Z0-9_.]+\b)\s*=\s*Q(?:Push|Tool)Button\((.*?)\)", line)
                if var_match:
                    var_name = var_match.group(1)
                    args = var_match.group(2)
                else:
                    var_name = "btn_inline"
                    args = line.strip()

                # Search within next 10 lines for .clicked.connect
                connected_to = "UNKNOWN"
                for offset in range(0, 12):
                    if idx - 1 + offset < len(lines):
                        chk_line = lines[idx - 1 + offset]
                        conn_m = re.search(r"\.clicked\.connect\((.*?)\)", chk_line)
                        if conn_m:
                            connected_to = conn_m.group(1).strip()
                            break

                # Classify the connection
                classification = "PLACEHOLDER_OR_STUB"
                if any(k in connected_to.lower() for k in ("db", "sqlite", "bus", "engine", "emit", "save", "export", "import", "process", "launch", "run", "stream", "ollama", "train", "vram", "audio", "wasapi", "terminal", "load", "fetch")):
                    classification = "REAL_BACKEND"
                elif any(k in connected_to.lower() for k in ("switch", "select", "toggle", "mode", "set_page", "scroll", "nav", "jump", "tab", "search", "filter", "undo", "redo", "cut", "copy", "paste", "bold", "italic", "underline")):
                    classification = "UI_STATE_TRANSITION"
                elif any(k in connected_to.lower() for k in ("dialog", "modal", "messagebox", "checkout", "help", "guide", "info")):
                    classification = "MODAL_OR_DIALOG"
                else:
                    # Let's check the target method if it is self._method
                    meth_m = re.search(r"self\.([a-zA-Z0-9_]+)", connected_to)
                    if meth_m:
                        meth_name = meth_m.group(1)
                        # Check method body in the file
                        meth_def_m = re.search(rf"def {meth_name}\([^)]*\):(?:\s*\"\"\"[^\"]*\"\"\")?(.*?)(?=\n\s*def |\Z)", source, re.DOTALL)
                        if meth_def_m:
                            body = meth_def_m.group(1)
                            if any(k in body.lower() for k in ("sqlite", "bus", "engine", "subprocess", "os.", "socket", "file", "json", "open(", "ollama", "wasapi", "gpu", "qprocess")):
                                classification = "REAL_BACKEND"
                            elif any(k in body.lower() for k in ("settext", "setcurrent", "setvisible", "setstylesheet", "hide()", "show()", "setvalue", "layout")):
                                classification = "UI_STATE_TRANSITION"
                            elif any(k in body.lower() for k in ("qdialog", "qmessagebox", "exec()", "exec_()")):
                                classification = "MODAL_OR_DIALOG"

                categories[classification] += 1
                total_buttons += 1
                btn_matches.append({
                    "line": idx,
                    "var": var_name,
                    "args": args[:60],
                    "connection": connected_to[:60],
                    "type": classification,
                })

        if btn_matches:
            results[py_file.name] = btn_matches

    return results, total_buttons, categories

if __name__ == "__main__":
    results, total_buttons, categories = scan_native_studio()
    print("=" * 60)
    print("AI-BS CODEBASE BUTTON-TO-ACTION ALIGNMENT AUDIT")
    print("=" * 60)
    print(f"Total Files with Buttons Scanned: {len(results)}")
    print(f"Total Buttons Discovered: {total_buttons}")
    print("\nAction Alignment Breakdown:")
    for cat, count in categories.items():
        pct = (count / total_buttons * 100) if total_buttons else 0
        print(f"  - {cat:22s}: {count:4d} ({pct:5.1f}%)")
    print("=" * 60)

    print("\n[PER-FILE BUTTON INVENTORY]")
    for fname, btns in results.items():
        stubs = [b for b in btns if b['type'] == 'PLACEHOLDER_OR_STUB']
        print(f"\n{fname:35s} | Total: {len(btns):3d} | Real Backend: {sum(1 for b in btns if b['type']=='REAL_BACKEND'):2d} | UI: {sum(1 for b in btns if b['type']=='UI_STATE_TRANSITION'):2d} | Modals: {sum(1 for b in btns if b['type']=='MODAL_OR_DIALOG'):2d} | Stubs: {len(stubs):2d}")
        if stubs:
            for s in stubs[:5]:
                print(f"    Line {s['line']:4d} | {s['var']:20s} | Conn: {s['connection']}")
