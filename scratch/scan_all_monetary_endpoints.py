import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
backend_dir = r"C:\AI-BS\backend"

endpoint_pattern = re.compile(r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')

endpoints = []
for root, dirs, files in os.walk(backend_dir):
    for f in files:
        if f.endswith(".py"):
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, backend_dir)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read()
            matches = endpoint_pattern.findall(content)
            for method, path in matches:
                if any(k in path.lower() for k in ["trade", "crypto", "account", "wallet", "payout", "bill", "storefront", "tax"]):
                    endpoints.append((rel, method.upper(), path))

print(f"Monetary Endpoints ({len(endpoints)}):")
for rel, method, path in sorted(endpoints):
    print(f"  [{method}] {path:<45} ({rel})")
