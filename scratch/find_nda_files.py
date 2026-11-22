import os

search_roots = [
    r"C:\AI-BS\Documents",
    r"C:\AI-BS\saved_data",
    r"C:\Users\footb\Documents",
    r"C:\Users\footb\Desktop",
    r"C:\Users\footb\Downloads"
]

results = []
for r in search_roots:
    if not os.path.exists(r):
        continue
    for root, dirs, files in os.walk(r):
        # skip git, node_modules, venvs
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.venv', '__pycache__', 'Megascans Library')]
        for f in files:
            fl = f.lower()
            if any(k in fl for k in ['nda', 'non-disclosure', 'nondisclosure', 'confidentiality', 'agreement', 'contract']):
                p = os.path.join(root, f)
                results.append((p, os.path.getsize(p)))

print(f"Found {len(results)} candidate files:")
for p, s in results[:30]:
    print(f"  {p} ({s} bytes)")
