import os
import subprocess
import sys
from pathlib import Path

NATIVE_DIR = Path(r"C:\AI-BS\native_studio")
os.chdir(NATIVE_DIR)
python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

print("==================================================")
print("PHASE 1: Building AI_BS_Studio.exe (Native Core Engine)")
print("==================================================")
cmd_app = [python_exe, "-m", "PyInstaller", "AI_BS_Studio.spec", "--noconfirm"]
p1 = subprocess.run(cmd_app, capture_output=True, text=True)
if p1.returncode != 0:
    print("Build App Error:\n", p1.stderr[-2000:])
    sys.exit(1)
print("AI_BS_Studio.exe build succeeded!")

print("\n==================================================")
print("PHASE 2: Building AI_BS_Studio_Setup.exe (Elevated Installer)")
print("==================================================")
cmd_installer = [python_exe, "-m", "PyInstaller", "AI_BS_Studio_Setup.spec", "--noconfirm"]
p2 = subprocess.run(cmd_installer, capture_output=True, text=True)
if p2.returncode != 0:
    print("Build Setup Error:\n", p2.stderr[-2000:])
    sys.exit(1)
print("AI_BS_Studio_Setup.exe build succeeded!")

# Verify sizes
app_exe = NATIVE_DIR / "dist" / "AI_BS_Studio" / "AI_BS_Studio.exe"
setup_exe = NATIVE_DIR / "dist" / "AI_BS_Studio_Setup.exe"

if app_exe.exists():
    print(f"\n[VERIFIED] Core App Exe: {app_exe} ({app_exe.stat().st_size / (1024*1024):.2f} MB)")
if setup_exe.exists():
    print(f"[VERIFIED] Setup Wizard Exe: {setup_exe} ({setup_exe.stat().st_size / (1024*1024):.2f} MB)")
print("All binaries built successfully!")
