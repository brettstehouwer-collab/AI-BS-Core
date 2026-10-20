import os
import glob
import py_compile
from collections import defaultdict

docs_dir = r"C:\AI-BS\docs"
all_items = os.listdir(docs_dir)

categories = defaultdict(list)
total_bytes = 0
python_syntax_errors = []

for item in all_items:
    full_path = os.path.join(docs_dir, item)
    if os.path.isdir(full_path):
        categories["Subdirectories"].append((item, 0))
        continue
        
    size = os.path.getsize(full_path)
    total_bytes += size
    ext = os.path.splitext(item)[1].lower()
    
    if ext in [".md", ".txt", ".html"]:
        categories["Markdown, Text & HTML Documents"].append((item, size))
    elif ext in [".pdf"]:
        categories["PDF Documents & Pitch Decks"].append((item, size))
    elif ext in [".wav", ".mp3", ".m4a", ".mp4"]:
        categories["Audio & Video Media Stems"].append((item, size))
    elif ext in [".jpg", ".png", ".jpeg"]:
        categories["Images & Visual Assets"].append((item, size))
    elif ext in [".zip"]:
        categories["Knowledge Archives (ZIP)"].append((item, size))
    elif ext in [".fdx"]:
        categories["Final Draft Screenplays (FDX)"].append((item, size))
    elif ext in [".safetensors", ".pt", ".bin"]:
        categories["AI Model Weights"].append((item, size))
    elif ext in [".py"]:
        categories["Python Scripts in Docs"].append((item, size))
        try:
            py_compile.compile(full_path, doraise=True)
        except Exception as e:
            python_syntax_errors.append((item, str(e)))
    elif ext in [".csv"]:
        categories["CSV Datasets"].append((item, size))
    elif ext in [".exe", ".msi"]:
        categories["Installers & Binaries"].append((item, size))
    else:
        categories["Other"].append((item, size))

print("=" * 70)
print("             AI-BS DOCS & KNOWLEDGE VAULT DEEP AUDIT")
print("=" * 70)
print(f"Total Items in C:\\AI-BS\\docs : {len(all_items)}")
print(f"Total File Size on Disk       : {round(total_bytes / (1024*1024), 2)} MB\n")

for cat, flist in sorted(categories.items()):
    cat_size = sum(s for _, s in flist)
    print(f"[{cat}] ({len(flist)} items, {round(cat_size / (1024*1024), 2)} MB):")
    for fname, size in sorted(flist, key=lambda x: x[0])[:6]:
        print(f"  - {fname:<46} ({round(size/1024, 1)} KB)")
    if len(flist) > 6:
        print(f"  ... and {len(flist) - 6} more")
    print()

print("=" * 70)
print(f"Python Script Syntax Errors : {len(python_syntax_errors)}")
for fname, err in python_syntax_errors:
    print(f"  [!] {fname}: {err}")
if not python_syntax_errors:
    print("  [SUCCESS] All Python scripts in docs/ compile with 0 syntax errors.")
print("=" * 70)