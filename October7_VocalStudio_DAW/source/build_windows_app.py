"""Build the native Windows Studio from its canonical PyInstaller recipe.

Session audio and recordings are user inputs, not application dependencies.
Signing and installation are separate release steps; this helper performs neither.
"""

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
NATIVE_NAME = "October7_VocalStudio_Native"


def build():
    spec_path = BASE_DIR / (NATIVE_NAME + ".spec")
    entrypoint = BASE_DIR / "app_native.py"
    for required in (spec_path, entrypoint, BASE_DIR / "native_version_info.txt"):
        if not required.is_file():
            print("[!] Required native build input is missing:", required)
            return False

    dist_dir = BASE_DIR / "dist"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--distpath", str(dist_dir),
        "--workpath", str(BASE_DIR / "build"),
        str(spec_path),
    ]
    print("[*] Building native October 7 Vocal Studio:", spec_path)
    ret = subprocess.run(cmd, cwd=str(BASE_DIR))
    if ret.returncode != 0:
        print("[!] PyInstaller compilation failed with code:", ret.returncode)
        return False

    output_exe = dist_dir / NATIVE_NAME / (NATIVE_NAME + ".exe")
    if not output_exe.is_file():
        print("[!] Executable not found at expected path:", output_exe)
        return False

    print("[OK] Native application built:", output_exe)
    print("[*] Session media is not bundled. Signing and installation remain separate.")
    return True


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
