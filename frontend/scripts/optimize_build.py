#!/usr/bin/env python3
"""
Electron Build Optimizer
Removes unused locales while preserving app functionality.
Run AFTER building: npm run build && python optimize_build.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

def optimize_electron_build():
    """Remove unused locales and unnecessary files from Electron build."""
    
    build_path = Path("build-output/win-unpacked")
    if not build_path.exists():
        print("ERROR: build-output/win-unpacked not found. Run 'npm run package:dry' first.")
        return False
    
    locales_path = build_path / "locales"
    resources_path = build_path / "resources"
    
    # Keep only English and essential locales (add others if needed)
    keep_locales = {
        'en-US.pak',
        'en-GB.pak',
        'es.pak',
        'fr.pak',
        'de.pak',
        'it.pak',
        'pt-BR.pak',
        'zh-CN.pak',
        'ja.pak',
        'ko.pak'
    }
    
    # Remove unused locales
    removed_size = 0
    if locales_path.exists():
        for locale_file in locales_path.glob('*.pak'):
            if locale_file.name not in keep_locales:
                size = locale_file.stat().st_size
                locale_file.unlink()
                removed_size += size
                print(f"  [OK] Removed locale: {locale_file.name} ({size/1024/1024:.1f} MB)")
    
    # Remove unnecessary Chromium files
    unnecessary_files = [
        'LICENSES.chromium.html',  # 9 MB - license file
        'chrome_100_percent.pak',   # Redundant high-DPI assets
    ]
    
    for filename in unnecessary_files:
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            filepath.unlink()
            removed_size += size
            print(f"  [OK] Removed: {filename} ({size/1024/1024:.1f} MB)")
    
    # Calculate final size
    total_size = sum(f.stat().st_size for f in build_path.rglob('*') if f.is_file())
    
    print(f"\n[SUCCESS] Optimization complete!")
    print(f"   Removed: {removed_size/1024/1024:.1f} MB")
    print(f"   Build size now: {total_size/1024/1024:.1f} MB")
    print(f"   Reduction: ~{removed_size/1024/1024/(total_size/1024/1024)*100:.1f}%")
    
    return True

if __name__ == '__main__':
    optimize_electron_build()
