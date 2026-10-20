import os

folders = [
    r"C:\Program Files\AI-BS Sovereign Studio",
    r"C:\Program Files\AI-BS Matrix",
    r"C:\Program Files\BS-Studio",
]

def get_dir_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except:
                pass
    return total

for f in folders:
    if os.path.exists(f):
        size_mb = get_dir_size(f) / (1024 * 1024)
        print(f"{f}: {size_mb:.2f} MB")
    else:
        print(f"{f}: NOT FOUND")
