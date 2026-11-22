#!/usr/bin/env python3
"""
increment_frontend_version.py
Phase 3: Synchronize frontend/package.json SemVer with the repository version.txt.

Usage:
    python increment_frontend_version.py            # sync only — reads version.txt,
                                                    # writes version to package.json
    python increment_frontend_version.py --status   # print current versions, no write
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
VERSION_FILE = ROOT / "version.txt"
PACKAGE_JSON = ROOT / "frontend" / "package.json"


def read_version_txt() -> tuple[int, int, int]:
    """Return (major, minor, patch) from version.txt."""
    raw = VERSION_FILE.read_text(
        encoding="utf-8-sig").strip()  # utf-8-sig strips BOM
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", raw)
    if not m:
        print(f"[ERROR] version.txt has unexpected format: {repr(raw)}")
        sys.exit(1)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def read_package_json() -> dict:
    """Load and return the parsed frontend/package.json."""
    with PACKAGE_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def write_package_json(data: dict) -> None:
    """Write updated data back to frontend/package.json with 2-space indent."""
    with PACKAGE_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # trailing newline


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status", action="store_true",
        help="Print current versions without modifying any file."
    )
    args = parser.parse_args()

    # Read sources of truth
    major, minor, patch = read_version_txt()
    canonical = f"{major}.{minor}.{patch}"

    pkg = read_package_json()
    current_pkg_version = pkg.get("version", "unknown")

    print(f"  version.txt       -> {canonical}")
    print(f"  package.json      -> {current_pkg_version}")

    if args.status:
        if canonical == current_pkg_version:
            print("  [OK] Versions are already in sync.")
        else:
            print("  [MISMATCH] Versions are OUT OF SYNC.")
        return

    # Sync package.json version to match version.txt
    if pkg.get("version") == canonical:
        print("  [OK] Already in sync -- no changes written.")
        return

    pkg["version"] = canonical
    write_package_json(pkg)
    print(
        f"  [OK] frontend/package.json updated: {current_pkg_version} -> {canonical}")


if __name__ == "__main__":
    main()
