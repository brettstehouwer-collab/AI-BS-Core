import os

DRIVE_DIR = r"C:\AI-BS\shared_cloud_drive"

print("=" * 75)
print("             AI-BS SHARED CLOUD DRIVE AUDIT")
print("=" * 75)

if not os.path.exists(DRIVE_DIR):
    print("shared_cloud_drive does not exist.")
    exit(0)

folders = os.listdir(DRIVE_DIR)
total_files = 0
total_bytes = 0

for f in sorted(folders):
    fpath = os.path.join(DRIVE_DIR, f)
    if os.path.isdir(fpath):
        subfiles = []
        for root, dirs, files in os.walk(fpath):
            for file in files:
                p = os.path.join(root, file)
                sz = os.path.getsize(p)
                subfiles.append((file, sz, os.path.relpath(p, fpath)))
        
        folder_bytes = sum(s[1] for s in subfiles)
        total_files += len(subfiles)
        total_bytes += folder_bytes
        print(f"\n[DIR: {f}] - {len(subfiles)} files ({folder_bytes / (1024*1024):.2f} MB)")
        for fname, sz, rel in subfiles[:8]:
            print(f"   * {fname} ({sz / 1024:.1f} KB)")
        if len(subfiles) > 8:
            print(f"   ... and {len(subfiles) - 8} more files")

print("\n" + "=" * 75)
print(f"Total Shared Cloud Drive Files : {total_files}")
print(f"Total Shared Cloud Drive Size  : {total_bytes / (1024*1024):.2f} MB")
print("=" * 75)