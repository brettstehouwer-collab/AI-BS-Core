"""Reference-source installer entry point; delegate to the repaired package installer."""
from pathlib import Path
import runpy

_ROOT_INSTALLER = Path(__file__).resolve().parents[1] / "setup_installer.py"

if __name__ == "__main__":
    if not _ROOT_INSTALLER.is_file():
        raise SystemExit("The repaired root installer is missing. No installation was attempted.")
    runpy.run_path(str(_ROOT_INSTALLER), run_name="__main__")
