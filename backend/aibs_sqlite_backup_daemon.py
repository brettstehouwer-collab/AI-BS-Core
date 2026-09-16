"""
AI-BS Automated SQLite 24-Hour Non-Blocking VACUUM INTO Backup Daemon
Executes atomic zero-lock database snapshots on a 24-hour cycle with 7-day retention pruning.
"""

import os
import sys
import time
import sqlite3
import shutil
import glob
import json
import argparse
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

WORKSPACE_ROOT = r"C:\AI-BS"
BACKUP_DIR = os.path.join(WORKSPACE_ROOT, "saved_data", "backups")
LOG_PATH = os.path.join(WORKSPACE_ROOT, "logs", "aibs_sqlite_backup_daemon.log")

TARGET_DATABASES = [
    os.path.join(WORKSPACE_ROOT, "backend", "stehouwer_vault.db"),
    os.path.join(WORKSPACE_ROOT, "backend", "lexicon_vault.db"),
    os.path.join(WORKSPACE_ROOT, "leads_store.db"),
    os.path.join(WORKSPACE_ROOT, "data", "leads_store.db"),
    os.path.join(WORKSPACE_ROOT, "data", "trade_queue.db"),
    os.path.join(WORKSPACE_ROOT, "data", "reasoning_traces_pending.db"),
    os.path.join(WORKSPACE_ROOT, "data", "telemetry_checkpoint.sqlite"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "trade_queue.db"),
    os.path.join(WORKSPACE_ROOT, "prestige_powerwash.db")
]

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [SQLITE_BACKUP] {msg}"
    try:
        print(formatted)
    except Exception:
        # Fallback for strict encodings
        print(formatted.encode('ascii', errors='replace').decode('ascii'))
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def backup_single_database(db_path):
    if not os.path.exists(db_path):
        return None

    db_filename = os.path.basename(db_path)
    rel_path = os.path.relpath(db_path, WORKSPACE_ROOT)
    # Replace directory separators with underscores for unique names
    sanitized_prefix = rel_path.replace("\\", "_").replace("/", "_")
    base_name, _ = os.path.splitext(sanitized_prefix)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_backup_name = f"{base_name}_{timestamp_str}.db"
    target_backup_path = os.path.join(BACKUP_DIR, target_backup_name)

    os.makedirs(BACKUP_DIR, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        
        # Passive checkpoint without blocking active writers
        try:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
        except Exception as cp_err:
            log_message(f"Passive WAL checkpoint note on {db_filename}: {cp_err}")

        # Native non-blocking VACUUM INTO
        # Escape single quotes in path if any
        escaped_path = target_backup_path.replace("'", "''")
        conn.execute(f"VACUUM INTO '{escaped_path}';")
        conn.close()

        if os.path.exists(target_backup_path):
            size_kb = os.path.getsize(target_backup_path) / 1024.0
            log_message(f"✅ Successfully backed up {db_filename} -> {target_backup_name} ({size_kb:.2f} KB)")
            return {
                "source": db_path,
                "backup": target_backup_path,
                "size_kb": size_kb,
                "status": "SUCCESS"
            }
        else:
            raise FileNotFoundError(f"Backup file {target_backup_path} was not created.")

    except Exception as e:
        log_message(f"❌ Backup failed for {db_filename}: {e}")
        return {
            "source": db_path,
            "error": str(e),
            "status": "FAILED"
        }

def prune_old_backups(retention_days=7):
    """
    Removes backup files older than retention_days.
    """
    if not os.path.exists(BACKUP_DIR):
        return 0

    cutoff_time = time.time() - (retention_days * 86400)
    pruned_count = 0

    for file_path in glob.glob(os.path.join(BACKUP_DIR, "*.db")):
        try:
            mtime = os.path.getmtime(file_path)
            if mtime < cutoff_time:
                os.remove(file_path)
                pruned_count += 1
                log_message(f"Pruned expired backup: {os.path.basename(file_path)}")
        except Exception as err:
            log_message(f"Error pruning {file_path}: {err}")

    return pruned_count

def run_full_backup_cycle(retention_days=7):
    log_message("Starting full 24-hour non-blocking SQLite snapshot cycle across all 9 databases...")
    results = []
    
    for db_path in TARGET_DATABASES:
        res = backup_single_database(db_path)
        if res:
            results.append(res)

    pruned = prune_old_backups(retention_days)
    log_message(f"Snapshot cycle finished. Backed up {len(results)} databases. Pruned {pruned} old files.")
    return results

def get_backup_summary():
    if not os.path.exists(BACKUP_DIR):
        return {"total_backups": 0, "files": []}

    files = []
    total_bytes = 0
    for f in glob.glob(os.path.join(BACKUP_DIR, "*.db")):
        size = os.path.getsize(f)
        total_bytes += size
        files.append({
            "filename": os.path.basename(f),
            "size_kb": round(size / 1024.0, 2),
            "created_at": datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
        })

    files.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "total_backups": len(files),
        "total_size_mb": round(total_bytes / (1024.0 * 1024.0), 2),
        "files": files[:20]
    }

def main():
    parser = argparse.ArgumentParser(description="AI-BS 24h SQLite Backup Daemon")
    parser.add_argument("--run-once", action="store_true", help="Execute single backup cycle and exit")
    parser.add_argument("--status", action="store_true", help="Show summary of existing database snapshots")
    parser.add_argument("--interval-hours", type=float, default=24.0, help="Backup loop interval in hours (default: 24.0)")
    parser.add_argument("--retention-days", type=int, default=7, help="Snapshot retention period in days (default: 7)")
    args = parser.parse_args()

    if args.status:
        summary = get_backup_summary()
        print(json.dumps(summary, indent=2))
        return

    if args.run_once:
        results = run_full_backup_cycle(args.retention_days)
        print(json.dumps(results, indent=2))
        return

    log_message(f"Starting continuous daemon loop (interval: {args.interval_hours}h, retention: {args.retention_days}d)...")
    while True:
        try:
            run_full_backup_cycle(args.retention_days)
        except Exception as loop_err:
            log_message(f"Unexpected error in backup loop: {loop_err}")

        sleep_seconds = int(args.interval_hours * 3600)
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main()
