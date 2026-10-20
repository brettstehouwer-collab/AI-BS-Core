import os
import shutil

src = r"c:\AI-BS\frontend\src\components\clients\DennisBellMobileRemote.jsx"

destinations = [
    r"c:\AI-BS\frontend\components\clients\DennisBellMobileRemote.jsx",
    r"c:\AI-BS\frontend\src\components\components\clients\DennisBellMobileRemote.jsx",
    r"c:\AI-BS\frontend\components\components\clients\DennisBellMobileRemote.jsx",
    r"c:\AI-BS\frontend\src\clients\DennisBellMobileRemote.jsx"
]

for dst in destinations:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Synced: {dst}")

print("All mirrors updated successfully with byte parity.")
