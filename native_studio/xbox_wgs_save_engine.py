import os
import struct
import shutil
import time
import glob
import sys
import zlib
from typing import List, Dict, Any, Optional

# ==============================================================================
# TIER 3: XBOX CONNECTED STORAGE (WGS) BINARY DESERIALIZER & MODDING ENGINE
# Supports parsing, mapping, backup, hex inspection, and patching for Xbox saves.
# ==============================================================================

class WGSEngine:
    def __init__(self):
        self.local_appdata = os.environ.get("LOCALAPPDATA", "")
        self.packages_dir = os.path.join(self.local_appdata, "Packages")

    def discover_wgs_games(self) -> List[Dict[str, Any]]:
        """Scans LocalAppData Packages for active Xbox Connected Storage games."""
        games = []
        if not os.path.exists(self.packages_dir):
            return games

        for pkg in os.listdir(self.packages_dir):
            wgs_dir = os.path.join(self.packages_dir, pkg, "SystemAppData", "wgs")
            if os.path.exists(wgs_dir):
                # Find containers.index files
                index_files = glob.glob(os.path.join(wgs_dir, "*", "containers.index"))
                total_files = len(glob.glob(os.path.join(wgs_dir, "**", "*"), recursive=True))
                games.append({
                    "package_name": pkg,
                    "wgs_path": wgs_dir,
                    "index_files": index_files,
                    "total_files": total_files
                })
        return games

    def parse_containers_index(self, index_path: str) -> Dict[str, Any]:
        """Parses Microsoft binary containers.index file."""
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index not found: {index_path}")

        with open(index_path, "rb") as f:
            data = f.read()

        if len(data) < 8:
            return {"error": "File too small"}

        version, container_count = struct.unpack("<II", data[:8])
        result = {
            "version": version,
            "container_count": container_count,
            "file_size": len(data),
            "containers": []
        }

        offset = 8
        try:
            # Check for package name header
            if len(data) > 12:
                reserved = struct.unpack("<I", data[offset:offset+4])[0]
                offset += 4
                pkg_len = struct.unpack("<I", data[offset:offset+4])[0]
                offset += 4
                pkg_str = data[offset:offset+pkg_len*2].decode("utf-16le", errors="replace")
                offset += pkg_len * 2
                result["package_identity"] = pkg_str
        except Exception:
            pass

        return result

    def parse_container_manifest(self, manifest_path: str) -> List[Dict[str, Any]]:
        """
        Parses container.<N> to map opaque GUID blobs to real filenames.
        Container layout: Version(4B), ItemCount(4B), [FileName(128B UTF-16LE), GUID(16B)]
        """
        if not os.path.exists(manifest_path):
            return []

        with open(manifest_path, "rb") as f:
            data = f.read()

        if len(data) < 8:
            return []

        version, count = struct.unpack("<II", data[:8])
        items = []
        offset = 8

        for _ in range(count):
            if offset + 128 + 16 > len(data):
                break
            
            raw_name = data[offset:offset+128]
            offset += 128
            friendly_name = raw_name.decode("utf-16le", errors="replace").split("\x00")[0]

            # 16-byte binary GUID
            blob_guid_raw = data[offset:offset+16]
            offset += 16
            
            # Format GUID into standard hex string
            guid_hex = blob_guid_raw[::-1].hex().upper() # standard display reversal
            # Also raw hex for matching directory filename:
            file_match_hex = blob_guid_raw.hex().upper()

            items.append({
                "friendly_name": friendly_name,
                "blob_guid_raw": blob_guid_raw.hex(),
                "file_match_hex": file_match_hex
            })

        return items

    def create_backup(self, wgs_dir: str) -> str:
        """Creates a timestamped backup archive of the entire wgs save directory."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(__file__), "wgs_backups")
        os.makedirs(backup_dir, exist_ok=True)
        pkg_name = os.path.basename(os.path.dirname(os.path.dirname(wgs_dir)))
        backup_path = os.path.join(backup_dir, f"{pkg_name}_{ts}.bak")

        shutil.copytree(wgs_dir, backup_path)
        print(f"[+] Secure save backup created: {backup_path}")
        return backup_path

    def hex_dump(self, file_path: str, max_bytes: int = 256) -> str:
        """Produces a clean hex + ASCII side-by-side dump."""
        if not os.path.exists(file_path):
            return "File not found."

        with open(file_path, "rb") as f:
            data = f.read(max_bytes)

        lines = []
        lines.append(f"Hex dump of {os.path.basename(file_path)} (First {len(data)} bytes):")
        lines.append("-" * 75)
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(f"{i:04x}  {h:<48}  |{a}|")
        return "\n".join(lines)

    def search_and_patch(self, file_path: str, search_hex: str, replace_hex: str) -> bool:
        """
        Surgically replaces binary byte sequences in a save blob.
        Automatically verifies that lengths match to prevent file corruption.
        """
        search_bytes = bytes.fromhex(search_hex)
        replace_bytes = bytes.fromhex(replace_hex)

        if len(search_bytes) != len(replace_bytes):
            raise ValueError("Search and replace byte lengths must match to preserve binary structure!")

        with open(file_path, "rb") as f:
            data = bytearray(f.read())

        idx = data.find(search_bytes)
        if idx == -1:
            print(f"[-] Byte pattern {search_hex} not found in file.")
            return False

        print(f"[+] Found pattern at offset 0x{idx:04x} ({idx})")
        data[idx:idx+len(replace_bytes)] = replace_bytes

        with open(file_path, "wb") as f:
            f.write(data)

        print(f"[+] Successfully patched {file_path} at offset 0x{idx:04x}!")
        return True

def main():
    engine = WGSEngine()
    games = engine.discover_wgs_games()

    print("=" * 80)
    print(" [*] TIER 3: XBOX CONNECTED STORAGE (WGS) BINARY SAVE ENGINE")
    print(f" [*] Discovered {len(games)} Xbox / Windows Store Game(s) with Cloud Save containers")
    print("=" * 80)

    for i, g in enumerate(games):
        print(f"\n [{i+1}] Game Package: {g['package_name']}")
        print(f"     Save Path:    {g['wgs_path']}")
        print(f"     Files Stored: {g['total_files']} files")

        for idx_file in g["index_files"]:
            parent = os.path.dirname(idx_file)
            account_id = os.path.basename(parent)
            print(f"     Account Tree: {account_id}")
            
            # Inspect container subdirectories
            for item in os.listdir(parent):
                cont_folder = os.path.join(parent, item)
                if os.path.isdir(cont_folder):
                    manifests = glob.glob(os.path.join(cont_folder, "container.*"))
                    for m in manifests:
                        blobs = engine.parse_container_manifest(m)
                        for b in blobs:
                            print(f"       -> Container [{item[:8]}...] Mapped File: '{b['friendly_name']}'")
                            
                            # Find matching data blob in directory
                            for f in os.listdir(cont_folder):
                                if f != os.path.basename(m):
                                    f_size = os.path.getsize(os.path.join(cont_folder, f))
                                    print(f"          [BLOB] {f} ({f_size} bytes)")

    print("\n" + "=" * 80)
    print(" [+] Tier 3 Binary Deserializer ready for inspection and patching.")
    print("=" * 80)

if __name__ == "__main__":
    main()
