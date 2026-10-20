import os
import time

def find_recent_large_files(root_dir, min_size_mb=100, hours=4):
    cutoff = time.time() - (hours * 3600)
    matches = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip system or restricted paths to avoid hang
        if any(skip in root.lower() for skip in ['$recycle.bin', 'system volume information', 'windows']):
            continue
        for f in files:
            try:
                p = os.path.join(root, f)
                st = os.stat(p)
                if st.st_size >= (min_size_mb * 1024 * 1024) and st.st_mtime >= cutoff:
                    matches.append((p, round(st.st_size / (1024*1024), 2), time.ctime(st.st_mtime)))
            except Exception:
                pass
    return matches

print("Scanning C:\\ for files > 100MB modified in last 4 hours...")
results = find_recent_large_files("C:\\Users\\footb", min_size_mb=50, hours=4)
results += find_recent_large_files("C:\\AI-BS", min_size_mb=50, hours=4)
results.sort(key=lambda x: x[1], reverse=True)

for p, sz, t in results[:30]:
    print(f"[{sz} MB] {t} -> {p}")
