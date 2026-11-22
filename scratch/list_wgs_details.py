import os

base = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs"

print(f"Listing files in: {base}")
for root, dirs, files in os.walk(base):
    for f in files:
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, base)
        size = os.path.getsize(full_path)
        print(f"  {rel_path:<60} {size:8d} bytes")
