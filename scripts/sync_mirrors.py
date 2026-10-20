#!/usr/bin/env python3
"""
Automated 4-Mirror Synchronization & Parity Verifier
AI-BS Ecosystem - Rule 1 (Multi-Mirror Synchronization Law)
Root scripts proxy calling frontend/scripts/sync_mirrors.py
"""

import sys
from pathlib import Path

# Add frontend/scripts to path and execute sync_mirrors
frontend_scripts = Path(__file__).resolve().parent.parent / "frontend" / "scripts"
sys.path.insert(0, str(frontend_scripts))

try:
    from sync_mirrors import sync_mirrors
    sys.exit(sync_mirrors())
except ImportError:
    # Direct fallback if imported differently
    import subprocess
    script = frontend_scripts / "sync_mirrors.py"
    res = subprocess.run([sys.executable, str(script)])
    sys.exit(res.returncode)
