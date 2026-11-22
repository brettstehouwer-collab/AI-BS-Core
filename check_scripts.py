import urllib.request
import urllib.parse
import json
import math
from pathlib import Path

res = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/screenwriting/projects').read())
projects = res.get('projects', [])

print(f"{'PROJECT NAME':45} | {'CHARS':8} | {'LINES':6} | {'EST PAGES'}")
print("-" * 75)

for proj in projects:
    try:
        url = 'http://127.0.0.1:8000/api/screenwriting/read?project_name=' + urllib.parse.quote(proj)
        data = json.loads(urllib.request.urlopen(url).read())
        content = data.get('content', '')
        lines = len(content.split('\n'))
        
        # Calculate pages based on Fountain parsing
        est_pages = max(1, math.ceil(lines / 54))
        print(f"{proj:45} | {len(content):8} | {lines:6} | {est_pages:3} pages")
    except Exception as e:
        print(f"{proj:45} | ERROR: {e}")

print("\n--- DISK SEARCH FOR FOUNTAIN & FDX SCRIPTS ---")
root = Path("C:/AI-BS/screenplay_projects")
if root.exists():
    for f in root.glob("**/*"):
        if f.suffix in ['.fountain', '.fdx'] and f.is_file():
            size = f.stat().st_size
            try:
                txt = f.read_text(encoding='utf-8', errors='ignore')
                lc = len(txt.split('\n'))
                print(f"{str(f):70} | {size:8} bytes | {lc:5} lines | ~{max(1, math.ceil(lc/54))} pgs")
            except Exception as e:
                print(f"{str(f):70} | {size:8} bytes")
