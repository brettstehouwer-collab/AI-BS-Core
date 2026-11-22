import json
import os

audit_path = r"C:\AI-BS\py_health_audit.json"
if not os.path.exists(audit_path):
    print("Audit JSON not found")
    exit(1)

with open(audit_path, "r", encoding="utf-8") as f:
    data = json.load(f)

details = data["details"]

def is_vendor(filepath):
    fp = filepath.lower()
    vendor_keywords = [
        "android studio", "comfyui", "_internal", "site-packages", 
        "dist-packages", "venv", ".venv", "plugins\\plugins\\nvidia",
        "resources\\brain_backend"
    ]
    return any(k in fp for k in vendor_keywords)

project_files = [d for d in details if not is_vendor(d["file"])]

print(f"Total Project Python Files (excluding third-party runtimes/bundled vendors): {len(project_files)}")

syntax_errors = [d for d in project_files if d["status"] in ("SYNTAX_ERROR", "PARSE_ERROR")]
empty_files = [d for d in project_files if d["size"] == 0]
broken_paths = [d for d in project_files if d["broken_paths"]]
archive_files = [d for d in project_files if d["is_archive"]]
active_files = [d for d in project_files if not d["is_archive"]]

print("\n--- SUMMARY FOR PROJECT CODE ---")
print(f"Active Python Files: {len(active_files)}")
print(f"Archived / Quarantine / Scratch Files: {len(archive_files)}")
print(f"Syntax Errors in Project Code: {len(syntax_errors)}")
print(f"Empty (.py 0-byte) Files: {len(empty_files)}")
print(f"Files with Missing Hardcoded Paths: {len(broken_paths)}")

if syntax_errors:
    print("\n--- SYNTAX ERRORS ---")
    for s in syntax_errors:
        print(f"  {s['rel_file']} ({s['root']}) -> {s['syntax_err']}")

if empty_files:
    print("\n--- EMPTY FILES ---")
    for e in empty_files[:20]:
        print(f"  {e['rel_file']} ({e['root']})")
    if len(empty_files) > 20:
        print(f"  ... and {len(empty_files)-20} more empty files")

if broken_paths:
    print("\n--- BROKEN PATH REFERENCES IN PROJECT CODE ---")
    for bp in broken_paths[:20]:
        print(f"  File: {bp['rel_file']}")
        for p in bp['broken_paths']:
            print(f"    -> Missing path: {p}")
