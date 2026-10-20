import os
import re
import json

FRONTEND_SRC = r"C:\AI-BS\frontend\src"
BACKEND_DIR = r"C:\AI-BS\backend"
AI_BS_ROOT = r"C:\AI-BS"

print("=" * 80)
print("     AI-BS CROSS-SUBSYSTEM INTEGRATION & PARTIAL MODULE AUDITOR")
print("=" * 80)

# 1. Inspect Frontend Tabs & Components
frontend_tabs = []
if os.path.exists(FRONTEND_SRC):
    for root, dirs, files in os.walk(FRONTEND_SRC):
        for f in files:
            if f.endswith(('.jsx', '.tsx', '.js', '.ts')):
                frontend_tabs.append(os.path.relpath(os.path.join(root, f), FRONTEND_SRC))

print(f"[FRONTEND] Found {len(frontend_tabs)} frontend source files.")

# 2. Extract API Fetch Calls in Frontend
api_fetch_calls = set()
fetch_pattern = re.compile(r'fetch\([`"\']([^`"\']+)|\/api\/[a-zA-Z0-9_\-\/]+')
for rel_path in frontend_tabs:
    full_path = os.path.join(FRONTEND_SRC, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()
            # find all /api/ endpoints
            matches = re.findall(r'[\'"`](\/api\/[a-zA-Z0-9_\-\/]+)[\'"`]', content)
            for m in matches:
                api_fetch_calls.add(m)
    except Exception:
        pass

print(f"[FRONTEND] Extracted {len(api_fetch_calls)} unique API route references:")
for r in sorted(api_fetch_calls):
    print(f"   -> {r}")

# 3. Extract Backend Endpoints in backend/
backend_routes = set()
router_files = []
for root, dirs, files in os.walk(BACKEND_DIR):
    for f in files:
        if f.endswith('.py'):
            router_files.append(os.path.join(root, f))

endpoint_pattern = re.compile(r'@(app|router)\.(get|post|put|delete|websocket)\([\'"]([^\'"]+)[\'"]')
for rf in router_files:
    try:
        with open(rf, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()
            matches = endpoint_pattern.findall(content)
            for _, method, path in matches:
                backend_routes.add(path)
    except Exception:
        pass

print(f"\n[BACKEND] Found {len(backend_routes)} backend route endpoints across {len(router_files)} python files.")

# 4. Check Standalone Apps & Scaffolds
subsystems = {
    "BroadcastStudioApp": os.path.exists(r"C:\AI-BS\BroadcastStudioApp"),
    "PrestigeMobileWash": os.path.exists(r"C:\AI-BS\PrestigeMobileWash"),
    "JuliesPlace": os.path.exists(r"C:\AI-BS\JuliesPlace"),
    "UnrealHub": os.path.exists(r"C:\AI-BS\UnrealHub"),
    "go-core": os.path.exists(r"C:\AI-BS\go-core"),
    "go_telemetry_gateway": os.path.exists(r"C:\AI-BS\go_telemetry_gateway"),
    "rust_master_worker": os.path.exists(r"C:\AI-BS\rust_master_worker"),
    "ComfyUI": os.path.exists(r"C:\AI-BS\ComfyUI"),
    "self_hosted_supabase": os.path.exists(r"C:\AI-BS\self_hosted_supabase"),
    "antigravity-sdk-python": os.path.exists(r"C:\AI-BS\antigravity-sdk-python"),
    "shared_cloud_drive": os.path.exists(r"C:\AI-BS\shared_cloud_drive"),
    "screenplay_projects": os.path.exists(r"C:\AI-BS\screenplay_projects"),
}

print("\n[SUBSYSTEMS STATUS]")
for name, exists in subsystems.items():
    print(f"  * {name:<25}: {'[EXISTS]' if exists else '[MISSING]'}")

print("=" * 80)