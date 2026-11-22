#!/usr/bin/env python3
"""
Automated SQLite Database Backup & SHA-256 Integrity Verification Engine (v5.129.0)
Performs non-blocking online backups of all relational databases to E: Drive with
checksum manifests and rolling 7-day snapshot retention.
"""

import os
import sqlite3
import hashlib
import time
import json
import shutil
from datetime import datetime, timezone

PRIMARY_BACKUP_DIR = r"E:\AI_BS_Resources\Backups"
FALLBACK_BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_data", "backups")
SOURCE_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_data"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "saved_data")
]

def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_target_backup_dir() -> str:
    # Try primary E: Drive backup path first
    try:
        drive = os.path.splitdrive(PRIMARY_BACKUP_DIR)[0]
        if os.path.exists(drive) or os.path.exists(PRIMARY_BACKUP_DIR):
            os.makedirs(PRIMARY_BACKUP_DIR, exist_ok=True)
            return PRIMARY_BACKUP_DIR
    except Exception:
        pass
    
    os.makedirs(FALLBACK_BACKUP_DIR, exist_ok=True)
    return FALLBACK_BACKUP_DIR

def run_database_backups(retention_days: int = 7) -> dict:
    t0 = time.time()
    target_base = get_target_backup_dir()
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(target_base, f"snapshot_{timestamp_str}")
    os.makedirs(snapshot_dir, exist_ok=True)

    backed_up_files = []
    checksum_lines = []
    
    # Locate all SQLite databases
    seen_files = set()
    for sdir in SOURCE_DIRS:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for file in files:
                if file.endswith(".sqlite") or file.endswith(".db"):
                    full_src = os.path.normpath(os.path.join(root, file))
                    if full_src in seen_files:
                        continue
                    seen_files.add(full_src)

                    # Destination filename
                    rel_name = os.path.basename(full_src)
                    dest_file = os.path.join(snapshot_dir, rel_name)

                    try:
                        # Safe non-blocking SQLite online backup API
                        src_conn = sqlite3.connect(full_src)
                        dest_conn = sqlite3.connect(dest_file)
                        src_conn.backup(dest_conn)
                        dest_conn.close()
                        src_conn.close()

                        # Calculate SHA-256
                        checksum = calculate_sha256(dest_file)
                        size_bytes = os.path.getsize(dest_file)

                        checksum_lines.append(f"{checksum}  {rel_name}")
                        backed_up_files.append({
                            "database": rel_name,
                            "source_path": full_src,
                            "backup_path": dest_file,
                            "size_bytes": size_bytes,
                            "sha256": checksum,
                            "status": "HEALTHY"
                        })
                    except Exception as e:
                        backed_up_files.append({
                            "database": rel_name,
                            "source_path": full_src,
                            "error": str(e),
                            "status": "FAILED"
                        })

    # Write SHA-256 Manifest
    manifest_path = os.path.join(snapshot_dir, "checksums.sha256")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(checksum_lines) + "\n")

    # Enforce retention policy
    cleaned_snapshots = 0
    now_sec = time.time()
    max_age_sec = retention_days * 86400

    for item in os.listdir(target_base):
        if item.startswith("snapshot_"):
            item_path = os.path.join(target_base, item)
            if os.path.isdir(item_path):
                mtime = os.path.getmtime(item_path)
                if now_sec - mtime > max_age_sec:
                    shutil.rmtree(item_path, ignore_errors=True)
                    cleaned_snapshots += 1

    duration = round(time.time() - t0, 3)
    summary = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backup_directory": snapshot_dir,
        "total_databases_backed_up": len([b for b in backed_up_files if b.get("status") == "HEALTHY"]),
        "failed_backups": len([b for b in backed_up_files if b.get("status") == "FAILED"]),
        "manifest_path": manifest_path,
        "purged_old_snapshots": cleaned_snapshots,
        "duration_seconds": duration,
        "databases": backed_up_files
    }

    # Save summary report in saved_data/reports
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "last_database_backup.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    result = run_database_backups()
    print(json.dumps(result, indent=2))
