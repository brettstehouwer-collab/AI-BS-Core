"""
Steam Gaming Hub & Native Launcher Router
Ecosystem: AI-BS Sovereign Intelligence Matrix
Provides:
- Discovery of installed Steam games across C:, D:, and E: drives from appmanifest_*.acf
- One-click native execution (steam://run/<AppID>) via Windows host shell
- Hardware Game-Mode Governor (pausing heavy Ollama VRAM compute while gaming)
- Live process check for running Steam games
"""

import os
import re
import glob
import json
import logging
import subprocess
import psutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("SteamRouter")
router = APIRouter(prefix="/api/v1/steam", tags=["Steam Gaming Hub"])

STEAM_MANIFEST_PATHS = [
    r"C:\Program Files (x86)\Steam\steamapps",
    r"D:\SteamLibrary\steamapps",
    r"E:\SteamLibrary\steamapps"
]

class GameLaunchRequest(BaseModel):
    appid: str
    game_name: Optional[str] = "Steam Game"
    enable_game_mode: Optional[bool] = True

def parse_steam_manifest(filepath: str) -> Optional[Dict[str, Any]]:
    """Parses Valve ACF manifest key-value file format into structured dictionary."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()

        name_m = re.search(r'"name"\s+"([^"]+)"', txt)
        appid_m = re.search(r'"appid"\s+"([^"]+)"', txt)
        size_m = re.search(r'"SizeOnDisk"\s+"([^"]+)"', txt)
        dir_m = re.search(r'"installdir"\s+"([^"]+)"', txt)
        played_m = re.search(r'"LastPlayed"\s+"([^"]+)"', txt)
        build_m = re.search(r'"buildid"\s+"([^"]+)"', txt)

        if name_m and appid_m:
            appid = appid_m.group(1).strip()
            name = name_m.group(1).replace("®", "").replace("™", "").replace("Ar", "").strip()
            
            # Filter out non-game redistributables
            if "Steamworks" in name or "Common Redistributables" in name:
                return None

            sz = int(size_m.group(1)) if size_m else 0
            size_gb = round(sz / (1024 ** 3), 2)
            installdir = dir_m.group(1) if dir_m else ""
            library_dir = os.path.dirname(filepath)
            full_install_path = os.path.join(library_dir, "common", installdir)

            # High-res banner image URL from Steam CDN
            header_img = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
            capsule_img = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg"

            return {
                "appid": appid,
                "name": name,
                "size_gb": size_gb,
                "installdir": installdir,
                "full_path": full_install_path,
                "last_played": int(played_m.group(1)) if played_m else 0,
                "build_id": build_m.group(1) if build_m else "unknown",
                "library": os.path.splitdrive(filepath)[0],
                "header_image": header_img,
                "capsule_image": capsule_img,
                "manifest_file": filepath
            }
    except Exception as e:
        logger.debug(f"Failed to parse Steam manifest {filepath}: {e}")
    return None

@router.get("/library")
async def get_steam_library():
    """Scans all local storage drives for installed Steam game manifests."""
    games = []
    for library_path in STEAM_MANIFEST_PATHS:
        if not os.path.exists(library_path):
            continue
        for manifest_file in glob.glob(os.path.join(library_path, "appmanifest_*.acf")):
            parsed = parse_steam_manifest(manifest_file)
            if parsed:
                games.append(parsed)

    # Sort games by last played (most recent first)
    games.sort(key=lambda g: g["last_played"], reverse=True)

    # Check which games or processes are currently active
    active_process_names = [p.name().lower() for p in psutil.process_iter(['name']) if p.info.get('name')]
    running_games = []
    
    # Common game executables
    known_exes = {
        "1938090": ["cod.exe", "bootstrapper.exe"],
        "4384550": ["cod.exe", "blackops6.exe"],
        "1240440": ["haloinfinite.exe"],
        "990080": ["hogwartslegacy.exe"],
        "960090": ["bloonstd6.exe"]
    }

    for g in games:
        appid = g["appid"]
        is_running = False
        if appid in known_exes:
            for exe in known_exes[appid]:
                if exe in active_process_names:
                    is_running = True
                    break
        g["is_running"] = is_running
        if is_running:
            running_games.append(g["name"])

    return {
        "status": "success",
        "total_installed": len(games),
        "games": games,
        "running_games": running_games,
        "game_mode_active": len(running_games) > 0
    }

@router.post("/launch")
async def launch_steam_game(req: GameLaunchRequest):
    """Launches a Steam game via native protocol hook steam://run/<AppID> and activates Game-Mode governor."""
    appid = req.appid.strip()
    if not appid.isdigit():
        raise HTTPException(status_code=400, detail="Invalid Steam AppID format")

    try:
        # Native Windows launch via URI handler
        uri = f"steam://run/{appid}"
        subprocess.Popen(f'start "" "{uri}"', shell=True)

        # Trigger Game Mode: unload heavy Ollama models from VRAM to give full 24GB RTX 4090 to game
        if req.enable_game_mode:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=3.0) as client:
                    # Tell Ollama to release loaded models immediately
                    await client.post("http://127.0.0.1:11434/api/generate", json={"model": "stehouwer_llm", "keep_alive": 0})
            except Exception as oe:
                logger.debug(f"Ollama unload ping during game launch: {oe}")

        return {
            "status": "launched",
            "appid": appid,
            "game_name": req.game_name,
            "protocol_uri": uri,
            "game_mode": "ACTIVE (VRAM Yielded for 100% GPU Gaming)"
        }
    except Exception as e:
        logger.error(f"Failed to launch Steam game {appid}: {e}")
        raise HTTPException(status_code=500, detail=f"Launch failed: {str(e)}")
