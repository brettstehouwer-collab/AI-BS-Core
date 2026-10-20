import os
import time
import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

now = time.time()
twelve_hours_ago = now - (12 * 3600)

subsystems = [
    r"C:\AI-BS\backend",
    r"C:\AI-BS\frontend\src",
    r"C:\AI-BS\scripts",
    r"C:\AI-BS\docs",
    r"C:\AI-BS\saved_data",
    r"C:\AI-BS\go-core"
]

ignore_dirs = {'.git', 'node_modules', '.cache', '__pycache__', 'dist', 'pyppeteer_env'}

print(f"=== 12-HOUR CODEBASE ACTIVITY AUDIT ===")
print(f"Window: {datetime.datetime.fromtimestamp(twelve_hours_ago).strftime('%Y-%m-%d %H:%M:%S')} ➔ {datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")

all_modified = []
for sub in subsystems:
    for root, dirs, files in os.walk(sub):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            fp = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(fp)
                if mtime >= twelve_hours_ago:
                    all_modified.append((mtime, fp, os.path.getsize(fp)))
            except Exception:
                pass

all_modified.sort(key=lambda x: x[0], reverse=True)
print(f"\nTotal modified files in core codebases (past 12 hours): {len(all_modified)}")

# Cluster into milestone timestamps (e.g. 15-minute windows)
clusters = []
current_cluster = []
for item in all_modified:
    if not current_cluster:
        current_cluster.append(item)
    else:
        # If within 25 minutes of cluster head
        if abs(current_cluster[0][0] - item[0]) < 1500:
            current_cluster.append(item)
        else:
            clusters.append(current_cluster)
            current_cluster = [item]
if current_cluster:
    clusters.append(current_cluster)

print(f"\nIdentified {len(clusters)} Distinct Engineering Work Blocks / Milestone Batches:")
for idx, cl in enumerate(clusters):
    start_t = datetime.datetime.fromtimestamp(min(x[0] for x in cl)).strftime('%H:%M:%S')
    end_t = datetime.datetime.fromtimestamp(max(x[0] for x in cl)).strftime('%H:%M:%S')
    print(f"\n--- Batch {idx+1}: [{start_t} - {end_t}] ({len(cl)} files modified) ---")
    samples = set()
    for mtime, fp, sz in cl:
        rel = os.path.relpath(fp, r"C:\AI-BS")
        samples.add(rel)
    for s in sorted(list(samples))[:10]:
        print(f"  • {s}")
    if len(samples) > 10:
        print(f"  ... and {len(samples)-10} more files")
