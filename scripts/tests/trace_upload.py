"""Trace file upload logic in ChatTab and related components (excluding node_modules)."""

import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

print("=== Searching frontend components (excluding node_modules) ===")
keywords = ["upload", "attachment", "formdata", "file", "/api/artifacts", "/api/upload", "unexpected end of json", "attachments", "uploadfile"]

matches = []
for root, dirs, files in os.walk(ROOT / "frontend" / "src"):
    if "node_modules" in root:
        continue
    for f in files:
        if f.endswith((".jsx", ".js", ".tsx", ".ts")):
            p = Path(root) / f
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for kw in keywords:
                    for line_no, line in enumerate(content.splitlines(), 1):
                        if kw in line.lower() and not line.strip().startswith("//"):
                            matches.append((f, line_no, kw, line.strip()[:100], str(p)))
            except Exception as e:
                pass

chat_matches = [m for m in matches if "chat" in m[0].lower()]
print(f"Total matches in Chat-related files: {len(chat_matches)}")
for fname, line_no, kw, snippet, path in chat_matches:
    print(f"{fname:25}:{line_no:4} [{kw:10}] {snippet}")

print("\n=== All frontend non-node_modules upload/attachment matches ===")
for fname, line_no, kw, snippet, path in sorted(matches, key=lambda x: x[0]):
    if any(k in kw for k in ["upload", "attachment", "formdata"]):
        print(f"{fname:30}:{line_no:4} [{kw:12}] {snippet}")
