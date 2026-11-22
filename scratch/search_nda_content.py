import os

search_folders = [
    r'C:\Users\footb\Desktop',
    r'C:\Users\footb\Documents',
    r'C:\Users\footb\Downloads',
    r'C:\AI-BS\Documents'
]

hits = []
for fld in search_folders:
    if not os.path.exists(fld):
        continue
    for root, dirs, files in os.walk(fld):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.venv', '__pycache__', 'Megascans Library', 'dist', 'build')]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.txt', '.md', '.html', '.json'):
                p = os.path.join(root, f)
                try:
                    if os.path.getsize(p) < 5 * 1024 * 1024:
                        with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                            txt = fp.read().lower()
                            if 'non-disclosure agreement' in txt or 'confidentiality agreement' in txt or 'mutual nda' in txt:
                                hits.append(p)
                except Exception:
                    pass

print(f"Text matches found: {len(hits)}")
for h in hits:
    print(f"  {h}")
