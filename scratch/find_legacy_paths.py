import os
import ast

project_root = r"C:\AI-BS"
legacy_patterns = ["C:\\Workspaces\\Stehouwer_Server", "G:\\Stehouwer_Server", "S:\\", "F:\\"]

findings = []

for root, dirs, files in os.walk(project_root):
    # Skip archive and vendor directories
    if any(k in root.lower() for k in ["_archive", "quarantine", "scratch", "comfyui", "android studio", "node_modules", "venv", ".venv"]):
        continue
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    for pat in legacy_patterns:
                        if pat.lower() in line.lower():
                            findings.append({
                                "file": os.path.relpath(full_path, project_root),
                                "line": idx,
                                "pattern": pat,
                                "content": line.strip()
                            })
            except Exception as e:
                pass

print(f"Total legacy hardcoded path occurrences found in active project files: {len(findings)}")
for f in findings:
    print(f"File: {f['file']}:{f['line']} ({f['pattern']})\n   Content: {f['content']}")
