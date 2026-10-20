import os
import pefile
import re

fl_path = r'c:\AI-BS\docs\flstudio_win64_26.1.5.5618.exe'

print(f"=== Deep Inspector: {os.path.basename(fl_path)} ===")
size_bytes = os.path.getsize(fl_path)
print(f"File Size: {size_bytes / (1024*1024):.2f} MB ({size_bytes:,} bytes)")

with open(fl_path, 'rb') as f:
    # Read first 15 MB
    start_chunk = f.read(15 * 1024 * 1024)
    # Read last 15 MB
    f.seek(-15 * 1024 * 1024, 2)
    end_chunk = f.read(15 * 1024 * 1024)

combined = start_chunk + end_chunk

patterns = {
    'NSIS (Nullsoft Scriptable Install System)': [b'NullsoftInst', b'Nullsoft.NSIS', b'NSIS.Library'],
    'Inno Setup': [b'Inno Setup Setup Data', b'InnoSetup', b'Inno Setup'],
    'InstallShield': [b'InstallShield', b'ISSetup'],
    'Advanced Installer': [b'Caphyon', b'Advanced Installer'],
    'WiX Burn / Bootstrapper': [b'WixBurn', b'Windows Installer'],
    'Wise Installer': [b'WiseMain', b'Wise Installation System'],
    '7-Zip SFX': [b'7z\xbc\xaf\x27\x1c']
}

detected = []
for name, sigs in patterns.items():
    for s in sigs:
        if s in combined:
            detected.append(name)
            break

print("Detected Installer Engine(s):", detected)

# Look for embedded strings, driver references, component names
keywords = [
    r'FL Studio', r'FL Studio ASIO', r'ASIO4ALL', r'Image-Line',
    r'Plugin Manager', r'Shared', r'Fruity', r'Flesh', r'Sytrus',
    r'Harmor', r'Soundfont', r'DirectWave', r'VST', r'VST3', r'CLAP',
    r'asio', r'driver', r'registry', r'Uninstall', r'Components'
]

print("\n=== Component & Feature String Extraction ===")
matches_found = set()
for kw in keywords:
    reg = re.compile(kw.encode('ascii', errors='ignore'), re.IGNORECASE)
    res = reg.findall(combined)
    if res:
        matches_found.add(kw)
        print(f"  Found Reference: {kw} (occurrences: {len(res)})")

# Search for NSIS specific section headers or component definitions
nsis_sections = re.findall(b'Section\s*["\']([^"\']+)["\']', combined)
if nsis_sections:
    print(f"\nDiscovered {len(nsis_sections)} NSIS Component Sections:")
    for sec in set(nsis_sections[:25]):
        print("  - Section:", sec.decode('ascii', errors='ignore'))

# Check PE Version Info
try:
    pe = pefile.PE(fl_path)
    if hasattr(pe, 'FileInfo'):
        print("\n=== PE Version Info ===")
        for entry in pe.FileInfo:
            for st in entry:
                if hasattr(st, 'StringTable'):
                    for st_entry in st.StringTable:
                        for k, v in st_entry.entries.items():
                            print(f"  {k.decode()}: {v.decode()}")
except Exception as e:
    print(f"PE parse error: {e}")
