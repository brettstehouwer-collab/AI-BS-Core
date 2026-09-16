import os

from shell_adapter import run_assembled_command

src_path = r"E:\Cymatics - DESTINY - Production Suite"
dst_path = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sample_Packs\Cymatics - DESTINY - Production Suite"

if not os.path.exists(dst_path):
    res = run_assembled_command("cmd", "/c", "mklink", "/J", dst_path, src_path)
    print("Junction Creation Output:", res.stdout)
else:
    print("Junction already exists.")

total_files = 0
total_bytes = 0
for root, dirs, files in os.walk(src_path):
    total_files += len(files)
    for f in files:
        total_bytes += os.path.getsize(os.path.join(root, f))

print(f"DESTINY Production Suite: {total_files} audio files/stems | {round(total_bytes/(1024**3), 2)} GB")
