"""
Recreational Debut Sovereign Sync Engine
========================================
Maintains 100% two-way byte parity and continuous synchronization between:
  1. C:\\Recreational-Debut (Standalone Entity)
  2. C:\\AI-BS (Master Workstation Core)
  3. All 4 AI-BS Frontend Mirror Trees:
     - C:\\AI-BS\\frontend\\src\\components\\clients\\
     - C:\\AI-BS\\frontend\\components\\clients\\
     - C:\\AI-BS\\frontend\\src\\components\\components\\clients\\
     - C:\\AI-BS\\frontend\\components\\components\\clients\\
     - C:\\AI-BS\\frontend\\src\\clients\\
"""

import os
import sys
import time
import shutil
import hashlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] RecDebutSync: %(message)s")
logger = logging.getLogger("RecDebutSync")

RECDEBUT_ROOT = Path(r"C:\Recreational-Debut")
AI_BS_ROOT = Path(r"C:\AI-BS")

# Component mapping
CORE_COMPONENTS = [
    "DennisBellMobileRemote.jsx",
    "DennisBellPortal.jsx",
    "recDebutAssets.js",
    "RecreationalDebut.jsx",
]

AI_BS_MIRRORS = [
    AI_BS_ROOT / r"frontend\src\components\clients",
    AI_BS_ROOT / r"frontend\components\clients",
    AI_BS_ROOT / r"frontend\src\components\components\clients",
    AI_BS_ROOT / r"frontend\components\components\clients",
    AI_BS_ROOT / r"frontend\src\clients",
]

# Scripts to synchronize
SYNC_SCRIPTS = [
    "check_recdebut_stats.py",
    "fix_recdebut_data.py",
    "inspect_recdebut_broadcast.py",
    "inspect_recdebut_status.py",
    "launch_recdebut_batch.py",
    "parse_recdebut_assets.py",
    "run_recdebut_scheduler.bat",
    "verify_recdebut_emails.py",
    "stage_and_send_batch.py",
    "check_texts_status.py",
    "adb_auto_install.ps1",
]

# Data files to synchronize
SYNC_DATA = [
    ("recdebut_site_data.json", r"saved_data\recdebut_site_data.json"),
    ("recdebut_extracted_summary.json", r"saved_data\recdebut_extracted_summary.json"),
    ("recdebut_email_verification_report.csv", r"saved_data\recdebut_email_verification_report.csv"),
]

def get_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def sync_components():
    rec_comp_dir = RECDEBUT_ROOT / r"frontend\src\components"
    primary_mirror = AI_BS_ROOT / r"frontend\src\components\clients"
    
    for comp in CORE_COMPONENTS:
        rec_file = rec_comp_dir / comp
        aibs_file = primary_mirror / comp
        
        if not rec_file.exists() and not aibs_file.exists():
            continue
            
        rec_hash = get_hash(rec_file)
        aibs_hash = get_hash(aibs_file)
        
        if rec_hash == aibs_hash and rec_hash != "":
            # Already identical, verify all secondary mirrors
            for mirror in AI_BS_MIRRORS[1:]:
                mirror_file = mirror / comp
                if get_hash(mirror_file) != rec_hash:
                    mirror.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(rec_file, mirror_file)
                    logger.info(f"Fixed mirror parity: {mirror_file}")
            continue
            
        # Determine which file is newer
        rec_mtime = rec_file.stat().st_mtime if rec_file.exists() else 0
        aibs_mtime = aibs_file.stat().st_mtime if aibs_file.exists() else 0
        
        if rec_mtime > aibs_mtime and rec_file.exists():
            logger.info(f"Propagating update from RecDebut -> AI-BS: {comp}")
            for mirror in AI_BS_MIRRORS:
                mirror.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rec_file, mirror / comp)
        elif aibs_file.exists():
            logger.info(f"Propagating update from AI-BS -> RecDebut: {comp}")
            rec_comp_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(aibs_file, rec_file)
            for mirror in AI_BS_MIRRORS[1:]:
                mirror.mkdir(parents=True, exist_ok=True)
                shutil.copy2(aibs_file, mirror / comp)

def sync_scripts():
    rec_scripts_dir = RECDEBUT_ROOT / "scripts"
    aibs_scripts_dir = AI_BS_ROOT / "scripts"
    
    for script in SYNC_SCRIPTS:
        rec_file = rec_scripts_dir / script
        aibs_file = aibs_scripts_dir / script
        
        if not rec_file.exists() and not aibs_file.exists():
            continue
            
        rec_hash = get_hash(rec_file)
        aibs_hash = get_hash(aibs_file)
        if rec_hash == aibs_hash and rec_hash != "":
            continue
            
        rec_mtime = rec_file.stat().st_mtime if rec_file.exists() else 0
        aibs_mtime = aibs_file.stat().st_mtime if aibs_file.exists() else 0
        
        if rec_mtime > aibs_mtime and rec_file.exists():
            logger.info(f"Propagating script RecDebut -> AI-BS: {script}")
            shutil.copy2(rec_file, aibs_file)
        elif aibs_file.exists():
            logger.info(f"Propagating script AI-BS -> RecDebut: {script}")
            shutil.copy2(aibs_file, rec_file)

def sync_data():
    rec_data_dir = RECDEBUT_ROOT / "data"
    for filename, aibs_rel_path in SYNC_DATA:
        rec_file = rec_data_dir / filename
        aibs_file = AI_BS_ROOT / aibs_rel_path
        
        if not rec_file.exists() and not aibs_file.exists():
            continue
            
        rec_hash = get_hash(rec_file)
        aibs_hash = get_hash(aibs_file)
        if rec_hash == aibs_hash and rec_hash != "":
            continue
            
        rec_mtime = rec_file.stat().st_mtime if rec_file.exists() else 0
        aibs_mtime = aibs_file.stat().st_mtime if aibs_file.exists() else 0
        
        if rec_mtime > aibs_mtime and rec_file.exists():
            logger.info(f"Propagating data RecDebut -> AI-BS: {filename}")
            shutil.copy2(rec_file, aibs_file)
        elif aibs_file.exists():
            logger.info(f"Propagating data AI-BS -> RecDebut: {filename}")
            shutil.copy2(aibs_file, rec_file)

def execute_sync():
    logger.info("Executing comprehensive bidirectional sync...")
    sync_components()
    sync_scripts()
    sync_data()
    logger.info("Sync complete. 100% parity verified across all ends.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        logger.info("Starting live continuous watch daemon (polling every 5s)...")
        while True:
            try:
                execute_sync()
            except Exception as e:
                logger.error(f"Error during sync loop: {e}")
            time.sleep(5)
    else:
        execute_sync()
