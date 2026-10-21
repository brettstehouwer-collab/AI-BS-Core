"""
AI-BS Omni-Sync Sentinel Daemon
================================
Author: Brett Stehouwer / AI-BS Autonomous Intelligence
Continuous background watchdog that guarantees:
  1. 100% SHA-256 byte parity across all 4 AI-BS Frontend Mirror Trees:
       - frontend/src/components
       - frontend/components
       - frontend/src/components/components
       - frontend/components/components
  2. Instant two-way synchronization between AI-BS and Satellite codebases (C:\\Recreational-Debut)
  3. Real-time parity between Backend Routers (AI-BS rec_debut_router.py <-> RecDebut rec_debut_router.py)
  4. Auto-regeneration of Desktop Athlete vCards (.vcf) upon any DB mutation in rec_debut.db
  5. Continuous Cloudflare Tunnel watchdog for stehouwer-publishing.com & recdebut-recruit.org
"""

import os
import sys
import time
import shutil
import hashlib
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

# Windows console encoding fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

AI_BS_ROOT = Path(r"C:\AI-BS")
RECDEBUT_ROOT = Path(r"C:\Recreational-Debut")
DB_PATH = AI_BS_ROOT / r"saved_data\rec_debut.db"
VCARD_SCRIPT = AI_BS_ROOT / r"scripts\generate_athlete_vcards.py"

AI_BS_PRIMARY = AI_BS_ROOT / r"frontend\src\components"
AI_BS_MIRRORS = [
    AI_BS_ROOT / r"frontend\components",
    AI_BS_ROOT / r"frontend\src\components\components",
    AI_BS_ROOT / r"frontend\components\components",
]

SATELLITE_COMPONENTS = [
    "DennisBellPortal.jsx",
    "DennisBellMobileRemote.jsx",
    "CampaignAutomationTab.jsx",
    "RecreationalDebut.jsx",
    "recDebutAssets.js"
]

ROUTER_PAIRS = [
    (
        AI_BS_ROOT / r"backend\routers\rec_debut_router.py",
        RECDEBUT_ROOT / r"backend\rec_debut_router.py"
    )
]

def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [OmniSync] {msg}", flush=True)

def get_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def sync_frontend_mirrors():
    """Syncs from primary frontend/src/components to secondary mirrors."""
    if not AI_BS_PRIMARY.exists():
        return

    ignored = {"components", "node_modules", "__pycache__", ".git"}
    updated = 0

    for root, dirs, files in os.walk(AI_BS_PRIMARY):
        dirs[:] = [d for d in dirs if d not in ignored]
        root_path = Path(root)
        rel_dir = root_path.relative_to(AI_BS_PRIMARY)

        for fname in files:
            src_file = root_path / fname
            rel_file = rel_dir / fname if rel_dir != Path(".") else Path(fname)
            src_hash = get_hash(src_file)
            if not src_hash:
                continue

            for mirror in AI_BS_MIRRORS:
                dst_file = mirror / rel_file
                if not dst_file.exists() or get_hash(dst_file) != src_hash:
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src_file, dst_file)
                        updated += 1
                    except Exception as e:
                        log(f"Error copying {src_file.name} to {dst_file}: {e}")

    if updated > 0:
        log(f"Propagated {updated} mirror file(s) across 4 AI-BS frontend trees.")

def sync_satellite_components():
    """Synchronizes core RecDebut components between AI-BS and C:\\Recreational-Debut."""
    rec_comp_dir = RECDEBUT_ROOT / r"frontend\src\components"
    if not rec_comp_dir.exists():
        return

    for comp in SATELLITE_COMPONENTS:
        aibs_file = AI_BS_PRIMARY / comp
        rec_file = rec_comp_dir / comp

        if not aibs_file.exists() and not rec_file.exists():
            continue

        aibs_hash = get_hash(aibs_file)
        rec_hash = get_hash(rec_file)

        if aibs_hash == rec_hash and aibs_hash != "":
            continue

        aibs_mtime = aibs_file.stat().st_mtime if aibs_file.exists() else 0
        rec_mtime = rec_file.stat().st_mtime if rec_file.exists() else 0

        if rec_mtime > aibs_mtime and rec_file.exists():
            log(f"Updating AI-BS from newer RecDebut satellite: {comp}")
            shutil.copy2(rec_file, aibs_file)
            for m in AI_BS_MIRRORS:
                m_file = m / comp
                m_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rec_file, m_file)
        elif aibs_file.exists():
            log(f"Updating RecDebut satellite from newer AI-BS: {comp}")
            rec_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(aibs_file, rec_file)

def sync_backend_routers():
    """Keeps rec_debut_router.py identical in both AI-BS and Recreational-Debut."""
    for aibs_r, rec_r in ROUTER_PAIRS:
        if not aibs_r.exists() and not rec_r.exists():
            continue

        h1 = get_hash(aibs_r)
        h2 = get_hash(rec_r)

        if h1 == h2 and h1 != "":
            continue

        m1 = aibs_r.stat().st_mtime if aibs_r.exists() else 0
        m2 = rec_r.stat().st_mtime if rec_r.exists() else 0

        if m2 > m1 and rec_r.exists():
            log(f"Syncing router: RecDebut -> AI-BS ({rec_r.name})")
            shutil.copy2(rec_r, aibs_r)
        elif aibs_r.exists():
            log(f"Syncing router: AI-BS -> RecDebut ({aibs_r.name})")
            shutil.copy2(aibs_r, rec_r)

def check_db_and_sync_vcards(last_db_mtime: float) -> float:
    """Checks if rec_debut.db was modified and triggers vcard generation."""
    if not DB_PATH.exists():
        return last_db_mtime

    current_mtime = DB_PATH.stat().st_mtime
    if last_db_mtime != 0 and current_mtime > last_db_mtime:
        log("Detected change in rec_debut.db -> Regenerating athlete vCards & rosters on Desktop...")
        try:
            subprocess.run([sys.executable, str(VCARD_SCRIPT)], check=True, capture_output=True, text=True)
            log("Athlete vCards synchronized successfully on Desktop.")
        except Exception as e:
            log(f"Error regenerating vcards: {e}")

    return current_mtime

def check_cloudflare_tunnels():
    """Checks if Cloudflare tunnel is responding for the public domains."""
    domains = ["https://stehouwer-publishing.com/", "https://recdebut-recruit.org/"]
    for d in domains:
        try:
            req = urllib.request.Request(d, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-BS-Sentinel"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status not in (200, 301, 302):
                    log(f"Warning: {d} returned status {resp.status}")
        except Exception as e:
            log(f"Warning: Cloudflare endpoint {d} check note: {e}")

def run_loop():
    log("Starting AI-BS Omni-Sync Sentinel Daemon (Multi-Mirror, Router, DB, & Cloudflare Watcher)...")
    last_db_mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0
    poll_count = 0

    while True:
        try:
            sync_frontend_mirrors()
            sync_satellite_components()
            sync_backend_routers()
            last_db_mtime = check_db_and_sync_vcards(last_db_mtime)

            poll_count += 1
            # Run cloudflare endpoint check every ~60 seconds (12 ticks of 5s)
            if poll_count % 12 == 0:
                check_cloudflare_tunnels()

        except Exception as e:
            log(f"Unexpected error in watch loop: {e}")

        time.sleep(5)

if __name__ == "__main__":
    run_loop()
