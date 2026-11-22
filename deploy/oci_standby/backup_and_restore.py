"""Consistent SQLite Backup & Passive-Only Restore Verifier for AI-BS HA (OPS-03).

Uses sqlite3.Connection.backup() rather than raw file copy so WAL transactions stay
consistent, records SHA-256 digests, and verifies any restored database opens in
strict PASSIVE mode with zero automatic live activation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

_REPO_SCRATCH = Path(__file__).resolve().parents[2] / "scratch"
if str(_REPO_SCRATCH) not in sys.path:
    sys.path.insert(0, str(_REPO_SCRATCH))

from ha_execution_gateway import AuthorityStore, verify_backup_passive


def perform_backup(db_path: Path, backup_dir: Path) -> dict[str, object]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"aibs_authority_{ts}.db"
    store = AuthorityStore(db_path)
    try:
        info = store.create_consistent_backup(dest)
    finally:
        store.close()
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_db": str(db_path),
        **info,
    }
    manifest_path = dest.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest_path": str(manifest_path), **manifest}


def verify_restore_in_dir(backup_path: Path, restore_dir: Path, expected_sha256: str | None = None) -> dict[str, object]:
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    actual_sha = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    if expected_sha256 and actual_sha != expected_sha256:
        raise RuntimeError(f"Backup SHA-256 mismatch: expected {expected_sha256}, got {actual_sha}")

    restore_dir.mkdir(parents=True, exist_ok=True)
    restored_db = restore_dir / "restored_authority.db"
    shutil.copy2(backup_path, restored_db)
    summary = verify_backup_passive(restored_db)
    if not summary.get("auto_live_disabled"):
        raise RuntimeError(f"Restored database did not enforce passive startup: {summary}")
    return {
        "restored_db": str(restored_db),
        "sha256": actual_sha,
        "sha256_verified": bool(not expected_sha256 or actual_sha == expected_sha256),
        **summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI-BS Consistent Backup & Passive Restore Verifier")
    parser.add_argument("--db", default="/var/lib/aibs-gateway/authority_journal.db", help="Source AuthorityStore SQLite DB")
    parser.add_argument("--backup-dir", default="/var/backups/aibs", help="Backup destination directory")
    parser.add_argument("--verify-restore", default="", help="Path to backup DB to restore into --dest-dir")
    parser.add_argument("--dest-dir", default="", help="Disposable temp directory for isolated restore verification")
    parser.add_argument("--expected-sha256", default="", help="Optional SHA-256 checksum to verify before restore")
    args = parser.parse_args(argv)

    if args.verify_restore:
        if not args.dest_dir:
            print("Error: --dest-dir is required with --verify-restore", file=sys.stderr)
            return 2
        res = verify_restore_in_dir(
            Path(args.verify_restore),
            Path(args.dest_dir),
            expected_sha256=args.expected_sha256 or None,
        )
        print(json.dumps(res, indent=2))
        return 0

    res = perform_backup(Path(args.db), Path(args.backup_dir))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
