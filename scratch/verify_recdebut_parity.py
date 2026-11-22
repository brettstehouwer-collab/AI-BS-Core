import hashlib
import os

files_to_check = [
    (
        "DennisBellPortal.jsx",
        [
            r"C:\AI-BS\frontend\src\components\clients\DennisBellPortal.jsx",
            r"C:\AI-BS\frontend\components\clients\DennisBellPortal.jsx",
            r"C:\AI-BS\frontend\src\components\components\clients\DennisBellPortal.jsx",
            r"C:\AI-BS\frontend\components\components\clients\DennisBellPortal.jsx",
            r"C:\AI-BS\frontend\src\clients\DennisBellPortal.jsx"
        ]
    ),
    (
        "RecreationalDebut.jsx",
        [
            r"C:\AI-BS\frontend\src\components\clients\RecreationalDebut.jsx",
            r"C:\AI-BS\frontend\components\clients\RecreationalDebut.jsx",
            r"C:\AI-BS\frontend\src\components\components\clients\RecreationalDebut.jsx",
            r"C:\AI-BS\frontend\components\components\clients\RecreationalDebut.jsx",
            r"C:\AI-BS\frontend\src\clients\RecreationalDebut.jsx"
        ]
    )
]

for name, paths in files_to_check:
    print(f"=== Checking {name} ===")
    src = paths[0]
    if not os.path.exists(src):
        print(f"Source missing: {src}")
        continue
    src_bytes = open(src, "rb").read()
    src_hash = hashlib.sha256(src_bytes).hexdigest()
    print(f"SRC: {src_hash} ({len(src_bytes)} bytes)")
    for p in paths[1:]:
        if not os.path.exists(p):
            print(f"MISSING: {p} -> copying from src")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(src_bytes)
        p_bytes = open(p, "rb").read()
        p_hash = hashlib.sha256(p_bytes).hexdigest()
        match = (p_hash == src_hash)
        if not match:
            print(f"MISMATCH: {p} -> overwriting with src")
            with open(p, "wb") as f:
                f.write(src_bytes)
            p_hash = hashlib.sha256(open(p, "rb").read()).hexdigest()
        print(f"  {p}: {p_hash} (Match: {p_hash == src_hash})")
