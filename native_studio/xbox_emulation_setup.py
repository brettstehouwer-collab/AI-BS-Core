import os
import sys
import json
import urllib.request
import time

STAGING_ROOT = r"C:\XboxStaging"
ROMS_DIR = os.path.join(STAGING_ROOT, "ROMs")
PACKAGES_DIR = os.path.join(STAGING_ROOT, "Packages")

SYSTEMS = [
    ("PS2", ".iso, .bin, .chd (PCSX2 Core)"),
    ("GameCube", ".iso, .ciso, .rvz (Dolphin Core)"),
    ("Wii", ".iso, .wbfs, .rvz (Dolphin Core)"),
    ("N64", ".z64, .n64, .v64 (Mupen64Plus Core)"),
    ("Dreamcast", ".cdi, .gdi, .chd (Flycast Core)"),
    ("PS1", ".chd, .bin/.cue, .pbp (Beetle PSX Core)"),
    ("GBA", ".gba (mGBA Core)"),
    ("SNES", ".sfc, .smc (Snes9x Core)")
]

def init_rom_structure():
    print("=" * 75)
    print(" [*] INITIALIZING RETROARCH ROM VAULT DIRECTORIES")
    print(f" [*] Location: {ROMS_DIR}")
    print("=" * 75)
    
    os.makedirs(ROMS_DIR, exist_ok=True)
    os.makedirs(PACKAGES_DIR, exist_ok=True)

    for sys_name, formats in SYSTEMS:
        sys_path = os.path.join(ROMS_DIR, sys_name)
        os.makedirs(sys_path, exist_ok=True)
        readme_file = os.path.join(sys_path, "format_info.txt")
        if not os.path.exists(readme_file):
            with open(readme_file, "w") as f:
                f.write(f"Drop your {sys_name} games here.\nSupported formats: {formats}\n")
        print(f"  [+] {sys_name:<12} -> {sys_path} ({formats})")

    print("\n[+] All emulation vaults created and ready for games.")

def get_retroarch_download_links():
    print("\n" + "=" * 75)
    print(" [*] RETROARCH UWP OFFICIAL PACKAGE SOURCES (Xbox One)")
    print("=" * 75)
    print("Official Libretro Buildbot direct downloads:")
    print("  1. RetroArch UWP (Stable):")
    print("     https://buildbot.libretro.com/stable/1.19.1/windows/msix/RetroArch.msixbundle")
    print("  2. Visual C++ Runtime Dependency (VCLibs x64):")
    print("     https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx")
    print("\nTarget folder for downloaded packages:")
    print(f"  {PACKAGES_DIR}")
    print("=" * 75)

def main():
    init_rom_structure()
    get_retroarch_download_links()

if __name__ == "__main__":
    main()
