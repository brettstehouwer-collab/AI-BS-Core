import os
import sys
import json
import logging
import hashlib
import asyncio
import subprocess
import aiohttp
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("AI_BS_Updater")

router = APIRouter(prefix="/api/v1/updater", tags=["App-Level Downloader/Updater"])

CURRENT_VERSION = "5.215.0"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_MANIFEST_PATH = os.path.join(BASE_DIR, "frontend", "public", "updates", "version.json")
LOCAL_PAYLOAD_PATH = os.path.join(BASE_DIR, "frontend", "public", "updates", "aibs_update_payload.zip")
REMOTE_MANIFEST_URL = "https://ai-bs-dashboard.web.app/updates/version.json"

download_state = {
    "status": "idle", # idle | downloading | downloaded | error
    "progress_percent": 0.0,
    "downloaded_bytes": 0,
    "total_bytes": 0,
    "error": None,
    "payload_path": None
}

def parse_semver(v: str):
    try:
        clean = v.strip().lstrip("v")
        return [int(x) for x in clean.split(".")[:3]]
    except Exception:
        return [0, 0, 0]

def is_newer(remote_v: str, current_v: str) -> bool:
    r = parse_semver(remote_v)
    c = parse_semver(current_v)
    return r > c

def locate_updater_stub() -> Optional[str]:
    candidates = [
        os.path.join(BASE_DIR, "frontend", "desktop-build", "win-unpacked", "aibs_updater.exe"),
        os.path.join(BASE_DIR, "frontend", "desktop-build", "win-unpacked", "resources", "updater", "aibs_updater.exe"),
        os.path.join(BASE_DIR, "go-core", "aibs_updater.exe"),
        os.path.join(BASE_DIR, "tools", "aibs_updater.exe"),
        os.path.join(BASE_DIR, "installer", "aibs_updater.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

@router.get("/status")
def get_updater_status() -> Dict[str, Any]:
    updater_bin = locate_updater_stub()
    return {
        "status": "online",
        "current_version": CURRENT_VERSION,
        "updater_stub_available": updater_bin is not None,
        "updater_stub_path": updater_bin,
        "base_directory": BASE_DIR,
        "download_state": download_state
    }

@router.get("/check")
async def check_for_updates() -> Dict[str, Any]:
    manifest_data = None

    # 1. Try remote cloud manifest
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(REMOTE_MANIFEST_URL) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    manifest_data = json.loads(text.lstrip('\ufeff'))
    except Exception as e:
        logger.warning(f"Remote manifest check failed: {e}. Falling back to local manifest.")

    # 2. Fallback to local manifest file if remote offline or during local testing
    if not manifest_data and os.path.exists(LOCAL_MANIFEST_PATH):
        try:
            with open(LOCAL_MANIFEST_PATH, "r", encoding="utf-8-sig") as f:
                manifest_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed reading local manifest: {e}")

    if not manifest_data:
        return {
            "update_available": False,
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "message": "No update manifest could be retrieved."
        }

    latest_version = manifest_data.get("version", CURRENT_VERSION)
    update_available = is_newer(latest_version, CURRENT_VERSION)

    return {
        "update_available": update_available,
        "current_version": CURRENT_VERSION,
        "latest_version": latest_version,
        "release_date": manifest_data.get("releaseDate"),
        "release_notes": manifest_data.get("releaseNotes", ""),
        "download_url": manifest_data.get("downloadUrl"),
        "fallback_url": manifest_data.get("fallbackUrl"),
        "sha256": manifest_data.get("sha256", ""),
        "size_bytes": manifest_data.get("sizeBytes", 0),
        "files": manifest_data.get("files", [])
    }

async def _perform_download(url: str, expected_sha256: str = ""):
    global download_state
    temp_dir = os.path.join(os.getenv("TEMP", "C:\\Temp"), "aibs_update")
    os.makedirs(temp_dir, exist_ok=True)
    dest_path = os.path.join(temp_dir, "aibs_update_payload.zip")

    download_state["status"] = "downloading"
    download_state["progress_percent"] = 0.0
    download_state["downloaded_bytes"] = 0
    download_state["error"] = None
    download_state["payload_path"] = dest_path

    # If local fallback file requested or remote fails, check if local file can be copied directly
    if not url.startswith("http") and os.path.exists(url):
        import shutil
        shutil.copyfile(url, dest_path)
        download_state["status"] = "downloaded"
        download_state["progress_percent"] = 100.0
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    # Fallback to local server payload if cloud download url fails
                    if os.path.exists(LOCAL_PAYLOAD_PATH):
                        import shutil
                        shutil.copyfile(LOCAL_PAYLOAD_PATH, dest_path)
                        download_state["status"] = "downloaded"
                        download_state["progress_percent"] = 100.0
                        return
                    raise RuntimeError(f"HTTP download failed with status: {resp.status}")

                total = int(resp.headers.get("content-length", 0))
                download_state["total_bytes"] = total
                downloaded = 0

                hasher = hashlib.sha256()
                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 64):
                        f.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        download_state["downloaded_bytes"] = downloaded
                        if total > 0:
                            download_state["progress_percent"] = round((downloaded / total) * 100, 1)

                actual_sha = hasher.hexdigest().lower()
                if expected_sha256 and actual_sha != expected_sha256.lower():
                    logger.warning(f"SHA256 mismatch! Expected: {expected_sha256}, Got: {actual_sha}")

        download_state["status"] = "downloaded"
        download_state["progress_percent"] = 100.0
        logger.info(f"Update payload downloaded successfully to {dest_path}")
    except Exception as e:
        download_state["status"] = "error"
        download_state["error"] = str(e)
        logger.error(f"Download error: {e}")

class DownloadRequest(BaseModel):
    url: Optional[str] = None
    sha256: Optional[str] = None

@router.post("/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    check_res = await check_for_updates()
    target_url = req.url or check_res.get("download_url") or check_res.get("fallback_url")
    if not target_url:
        raise HTTPException(status_code=400, detail="No valid download URL provided or found.")

    background_tasks.add_task(_perform_download, target_url, req.sha256 or check_res.get("sha256", ""))
    return {"status": "started", "target_url": target_url}

@router.get("/download-progress")
def get_download_progress():
    return download_state

@router.post("/apply")
def apply_update():
    updater_bin = locate_updater_stub()
    if not updater_bin:
        raise HTTPException(status_code=500, detail="Updater stub executable (aibs_updater.exe) not found.")

    payload_path = download_state.get("payload_path")
    if not payload_path or not os.path.exists(payload_path):
        # Check if local payload exists as fallback
        if os.path.exists(LOCAL_PAYLOAD_PATH):
            payload_path = LOCAL_PAYLOAD_PATH
        else:
            raise HTTPException(status_code=400, detail="No downloaded payload zip available to apply.")

    target_dir = os.path.join(BASE_DIR, "frontend", "desktop-build", "win-unpacked")
    if not os.path.exists(target_dir):
        target_dir = BASE_DIR

    # Copy updater stub to temp directory so it can overwrite files in target_dir without self-lock
    temp_updater = os.path.join(os.getenv("TEMP", "C:\\Temp"), "aibs_update", "aibs_updater.exe")
    os.makedirs(os.path.dirname(temp_updater), exist_ok=True)
    import shutil
    shutil.copyfile(updater_bin, temp_updater)

    current_pid = os.getpid()
    cmd = [
        temp_updater,
        f"-target-dir={target_dir}",
        f"-payload-zip={payload_path}",
        f"-parent-pid={current_pid}",
        "-executable=AI-BS Sovereign Studio.exe"
    ]

    logger.info(f"Spawning updater stub: {' '.join(cmd)}")

    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(cmd, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, close_fds=True)

    return {
        "status": "applying",
        "message": "Updater stub launched. Main application terminating for in-place patch replacement.",
        "target_dir": target_dir
    }

@router.get("/payload")
def serve_local_payload():
    if os.path.exists(LOCAL_PAYLOAD_PATH):
        return FileResponse(LOCAL_PAYLOAD_PATH, media_type="application/zip", filename="aibs_update_payload.zip")
    raise HTTPException(status_code=404, detail="Local update payload archive not found.")
