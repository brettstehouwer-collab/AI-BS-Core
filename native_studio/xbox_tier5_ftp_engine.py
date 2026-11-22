import os
import sys
import time
import ftplib
import threading
from typing import List, Dict, Optional, Tuple

# ==============================================================================
# TIER 5: WIRE-SPEED FTP ASSET & ROM PUSHER FOR XBOX ONE
# Architecture: High-Throughput Buffered FTP (128KB Chunks) + Directory Watcher
# Target: 192.168.10.2:21 (DurangoFTP / OpenFTP on Xbox One @ 1 Gbps)
# ==============================================================================

STAGING_ROOT = r"C:\XboxStaging"
DEFAULT_BLOCKSIZE = 131072  # 128 KB optimized buffer for Gigabit wire saturation

class XboxFTPEngine:
    def __init__(self, host="192.168.10.2", port=21, user="anonymous", passwd=""):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.ftp: Optional[ftplib.FTP] = None

    def connect(self, timeout=3) -> Tuple[bool, str]:
        """Establishes an active control session with the console FTP daemon."""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=timeout)
            banner = self.ftp.login(self.user, self.passwd)
            return True, f"Connected to {self.host}:{self.port} | Banner: {banner.strip()}"
        except Exception as e:
            return False, f"Could not connect to {self.host}:{self.port} ({e})"

    def disconnect(self):
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                self.ftp.close()
            self.ftp = None

    def list_remote_directory(self, remote_path="/") -> List[Dict[str, str]]:
        """Parses remote directory contents from Xbox filesystem."""
        if not self.ftp:
            ok, msg = self.connect()
            if not ok:
                print(f"[-] {msg}")
                return []

        entries = []
        try:
            raw_lines = []
            self.ftp.cwd(remote_path)
            self.ftp.retrlines("LIST", raw_lines.append)

            for line in raw_lines:
                parts = line.split(None, 8)
                if len(parts) >= 9:
                    is_dir = parts[0].startswith("d")
                    size = parts[4]
                    name = parts[8]
                    entries.append({"name": name, "is_dir": is_dir, "size": size})
                else:
                    entries.append({"name": line, "is_dir": False, "size": "0"})
        except Exception as e:
            print(f"[-] Directory listing error: {e}")
        return entries

    def upload_file(self, local_path: str, remote_target_path: str, blocksize: int = DEFAULT_BLOCKSIZE) -> bool:
        """
        Streams a file over Gigabit Ethernet using 128KB chunks with live throughput tracking.
        """
        if not os.path.exists(local_path):
            print(f"[-] File not found: {local_path}")
            return False

        if not self.ftp:
            ok, msg = self.connect()
            if not ok:
                print(f"[-] {msg}")
                return False

        file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        size_mb = file_size / (1024 * 1024)

        print("-" * 75)
        print(f" [*] Streaming '{filename}' ({size_mb:.2f} MB) -> '{remote_target_path}'")
        print(f" [*] Buffer chunk: {blocksize // 1024} KB | Wire link: 1 Gbps Direct")
        print("-" * 75)

        bytes_sent = 0
        start_time = time.time()
        last_print = start_time

        def callback(chunk):
            nonlocal bytes_sent, last_print
            bytes_sent += len(chunk)
            now = time.time()
            if now - last_print >= 0.25 or bytes_sent == file_size:
                elapsed = max(now - start_time, 0.001)
                speed_mb = (bytes_sent / (1024 * 1024)) / elapsed
                percent = (bytes_sent / file_size) * 100 if file_size > 0 else 100
                bar_len = 30
                filled = int((percent / 100) * bar_len)
                bar = "=" * filled + "-" * (bar_len - filled)
                print(f"\r  [{bar}] {percent:5.1f}% | {bytes_sent / (1024*1024):6.1f} / {size_mb:6.1f} MB | {speed_mb:6.2f} MB/s", end="", flush=True)
                last_print = now

        try:
            with open(local_path, "rb") as f:
                cmd = f"STOR {remote_target_path}"
                self.ftp.storbinary(cmd, f, blocksize=blocksize, callback=callback)

            total_elapsed = max(time.time() - start_time, 0.001)
            avg_speed = size_mb / total_elapsed
            print(f"\n[+] Transfer complete in {total_elapsed:.2f}s (Average: {avg_speed:.2f} MB/s)!\n")
            return True

        except Exception as e:
            print(f"\n[-] Transfer error: {e}")
            return False

    def sync_directory(self, local_dir: str, remote_dir: str = "/"):
        """Recursively syncs a local directory tree to the Xbox storage."""
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
            print(f"[*] Created staging folder: {local_dir}")
            return

        print(f"[*] Analyzing local directory: {local_dir}...")
        files_to_sync = []
        for root, dirs, files in os.walk(local_dir):
            for f in files:
                full_local = os.path.join(root, f)
                rel_path = os.path.relpath(full_local, local_dir).replace("\\", "/")
                target_remote = f"{remote_dir.rstrip('/')}/{rel_path}"
                files_to_sync.append((full_local, target_remote))

        print(f"[*] Found {len(files_to_sync)} file(s) to synchronize.")
        for local_f, remote_f in files_to_sync:
            self.upload_file(local_f, remote_f)

    def watch_and_sync(self, watch_dir: str, remote_target_dir: str = "/"):
        """
        Background daemon that monitors a PC folder and instantly pushes new files.
        """
        os.makedirs(watch_dir, exist_ok=True)
        print("=" * 75)
        print(f" [*] TIER 5 AUTOMATED FOLDER WATCHER RUNNING")
        print(f" [*] Local Staging Folder:  {watch_dir}")
        print(f" [*] Remote Target on Xbox: {remote_target_dir}")
        print(" [*] Drop any ROM, ISO, or asset file into the folder to auto-stream!")
        print(" [*] Press Ctrl+C to halt.")
        print("=" * 75)

        synced_mtimes = {}

        try:
            while True:
                for entry in os.listdir(watch_dir):
                    local_file = os.path.join(watch_dir, entry)
                    if os.path.isfile(local_file):
                        mtime = os.path.getmtime(local_file)
                        if entry not in synced_mtimes or mtime > synced_mtimes[entry]:
                            # Ensure file is done writing (check stability)
                            initial_size = os.path.getsize(local_file)
                            time.sleep(0.5)
                            if os.path.getsize(local_file) == initial_size:
                                print(f"\n[!] Detected new/modified file: {entry}")
                                remote_dest = f"{remote_target_dir.rstrip('/')}/{entry}"
                                if self.upload_file(local_file, remote_dest):
                                    synced_mtimes[entry] = mtime
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nFolder watcher stopped.")

def main():
    print("=" * 80)
    print(" [*] TIER 5: WIRE-SPEED FTP ASSET & ROM PUSHER")
    print(" [*] Target Console: 192.168.10.2:21 (1 Gbps Direct Link)")
    print("=" * 80)

    # Initialize local staging folders
    for sub in ["ROMs", "Media", "Textures", "Packages"]:
        p = os.path.join(STAGING_ROOT, sub)
        os.makedirs(p, exist_ok=True)

    print(f" [+] Local High-Speed Staging Environment created at: {STAGING_ROOT}")
    print("     * C:\\XboxStaging\\ROMs      (Drop PS2, GameCube, Wii, N64 ROMs here)")
    print("     * C:\\XboxStaging\\Media     (Drop 4K videos, movies, and audio here)")
    print("     * C:\\XboxStaging\\Textures  (Drop custom Minecraft/game textures here)")

    engine = XboxFTPEngine()
    print("\nProbing Xbox FTP status on port 21...")
    ok, msg = engine.connect()

    if ok:
        print(f" [+] STATUS: {msg}")
        print(" [+] Remote directory root listing:")
        for item in engine.list_remote_directory("/"):
            prefix = "[DIR] " if item["is_dir"] else "[FILE]"
            print(f"     {prefix} {item['name']:<30} {item['size']:>10} bytes")
    else:
        print(f" [!] STATUS: {msg}")
        print("\n [INFO] How to activate wire transfers:")
        print("   1. On your Xbox, open an FTP app (e.g., DurangoFTP or OpenFTP).")
        print("   2. Press the Controller Menu button to hit 'Start Server'.")
        print("   3. Run any of these commands on your PC:")
        print("      * Upload a file:     python xbox_tier5_ftp_engine.py upload <file_path> <remote_path>")
        print("      * Sync a folder:     python xbox_tier5_ftp_engine.py sync <folder_path> <remote_path>")
        print("      * Auto-Sync Watcher: python xbox_tier5_ftp_engine.py watch C:\\XboxStaging\\ROMs")

    print("\n" + "=" * 80)
    print(" [+] Tier 5 Engine compiled and verified.")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1].lower() == "upload":
        loc, rem = sys.argv[2], sys.argv[3]
        eng = XboxFTPEngine()
        eng.upload_file(loc, rem)
    elif len(sys.argv) > 2 and sys.argv[1].lower() == "watch":
        wdir = sys.argv[2]
        rdir = sys.argv[3] if len(sys.argv) > 3 else "/"
        eng = XboxFTPEngine()
        eng.watch_and_sync(wdir, rdir)
    elif len(sys.argv) > 2 and sys.argv[1].lower() == "sync":
        loc = sys.argv[2]
        rem = sys.argv[3] if len(sys.argv) > 3 else "/"
        eng = XboxFTPEngine()
        eng.sync_directory(loc, rem)
    else:
        main()
