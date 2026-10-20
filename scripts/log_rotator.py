"""
log_rotator.py - Autonomous AI-BS Log Rotation Utility
Prevents disk I/O thrashing by enforcing a strict 50MB ceiling on all .log and .err files.
Rotates oversized logs to an archive directory.
"""
import os
import glob
from pathlib import Path
import time
import shutil

MAX_LOG_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_AGE_SECONDS = 48 * 3600             # 48 Hours

def rotate_logs(max_age_hours: float = 48.0, max_size_mb: float = 50.0):
    base_dir = Path(r"C:\AI-BS")
    logs_dir = base_dir / "logs"
    archive_dir = logs_dir / "archive"
    
    if not logs_dir.exists():
        print("[Log Rotator] Logs directory does not exist. Skipping.")
        return
        
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    now = time.time()
    max_age_sec = max_age_hours * 3600
    max_size_bytes = max_size_mb * 1024 * 1024
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    files_rotated = 0
    files_archived = 0
    bytes_reclaimed = 0
    
    for log_file in logs_dir.glob("*.*"):
        if log_file.is_file() and log_file.suffix in [".log", ".err", ".jsonl"]:
            try:
                st = log_file.stat()
                size = st.st_size
                mtime = st.st_mtime
                age_sec = now - mtime
                
                # Check 1: Inactive / Stale Log (> 48 hours old)
                if age_sec > max_age_sec:
                    archived_path = archive_dir / f"{log_file.stem}_{timestamp}{log_file.suffix}"
                    shutil.move(str(log_file), str(archived_path))
                    files_archived += 1
                    bytes_reclaimed += size
                    print(f"  [ARCHIVED STALE] {log_file.name} (Age: {age_sec / 3600:.1f}h, Size: {size / 1024:.1f} KB)")
                    continue
                
                # Check 2: Oversized Log (> 50 MB)
                if size > max_size_bytes:
                    archived_path = archive_dir / f"{log_file.stem}_{timestamp}{log_file.suffix}"
                    shutil.move(str(log_file), str(archived_path))
                    files_rotated += 1
                    bytes_reclaimed += size
                    print(f"  [ROTATED OVERSIZED] {log_file.name} ({size / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"  [ERROR] Could not process {log_file.name}: {e}")
                    
    total = files_rotated + files_archived
    if total > 0:
        print(f"[Log Rotator] Complete. Archived {files_archived} stale logs, Rotated {files_rotated} oversized logs. Reclaimed {bytes_reclaimed / 1024 / 1024:.2f} MB.")
    else:
        print("[Log Rotator] All active logs are fresh (<48h) and within optimal size bounds.")

if __name__ == "__main__":
    rotate_logs()
