import os
import re

root_dir = r"C:\AI-BS"
backend_dir = os.path.join(root_dir, "backend")
frontend_dir = os.path.join(root_dir, "frontend", "src")

root_files = [f for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))]

def collect_content(target_dir, extensions):
    content = ""
    for root, _, files in os.walk(target_dir):
        if any(skip in root for skip in [".venv", "node_modules", ".git", "__pycache__", "dist", "build"]):
            continue
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as fh:
                        content += "\n" + fh.read()
                except Exception:
                    pass
    return content

backend_content = collect_content(backend_dir, [".py", ".json", ".bat", ".sh", ".yaml"])
frontend_content = collect_content(frontend_dir, [".jsx", ".js", ".json", ".css", ".html"])

backend_referenced = []
frontend_referenced = []
orphaned_or_standalone = []

for rf in root_files:
    in_b = rf in backend_content
    in_f = rf in frontend_content
    if in_b:
        backend_referenced.append(rf)
    if in_f:
        frontend_referenced.append(rf)
    if not in_b and not in_f:
        orphaned_or_standalone.append(rf)

print(f"Total Root Files: {len(root_files)}")
print(f"Referenced in Backend: {len(backend_referenced)}")
print(f"Referenced in Frontend: {len(frontend_referenced)}")
print(f"Standalone / Operational Root Files: {len(orphaned_or_standalone)}")
print("\nSample Backend Referenced:", backend_referenced[:15])
print("\nSample Frontend Referenced:", frontend_referenced[:15])
print("\nSample Standalone/Operational:", orphaned_or_standalone[:15])
