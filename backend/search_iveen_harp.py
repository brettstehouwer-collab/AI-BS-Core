import os
import re

# Search E:\ drive and local sample paths for harp files or text files mentioning Iveen
search_dirs = [r"E:\\", r"C:\AI-BS\shared_cloud_drive\4 media"]

harp_files = []
iveen_mentions = []

for sdir in search_dirs:
    if not os.path.exists(sdir):
        continue
    for root, dirs, files in os.walk(sdir):
        for f in files:
            f_lower = f.lower()
            if "harp" in f_lower:
                harp_files.append(os.path.join(root, f))
            if "iveen" in f_lower or f_lower.endswith('.pdf') or f_lower.endswith('.txt'):
                try:
                    p = os.path.join(root, f)
                    if f_lower.endswith('.txt') or f_lower.endswith('.pdf'):
                        with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                            content = fh.read()
                            if "harp" in content.lower() and "iveen" in content.lower():
                                iveen_mentions.append((p, f))
                except:
                    pass

print(f"Total harp files found on disk: {len(harp_files)}")
print("\nSample of Harp Files across Suites:")
suites = set()
for h in harp_files:
    # get parent suite folder
    parts = h.split(os.sep)
    if len(parts) > 2:
        suites.add(parts[1] if parts[0] == 'E:' else parts[2])

for s in sorted(suites):
    print("  Suite:", s)

print(f"\nDirect Iveen + Harp mentions: {len(iveen_mentions)}")
for m in iveen_mentions:
    print(" ", m)
