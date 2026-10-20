import os
import json

LOGS_DIR = r"C:\AI-BS\logs"

print("=" * 75)
print("                  AI-BS DAEMON LOGS & TELEMETRY AUDIT")
print("=" * 75)

if not os.path.exists(LOGS_DIR):
    print("Logs directory does not exist.")
    exit(0)

files = os.listdir(LOGS_DIR)
print(f"Total Log / Telemetry Files in C:\\AI-BS\\logs: {len(files)}\n")

for f in sorted(files):
    p = os.path.join(LOGS_DIR, f)
    if os.path.isfile(p):
        sz_kb = os.path.getsize(p) / 1024
        # Count lines if text
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                lines = sum(1 for _ in fp)
        except Exception:
            lines = 0
        print(f"  * {f:<38} | {sz_kb:>8.1f} KB | {lines:>6} lines")

print("=" * 75)