import os
import re

print("=== SCANNING FOR HARDCODED MONETARY DATA & MOCK BALANCES ===")

root_dirs = [r"C:\AI-BS\backend", r"C:\AI-BS\frontend\src\components"]

mock_patterns = [
    re.compile(r'["\'](?:portfolio_total_usd|balance_usd|total_balance|total_revenue|net_worth)["\']\s*:\s*[0-9]+', re.IGNORECASE),
    re.compile(r'\b(?:fake|mock|dummy|simulat(?:ed|e))_(?:transaction|balance|order|invoice|payout|account)\b', re.IGNORECASE),
    re.compile(r'["\'](?:amount_paid|usd_value)["\']\s*:\s*[0-9]+\.[0-9]+', re.IGNORECASE),
    re.compile(r'Test Secondary RTX GPU Rig', re.IGNORECASE)
]

for base_dir in root_dirs:
    for root, _, files in os.walk(base_dir):
        if any(skip in root for skip in [".venv", "node_modules", "__pycache__", ".git"]):
            continue
        for fname in files:
            if fname.endswith((".py", ".jsx", ".tsx", ".js", ".json")):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for pat in mock_patterns:
                        matches = pat.findall(content)
                        if matches:
                            rel = os.path.relpath(fpath, r"C:\AI-BS")
                            print(f"Match in {rel}: {matches[:3]}")
                except Exception:
                    pass
