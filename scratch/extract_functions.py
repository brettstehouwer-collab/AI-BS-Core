import os
import re

out_file = r"C:\AI-BS\function_manifest.txt"
functions = set()

py_regex = re.compile(r"^\s*def\s+([a-zA-Z0-9_]+)")
go_regex = re.compile(r"^\s*func\s+([a-zA-Z0-9_]+)")
ts_regex = re.compile(r"(?:function\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*\([^)]*\)\s*=>)")

for root, dirs, files in os.walk(r"C:\AI-BS"):
    if any(exclude in root for exclude in ["node_modules", ".git", "venv", "__pycache__", "build", "sandbox"]):
        continue
    for file in files:
        path = os.path.join(root, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if file.endswith(".py"):
                    functions.update(py_regex.findall(content))
                elif file.endswith(".go"):
                    functions.update(go_regex.findall(content))
                elif file.endswith(".ts") or file.endswith(".tsx"):
                    for m in ts_regex.finditer(content):
                        func = m.group(1) or m.group(2)
                        if func:
                            functions.add(func)
        except Exception:
            pass

with open(out_file, "w", encoding="utf-8") as f:
    for func in sorted(functions):
        f.write(func + "\n")
