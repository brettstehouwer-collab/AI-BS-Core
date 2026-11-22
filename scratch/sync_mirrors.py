import shutil
import hashlib
import os

src = r'C:\AI-BS\frontend\src\components\OperationsAuditHubTab.jsx'
mirrors = [
    r'C:\AI-BS\frontend\components\OperationsAuditHubTab.jsx',
    r'C:\AI-BS\frontend\src\components\components\OperationsAuditHubTab.jsx',
    r'C:\AI-BS\frontend\components\components\OperationsAuditHubTab.jsx'
]

for m in mirrors:
    os.makedirs(os.path.dirname(m), exist_ok=True)
    shutil.copy2(src, m)
    print(f"Copied to: {m}")

all_paths = [src] + mirrors
print("\nSHA-256 Mirror Hash Parity:")
for p in all_paths:
    with open(p, 'rb') as f:
        h = hashlib.sha256(f.read()).hexdigest()
    print(f"{p} -> {h}")
