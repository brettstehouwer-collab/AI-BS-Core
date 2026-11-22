import re
import os

app_jsx_path = r'C:\AI-BS\frontend\App.jsx'
frontend_dir = os.path.dirname(app_jsx_path)

with open(app_jsx_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all import('./path')
imports = re.findall(r"import\(['\"](.*?)['\"]\)", content)

print("Checking imports...")
missing = []
for imp in imports:
    if imp.startswith('./'):
        rel_path = imp[2:]
    else:
        rel_path = imp
        
    full_path = os.path.join(frontend_dir, os.path.normpath(rel_path))
    
    # Check if exact file exists
    if os.path.exists(full_path):
        continue
        
    # Check extensions
    found = False
    for ext in ['.jsx', '.js', '.tsx', '/index.jsx', '/index.js']:
        if os.path.exists(full_path + ext):
            found = True
            break
            
    if not found:
        missing.append(imp)
        print(f"[MISSING] {imp} (Resolved: {full_path})")

if not missing:
    print("All imported components exist!")
else:
    print(f"Total missing: {len(missing)}")
