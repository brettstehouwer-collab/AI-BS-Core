import os

search_folders = [
    r'C:\Users\footb\Desktop',
    r'C:\Users\footb\Documents',
    r'C:\Users\footb\Downloads',
    r'C:\AI-BS\Documents'
]

pdf_docx = []
for fld in search_folders:
    if not os.path.exists(fld):
        continue
    for root, dirs, files in os.walk(fld):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.venv', '__pycache__', 'Megascans Library', 'dist', 'build', 'vms')]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.pdf', '.docx', '.doc'):
                p = os.path.join(root, f)
                pdf_docx.append(p)

print(f"Total PDF/DOCX files: {len(pdf_docx)}")
for p in pdf_docx:
    print(f"  {p}")
