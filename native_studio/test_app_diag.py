import sys
from pathlib import Path
sys.path.insert(0, r"C:\AI-BS")
sys.path.insert(0, r"C:\AI-BS\native_studio")

import traceback
try:
    import app as a
    print("Direct app imported cleanly")
    import native_studio.app as na
    print("native_studio.app imported cleanly")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
print("Diagnostic test passed!")
