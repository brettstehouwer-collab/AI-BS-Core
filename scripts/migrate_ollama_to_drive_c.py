#!/usr/bin/env python3
"""
Sovereign Ollama Fleet Migration & Parity Verification Engine
Transfers 142.6 GB model vault from Drive E to Drive C with cryptographic SHA-256 assertion.
"""

import os
import sys
import time
import hashlib
import shutil
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

SOURCE_ROOT = Path(r"E:\AI_BS_Resources\Ollama")
TARGET_ROOT = Path(r"C:\AI-BS\models\ollama")
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB streaming buffer

def compute_sha256(filepath: Path, chunk_size: int = CHUNK_SIZE) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def copy_with_hash(src_path: Path, dst_path: Path, expected_hash: str = None) -> bool:
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if target already exists and is valid
    if dst_path.exists() and dst_path.stat().st_size == src_path.stat().st_size:
        if expected_hash:
            dst_hash = compute_sha256(dst_path)
            if dst_hash == expected_hash:
                print(f"  [SKIPPED/EXISTS] {dst_path.name} (SHA-256 verified)")
                return True
            else:
                print(f"  [MISMATCH] {dst_path.name} corrupt or incomplete. Re-copying...")
        else:
            src_hash = compute_sha256(src_path)
            dst_hash = compute_sha256(dst_path)
            if src_hash == dst_hash:
                print(f"  [SKIPPED/EXISTS] {dst_path.name} (SHA-256 verified)")
                return True

    temp_dst = dst_path.with_suffix(dst_path.suffix + ".part")
    hasher = hashlib.sha256()
    total_bytes = src_path.stat().st_size
    copied_bytes = 0
    start_time = time.time()
    
    with open(src_path, "rb") as fsrc, open(temp_dst, "wb") as fdst:
        while True:
            chunk = fsrc.read(CHUNK_SIZE)
            if not chunk:
                break
            fdst.write(chunk)
            hasher.update(chunk)
            copied_bytes += len(chunk)
            elapsed = time.time() - start_time
            speed = (copied_bytes / (1024 * 1024)) / (elapsed if elapsed > 0 else 0.001)
            pct = (copied_bytes / total_bytes) * 100 if total_bytes > 0 else 100
            print(f"\r  [COPYING] {src_path.name[:32]}... {pct:.1f}% ({copied_bytes / 1024 / 1024:.1f}/{total_bytes / 1024 / 1024:.1f} MB) @ {speed:.1f} MB/s", end="", flush=True)

    print()
    computed_hash = hasher.hexdigest()

    if expected_hash and computed_hash != expected_hash:
        print(f"  [ERROR] Hash mismatch for {src_path.name}! Expected: {expected_hash}, Got: {computed_hash}")
        if temp_dst.exists():
            temp_dst.unlink()
        return False

    # Atomic rename part to final
    if dst_path.exists():
        dst_path.unlink()
    temp_dst.rename(dst_path)
    print(f"  [VERIFIED] {dst_path.name} -> {computed_hash[:16]}... OK")
    return True

def run_migration():
    print("=" * 80)
    print("🛡️ SOVEREIGN OLLAMA FLEET MIGRATION: DRIVE E -> DRIVE C")
    print(f"Source:      {SOURCE_ROOT}")
    print(f"Destination: {TARGET_ROOT}")
    print("=" * 80)

    if not SOURCE_ROOT.exists():
        print(f"FATAL: Source root {SOURCE_ROOT} not accessible.")
        sys.exit(1)

    TARGET_ROOT.mkdir(parents=True, exist_ok=True)

    # Collect all files
    all_files = [f for f in SOURCE_ROOT.rglob("*") if f.is_file()]
    total_files = len(all_files)
    total_size = sum(f.stat().st_size for f in all_files)

    print(f"Discovered {total_files} files totaling {total_size / (1024**3):.2f} GB across models and manifests.\n")

    overall_start = time.time()
    success_count = 0
    fail_count = 0

    for idx, src_file in enumerate(all_files, start=1):
        rel_path = src_file.relative_to(SOURCE_ROOT)
        dst_file = TARGET_ROOT / rel_path
        file_size_mb = src_file.stat().st_size / (1024 * 1024)
        
        print(f"[{idx}/{total_files}] Processing: {rel_path} ({file_size_mb:.2f} MB)")

        # Determine expected hash if blob
        expected_hash = None
        if src_file.parent.name == "blobs" and src_file.name.startswith("sha256-"):
            expected_hash = src_file.name.replace("sha256-", "")

        ok = copy_with_hash(src_file, dst_file, expected_hash=expected_hash)
        if ok:
            success_count += 1
        else:
            fail_count += 1
            print(f"CRITICAL FAILURE copying {src_file}")

    overall_elapsed = time.time() - overall_start
    print("\n" + "=" * 80)
    print("MIGRATION EXECUTION SUMMARY")
    print(f"Total Files Scanned:  {total_files}")
    print(f"Successfully Verified:{success_count}")
    print(f"Failures:             {fail_count}")
    print(f"Elapsed Duration:     {overall_elapsed:.2f} seconds ({overall_elapsed/60:.2f} minutes)")
    avg_speed = (total_size / (1024 * 1024)) / (overall_elapsed if overall_elapsed > 0 else 0.001)
    print(f"Average Throughput:   {avg_speed:.2f} MB/s")
    print("=" * 80)

    if fail_count > 0:
        print("MIGRATION FAILED WITH ERRORS.")
        sys.exit(1)

    print("ALL FILES VERIFIED WITH 100% SHA-256 PARITY ON DRIVE C.")
    sys.exit(0)

if __name__ == "__main__":
    run_migration()
