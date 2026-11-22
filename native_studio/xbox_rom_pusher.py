"""
AI-BS XBOX EMULATION ASSET & ROM PUSHER (TIER 5 WIRE-SPEED ENGINE)
==================================================================
Direct Gigabit wire-speed synchronization between PC Staging and Xbox One.
Targets RetroArch's isolated UWP sandbox storage (/LocalState/ROMs & /LocalState/system).
"""

import os
import sys
import time
import json
import urllib.parse
from typing import Dict, List, Optional, Tuple
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RETROARCH_PKG = "1e4cf179-f3c2-404f-b9f3-cb2070a5aad8_1.19.1.0_x64__8ngdn9a6dx1ma"
STAGING_DIR = r"C:\XboxStaging"
ROMS_DIR = os.path.join(STAGING_DIR, "ROMs")
BIOS_DIR = os.path.join(STAGING_DIR, "BIOS")
AUTH_FILE = os.path.join(os.path.dirname(__file__), "xbox_wdp_auth.json")

SYSTEM_SUBDIRS = [
    "PS2", "GameCube", "Wii", "N64", "Dreamcast", 
    "PS1", "GBA", "SNES", "Genesis", "Arcade", "NDS", "PSP"
]

class XboxRomPusher:
    def __init__(self, host: str = "192.168.10.2", port: int = 11443):
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}"
        self.session = requests.Session()
        self.session.verify = False
        self._load_auth()

    def _load_auth(self):
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, "r") as f:
                cfg = json.load(f)
                self.session.auth = (cfg.get("username", ""), cfg.get("password", ""))

    def get_csrf(self) -> str:
        try:
            self.session.get(f"{self.base_url}/api/os/info", timeout=3)
            for cookie in self.session.cookies:
                if cookie.name == "CSRF-Token":
                    return cookie.value
        except Exception:
            pass
        return ""

    def ensure_directory(self, parent_path: str, new_folder: str) -> bool:
        """Creates a directory in RetroArch LocalAppData if it doesn't already exist."""
        csrf = self.get_csrf()
        params = {
            "knownfolderid": "LocalAppData",
            "newfoldername": new_folder,
            "packagefullname": RETROARCH_PKG,
            "path": parent_path
        }
        url = f"{self.base_url}/api/filesystem/apps/folder?" + urllib.parse.urlencode(params)
        headers = {"X-CSRF-Token": csrf} if csrf else {}
        r = self.session.post(url, headers=headers, timeout=5)
        return r.status_code in (200, 409)  # 200 Created, 409 already exists

    def list_files(self, path: str) -> List[Dict[str, any]]:
        """Lists files and folders inside a given RetroArch LocalAppData path."""
        params = {
            "knownfolderid": "LocalAppData",
            "packagefullname": RETROARCH_PKG,
            "path": path
        }
        url = f"{self.base_url}/api/filesystem/apps/files?" + urllib.parse.urlencode(params)
        try:
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                return r.json().get("Items", [])
        except Exception:
            pass
        return []

    def upload_file(self, local_path: str, remote_path: str, show_progress: bool = True) -> bool:
        """Uploads a local file (ROM, ISO, BIOS) into the Xbox UWP filesystem."""
        if not os.path.exists(local_path):
            print(f"[-] File not found: {local_path}")
            return False

        filename = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)
        size_mb = file_size / (1024 * 1024)

        csrf = self.get_csrf()
        params = {
            "knownfolderid": "LocalAppData",
            "packagefullname": RETROARCH_PKG,
            "path": remote_path,
            "filename": filename
        }
        url = f"{self.base_url}/api/filesystem/apps/file?" + urllib.parse.urlencode(params)
        headers = {"X-CSRF-Token": csrf} if csrf else {}

        if show_progress:
            print(f"[*] Pushing: {filename} ({size_mb:.2f} MB) -> {remote_path}...", end="", flush=True)

        start_time = time.time()
        try:
            with open(local_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                r = self.session.post(url, files=files, headers=headers, timeout=600)

            elapsed = max(time.time() - start_time, 0.001)
            speed = size_mb / elapsed

            if r.status_code == 200:
                if show_progress:
                    print(f" [OK] in {elapsed:.2f}s (~{speed:.2f} MB/s)")
                return True
            else:
                print(f" [FAILED] HTTP {r.status_code}: {r.text}")
                return False
        except Exception as e:
            print(f" [ERROR] {e}")
            return False

    def init_console_structure(self):
        """Initializes the standard emulation directory hierarchy on the Xbox."""
        print("[*] Initializing Xbox Emulation Directory Tree...")
        self.ensure_directory(r"\LocalState", "ROMs")
        for sub in SYSTEM_SUBDIRS:
            self.ensure_directory(r"\LocalState\ROMs", sub)
        print(" [+] Emulation tree ready: /LocalState/ROMs/[PS2, GameCube, Wii, N64, Dreamcast, PS1, GBA, SNES...]")

    def sync_all(self):
        """Pushes all staged ROMs and BIOS files to the Xbox."""
        self.init_console_structure()
        total_pushed = 0

        # 1. Sync BIOS files
        if os.path.exists(BIOS_DIR):
            bios_files = [f for f in os.listdir(BIOS_DIR) if os.path.isfile(os.path.join(BIOS_DIR, f))]
            if bios_files:
                print(f"\n[*] Syncing {len(bios_files)} BIOS files -> /LocalState/system/...")
                for bf in bios_files:
                    full_p = os.path.join(BIOS_DIR, bf)
                    if self.upload_file(full_p, r"\LocalState\system"):
                        total_pushed += 1

        # 2. Sync ROMs per system
        if os.path.exists(ROMS_DIR):
            for sub in os.listdir(ROMS_DIR):
                sub_path = os.path.join(ROMS_DIR, sub)
                if os.path.isdir(sub_path):
                    games = [f for f in os.listdir(sub_path) if os.path.isfile(os.path.join(sub_path, f))]
                    if games:
                        remote_dest = f"\\LocalState\\ROMs\\{sub}"
                        print(f"\n[*] Syncing {len(games)} files for [{sub}] -> {remote_dest}...")
                        for game in games:
                            full_game = os.path.join(sub_path, game)
                            if self.upload_file(full_game, remote_dest):
                                total_pushed += 1

        print(f"\n" + "=" * 60)
        print(f" [+] Sync Completed: {total_pushed} files pushed to Xbox One at wire speed.")
        print("=" * 60)

    def watch(self, interval_sec: int = 2):
        """Live folder watcher: auto-pushes newly added files in real-time."""
        self.init_console_structure()
        print(f"\n[*] Live Wire-Speed Watcher Active on {STAGING_DIR}...")
        print("    Drop ROMs or ISOs into C:\\XboxStaging\\ROMs\\<System>\\ to push instantly!")
        print("    Press Ctrl+C to stop.\n")

        known_files = set()
        for root, _, files in os.walk(STAGING_DIR):
            for f in files:
                known_files.add(os.path.join(root, f))

        try:
            while True:
                time.sleep(interval_sec)
                current_files = set()
                for root, _, files in os.walk(STAGING_DIR):
                    for f in files:
                        current_files.add(os.path.join(root, f))

                new_files = current_files - known_files
                for nf in new_files:
                    rel = os.path.relpath(nf, STAGING_DIR)
                    parts = rel.split(os.sep)
                    if parts[0].lower() == "bios":
                        self.upload_file(nf, r"\LocalState\system")
                    elif parts[0].lower() == "roms" and len(parts) > 1:
                        sys_name = parts[1]
                        self.upload_file(nf, f"\\LocalState\\ROMs\\{sys_name}")
                    else:
                        self.upload_file(nf, r"\LocalState\downloads")
                    known_files.add(nf)
        except KeyboardInterrupt:
            print("\n[*] Watcher terminated.")

def main():
    pusher = XboxRomPusher()
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "init":
            pusher.init_console_structure()
        elif cmd == "sync":
            pusher.sync_all()
        elif cmd == "watch":
            pusher.watch()
        elif cmd == "push" and len(sys.argv) > 3:
            local = sys.argv[2]
            remote = sys.argv[3]
            pusher.upload_file(local, remote)
        else:
            print("Usage: python xbox_rom_pusher.py [init | sync | watch | push <local_file> <remote_path>]")
    else:
        pusher.sync_all()

if __name__ == "__main__":
    main()
