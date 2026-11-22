import hashlib
import os
import shutil

src = r'C:\AI-BS\frontend\src\components\clients\DennisBellPortal.jsx'
mirrors = [
    r'C:\AI-BS\frontend\components\clients\DennisBellPortal.jsx',
    r'C:\AI-BS\frontend\src\components\components\clients\DennisBellPortal.jsx',
    r'C:\AI-BS\frontend\components\components\clients\DennisBellPortal.jsx',
]

with open(src, 'rb') as f:
    src_bytes = f.read()
src_hash = hashlib.sha256(src_bytes).hexdigest()
print(f'SRC: {src_hash} ({len(src_bytes)} bytes)')

for m in mirrors:
    os.makedirs(os.path.dirname(m), exist_ok=True)
    with open(m, 'wb') as f:
        f.write(src_bytes)
    m_hash = hashlib.sha256(open(m, 'rb').read()).hexdigest()
    print(f'MIRROR {m}: {m_hash} (Match: {src_hash == m_hash})')
