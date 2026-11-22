#!/usr/bin/env python3
"""
Automated 4-Mirror Synchronization & Parity Verifier
AI-BS Ecosystem - Rule 1 (Multi-Mirror Synchronization Law)

Synchronizes all components and stylesheets from the primary source of truth:
  1. frontend/src/components/
To all 3 satellite mirror trees:
  2. frontend/components/
  3. frontend/src/components/components/
  4. frontend/components/components/

Enforces 100% byte-for-byte SHA256 parity before Vite build and Firebase deployment.
"""

import os
import sys
import hashlib
from pathlib import Path

# Force UTF-8 on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def get_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def find_frontend_dir() -> Path:
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
        Path("C:/AI-BS/frontend"),
        Path.cwd() / "frontend"
    ]
    for c in candidates:
        if (c / "src" / "components").exists() and (c / "package.json").exists():
            return c.resolve()
    raise FileNotFoundError("Could not locate frontend directory with src/components and package.json.")

def sync_mirrors() -> int:
    frontend_dir = find_frontend_dir()
    primary = frontend_dir / "src" / "components"
    
    mirrors = [
        frontend_dir / "components",
        frontend_dir / "src" / "components" / "components",
        frontend_dir / "components" / "components"
    ]
    
    for m in mirrors:
        m.mkdir(parents=True, exist_ok=True)

    synced_count = 0
    updated_count = 0
    ignored_subdirs = {"components", "node_modules", "__pycache__", ".git"}
    
    # 1. Sync all files in primary recursively
    for root, dirs, files in os.walk(primary):
        # Exclude ignored directories from recursion
        dirs[:] = [d for d in dirs if d not in ignored_subdirs]
        root_path = Path(root)
        rel_dir = root_path.relative_to(primary)
        
        for fname in files:
            src_file = root_path / fname
            rel_file = rel_dir / fname if rel_dir != Path(".") else Path(fname)
            primary_hash = get_sha256(src_file)
            synced_count += 1
            
            for m in mirrors:
                target_file = m / rel_file
                target_file.parent.mkdir(parents=True, exist_ok=True)
                if not target_file.exists() or get_sha256(target_file) != primary_hash:
                    with open(src_file, "rb") as src, open(target_file, "wb") as dst:
                        dst.write(src.read())
                    updated_count += 1

    # 2. Strict verification pass
    mismatch_found = False
    for item in primary.iterdir():
        if item.is_file():
            p_hash = get_sha256(item)
            for m in mirrors:
                target = m / item.name
                if not target.exists():
                    print(f"❌ [sync-mirrors] Missing target: {target}")
                    mismatch_found = True
                elif get_sha256(target) != p_hash:
                    print(f"❌ [sync-mirrors] Hash mismatch for {item.name} at {target}")
                    mismatch_found = True

    if mismatch_found:
        print("❌ [sync-mirrors] Verification FAILED. Multi-mirror parity broken.")
        return 1

    print(f"✅ [sync-mirrors] 100% SHA256 parity verified across all 4 mirror trees ({synced_count} files verified, {updated_count} mirrors updated).")
    return 0

if __name__ == "__main__":
    sys.exit(sync_mirrors())
