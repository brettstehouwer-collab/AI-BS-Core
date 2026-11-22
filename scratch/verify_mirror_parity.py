import hashlib
import os

files = ['ChatTab.jsx', 'TopNavbar.jsx', 'Sidebar.jsx']
mirrors = [
    r'C:\AI-BS\frontend\src\components',
    r'C:\AI-BS\frontend\components',
    r'C:\AI-BS\frontend\src\components\components',
    r'C:\AI-BS\frontend\components\components'
]

for f in files:
    print(f"=== {f} ===")
    hashes = set()
    for m in mirrors:
        p = os.path.join(m, f)
        if os.path.exists(p):
            with open(p, 'rb') as fp:
                h = hashlib.sha256(fp.read()).hexdigest()
                hashes.add(h)
                print(f"  {m}: {h}")
        else:
            print(f"  {m}: MISSING")
    if len(hashes) == 1:
        print("  -> 100% MATCH across all mirrors!")
    else:
        print("  -> MISMATCH DETECTED!")
