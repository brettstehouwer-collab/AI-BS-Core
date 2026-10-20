import os
import time
import datetime
import subprocess

now = time.time()
twelve_hours_ago = now - (12 * 3600)

print(f"Current local time: {datetime.datetime.fromtimestamp(now)}")
print(f"12 hours ago cutoff: {datetime.datetime.fromtimestamp(twelve_hours_ago)}")

# 1. Check Git Commits in last 12-24 hours
try:
    res = subprocess.run(["git", "log", "--since=24.hours", "--oneline"], cwd=r"C:\AI-BS", capture_output=True, text=True)
    print("\n=== GIT COMMITS IN PAST 24 HOURS ===")
    print(res.stdout if res.stdout else "No recent git commits / git not tracking.")
except Exception as e:
    print(f"Git check error: {e}")

# 2. Check files modified in the past 12 hours across C:\AI-BS
print("\n=== SCANNING MODIFIED FILES IN C:\\AI-BS (PAST 12 HOURS) ===")
modified_files = []
ignore_dirs = {'.git', 'node_modules', '.cache', '__pycache__', 'dist', 'pyppeteer_env'}

for root, dirs, files in os.walk(r"C:\AI-BS"):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.system_generated')]
    for f in files:
        fp = os.path.join(root, f)
        try:
            mtime = os.path.getmtime(fp)
            if mtime >= twelve_hours_ago:
                modified_files.append((mtime, fp, os.path.getsize(fp)))
        except Exception:
            pass

modified_files.sort(key=lambda x: x[0], reverse=True)
print(f"Total files modified in past 12 hours: {len(modified_files)}")

# Group by category / folder
categories = {}
for mtime, fp, size in modified_files:
    rel = os.path.relpath(fp, r"C:\AI-BS")
    top_dir = rel.split(os.sep)[0]
    categories.setdefault(top_dir, []).append((datetime.datetime.fromtimestamp(mtime).strftime("%H:%M:%S"), rel))

for cat, flist in sorted(categories.items()):
    print(f"\n[{cat}] ({len(flist)} files):")
    for t_str, rel in flist[:15]:
        print(f"  {t_str} - {rel}")
    if len(flist) > 15:
        print(f"  ... and {len(flist)-15} more files")
