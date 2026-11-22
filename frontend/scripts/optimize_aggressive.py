#!/usr/bin/env python3
"""
Aggressive Electron Build Optimizer v2
Removes non-critical graphics, validation, and optional DLLs
Preserves core functionality (rendering, audio, input)
Target reduction: Additional 50-100 MB without breaking functionality
"""

import os
from pathlib import Path

def optimize_aggressive():
    """Remove non-essential Electron/Chromium files."""
    
    build_path = Path("build-output/win-unpacked")
    if not build_path.exists():
        print("ERROR: build-output/win-unpacked not found")
        return False
    
    total_removed = 0
    
    # FILES TO REMOVE (Safe deletions - no functional impact)
    removable_files = {
        'debug.log': 'Debug log file',
        'LICENSE.electron.txt': 'License file (9 lines, optional)',
        'snapshot_blob.bin': 'Duplicate JS snapshot (also in app.asar)',
    }
    
    print("[PHASE 1] Removing non-essential files")
    for filename, reason in removable_files.items():
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            filepath.unlink()
            total_removed += size
            print(f"  [OK] {filename} ({size/1024/1024:.2f} MB) - {reason}")
    
    # GRAPHICS OPTIMIZATION
    # These can be safely removed if GPU acceleration not critical
    optional_graphics = {
        'vk_swiftshader.dll': 'Software graphics fallback (SwiftShader)',
        'vk_swiftshader_icd.json': 'SwiftShader config',
        'vulkan-1.dll': 'Vulkan API (fallback to D3D)',
        'libGLESv2.dll': 'GLES library (D3D primary)',
    }
    
    print("\n[PHASE 2] Optional graphics libraries (keep if GPU fallback needed)")
    for filename, reason in optional_graphics.items():
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  [OPTIONAL] {filename} ({size/1024/1024:.2f} MB) - {reason}")
            # Commented out - user must choose
            # filepath.unlink()
            # total_removed += size
    
    # CODEC OPTIMIZATION
    codec_files = {
        'ffmpeg.dll': 'Video codec library (2.56 MB)',
        'd3dcompiler_47.dll': 'DirectX compiler (4.69 MB)',
    }
    
    print("\n[PHASE 3] Codec & compilation libraries")
    for filename, reason in codec_files.items():
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  [OPTIONAL] {filename} ({size/1024/1024:.2f} MB) - {reason}")
            # These can be removed if no video playback needed
            # filepath.unlink()
            # total_removed += size
    
    # RESOURCE DATA OPTIMIZATION
    pak_files = {
        'chrome_200_percent.pak': 'High-DPI assets (200% scale)',
        'resources.pak': 'Chromium UI resources (CRITICAL - keep)',
    }
    
    print("\n[PHASE 4] Resource pak files")
    for filename, reason in pak_files.items():
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            status = "[KEEP]" if filename == 'resources.pak' else "[OPTIONAL]"
            print(f"  {status} {filename} ({size/1024/1024:.2f} MB) - {reason}")
            
            if filename == 'chrome_200_percent.pak':
                # Safe to remove if only 1x/100% DPI displays
                # filepath.unlink()
                # total_removed += size
                pass
    
    # SNAPSHOT FILES
    snapshot_files = {
        'v8_context_snapshot.bin': 'V8 JS engine snapshot (0.63 MB)',
        'icudtl.dat': 'Unicode data (CRITICAL - needed for text)',
    }
    
    print("\n[PHASE 5] JS engine snapshots")
    for filename, reason in snapshot_files.items():
        filepath = build_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            status = "[KEEP]" if filename == 'icudtl.dat' else "[OPTIONAL]"
            print(f"  {status} {filename} ({size/1024/1024:.2f} MB) - {reason}")
    
    # LOCALES (Already pruned, but verify)
    locales_path = build_path / "locales"
    if locales_path.exists():
        locale_count = len(list(locales_path.glob('*.pak')))
        locale_size = sum(f.stat().st_size for f in locales_path.glob('*.pak'))
        print(f"\n[PHASE 6] Locales: {locale_count} files ({locale_size/1024/1024:.1f} MB)")
        print(f"  [KEPT] Already optimized in previous pass")
    
    # SUMMARY
    print(f"\n{'='*70}")
    print(f"SAFE REMOVALS APPLIED: {total_removed/1024/1024:.1f} MB")
    print(f"{'='*70}")
    print("\nOPTIONAL REMOVALS (disabled, uncomment to apply):")
    print("  • vk_swiftshader.dll + .json (5.2 MB) - Keep if GPU fallback needed")
    print("  • vulkan-1.dll (0.92 MB) - Keep for stability")
    print("  • libGLESv2.dll (7.69 MB) - Keep for D3D fallback")
    print("  • ffmpeg.dll (2.56 MB) - Remove only if no video playback")
    print("  • d3dcompiler_47.dll (4.69 MB) - Remove only if not using D3D12")
    print("  • chrome_200_percent.pak (0.22 MB) - Remove if only 1080p displays")
    print("\nRECOMMENDATION:")
    print("  Keep graphics DLLs (GPU fallback is critical for stability)")
    print("  Remove ffmpeg.dll if video playback not in UI")
    print("  Keep d3dcompiler (minimal impact, better compatibility)")
    print("\n" + "="*70)
    
    return True

if __name__ == '__main__':
    optimize_aggressive()
