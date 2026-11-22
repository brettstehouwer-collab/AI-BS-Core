"""Automated Orphan Signal Patcher for AI-BS Native Studio View Modules.

Scans all *_view.py files in native_studio for QPushButton and QToolButton definitions
that lack an explicit .clicked.connect(...) binding, and wires deterministic EngineBus
callbacks directly into the source files.
"""

import re
import sys
from pathlib import Path

STUDIO_DIR = Path(__file__).resolve().parent


def patch_view_file(file_path: Path) -> int:
    source = file_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    button_defs = {}

    assign_pattern = re.compile(r"^(\s*)(self\.[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s*=\s*Q(?:Push|Tool)Button\((.*)\)")
    for idx, line in enumerate(lines):
        m = assign_pattern.match(line)
        if m:
            indent, var_name, args = m.groups()
            button_defs[var_name] = (idx, indent, args)

    patched_count = 0
    new_lines = list(lines)
    offset = 0

    for var_name, (line_idx, indent, args) in button_defs.items():
        connect_pattern = re.compile(rf"\b{re.escape(var_name)}\.clicked\.connect\(")
        if not connect_pattern.search(source):
            clean_name = var_name.replace("self.", "")
            wire_stmt = (
                f"{indent}{var_name}.clicked.connect("
                f"lambda checked=False, action='{clean_name}': "
                f"getattr(self, 'bus', getattr(self, 'engine_bus', None)) and "
                f"getattr(self, 'bus', getattr(self, 'engine_bus', None)).emit_event('{clean_name}_triggered', {{}}))"
            )
            insert_at = line_idx + 1 + offset
            new_lines.insert(insert_at, wire_stmt)
            offset += 1
            patched_count += 1

    if patched_count > 0:
        file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return patched_count


def main() -> None:
    total_patched = 0
    for vf in sorted(STUDIO_DIR.glob("*_view.py")):
        count = patch_view_file(vf)
        if count > 0:
            print(f"[PATCHED] {vf.name}: wired {count} orphaned button(s)")
            total_patched += count
    print(f"[SUMMARY] Total orphaned buttons permanently wired: {total_patched}")


if __name__ == "__main__":
    main()
