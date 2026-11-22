import threading
import time
import os
import sys
sys.path.append(r"C:\AI-BS\native_studio")
from xbox_tier5_ftp_engine import XboxFTPEngine

# Test local staging path creation
staging_dirs = [r"C:\XboxStaging\ROMs", r"C:\XboxStaging\Media", r"C:\XboxStaging\Textures"]
all_ok = all(os.path.exists(d) for d in staging_dirs)
print(f"Staging Environment verified: {all_ok}")
for d in staging_dirs:
    print(f"  * {d}")
