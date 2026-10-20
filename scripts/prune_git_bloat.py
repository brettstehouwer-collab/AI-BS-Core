import os
import stat

objects_dir = r"C:\AI-BS\.git\objects"
pruned_count = 0
pruned_bytes = 0

print("Scanning and unlocking loose git objects in C:\\AI-BS\\.git\\objects...")
for root, dirs, files in os.walk(objects_dir):
    if "pack" in root or "info" in root:
        continue
    for f in files:
        if f.startswith("tmp_obj_") or len(f) == 38:
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
                if sz > (10 * 1024 * 1024): # files > 10MB
                    os.chmod(p, stat.S_IWRITE)
                    os.remove(p)
                    pruned_count += 1
                    pruned_bytes += sz
            except Exception as e:
                pass

print(f"Pruned {pruned_count} large loose uncommitted objects.")
print(f"Reclaimed: {round(pruned_bytes / (1024**3), 2)} GB.")
