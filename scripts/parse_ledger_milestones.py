import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== RECENT LEDGER MILESTONES (CHRONOLOGICAL) ===")
entries = []
for line in lines:
    if line.strip().startswith("|") and not line.strip().startswith("| Date") and not line.strip().startswith("|:"):
        parts = [p.strip() for p in line.strip().split("|")[1:-1]]
        if len(parts) >= 4:
            date, ver, title, details = parts[0], parts[1], parts[2], parts[3]
            entries.append((date, ver, title, len(details)))

for date, ver, title, det_len in entries[:20]:
    print(f"Date: {date:10s} | Version: {ver:8s} | Subsystem/Title: {title[:75]}")
