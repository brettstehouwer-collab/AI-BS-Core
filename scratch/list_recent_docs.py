import os
import glob
from datetime import datetime

paths = [
    r'C:\Users\footb\Desktop',
    r'C:\Users\footb\Downloads',
    r'C:\Users\footb\Documents',
    r'C:\AI-BS\Documents',
    r'C:\AI-BS\saved_data',
    r'C:\AI-BS\shared_cloud_drive'
]

docs = []
for base in paths:
    if not os.path.exists(base):
        continue
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.venv', '__pycache__', 'Megascans Library')]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.pdf', '.docx', '.doc', '.txt', '.rtf', '.md', '.html'):
                full = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(full)
                    size = os.path.getsize(full)
                    docs.append((mtime, full, size))
                except Exception:
                    pass

docs.sort(key=lambda x: x[0], reverse=True)
print(f"Total documents found: {len(docs)}")
print("\nTop 40 most recently modified documents:")
for mtime, full, size in docs[:40]:
    dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{dt} | {size:>10} bytes | {full}")
