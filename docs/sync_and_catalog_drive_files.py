r"""AI-BS Sovereign Google Drive Sync & Inspection Engine.

Scans all 31 mapped Google Drive folders, catalogs every file/asset,
and syncs/exports high-value documents, manuscripts, spreadsheets,
and scripts into C:\AI-BS\synced_drive_assets\.
"""
import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List

CATALOG_JSON = Path("C:/AI-BS/docs/scattered_drive_folders_catalog.json")
INVENTORY_JSON = Path("C:/AI-BS/docs/scattered_drive_files_inventory.json")
SYNC_ROOT = Path("C:/AI-BS/synced_drive_assets")

CATEGORY_MAP = {
    # 1. Engineering & Backups
    "1LkvLlv26CtdvJgYNvuR-Yw03r1eMyJA4": "01_Engineering_Backups/PC_Backup_C_Drive",
    "1qfPSt1VP0T7RAt5t8FsdWD7LBEcAjn-3": "01_Engineering_Backups/AI_BS_Private_Recovery",
    "1EP7kfZ2zxEzS6WdvB2ipzQXlc3LbAHse": "01_Engineering_Backups/AI_BS_Codex_Ledger",
    "1AuKV45cCnZhiNSVEt9BqVXn9VlyxcLLF": "01_Engineering_Backups/AI_BS_Engineering",
    "1g4y2J6dveKoZ72hKWhpk9PpbAViKGCLF": "01_Engineering_Backups/AI_Protocols_Workflows",
    "1siuY6PGT0MFtfzFN6SWsgtgTyhHt9d6m": "01_Engineering_Backups/BS_Game",

    # 2. Memoirs & Manuscripts
    "1G_S80cLrKEpoZwPD0wMcG64Dg2LU0uO4": "02_Memoirs_Manuscripts/Echos_Within_Manuscripts",
    "1SfUxwQU-jw9f9VjqxRJCMD0zC-vpRR7U": "02_Memoirs_Manuscripts/Memoir_Outlines",
    "1vXhImRqX4Uxtkb9eOKy4cHwSsATStK2B": "02_Memoirs_Manuscripts/Memoir_Archival",
    "1OzQre4Cnkq3oNNkSZ0mu0j4JKZkiFzJF": "02_Memoirs_Manuscripts/Creative_Screenplays",
    "1C-zl9s8Eh9rej9Os1EKn4bXaeHazJtzF": "02_Memoirs_Manuscripts/Writing_Literary_Works",
    "1uQpPzflF83pg6IYEsyyXM_QjiA5BiZwr": "02_Memoirs_Manuscripts/Personal_Writings_Memoirs",
    "1VWKkUaB7Zz2KQcevcltmXvxTm1lSIN29": "02_Memoirs_Manuscripts/Protocol_25_7_Satire",

    # 3. Finance & Trading
    "1ou4GhTN0pPxmCNKABV2MNUIGdIVOFJDz": "03_Finance_Trading/Macroeconomic_Synthesis",
    "1vbmmJcitPsA0408xqXeTYlzuB3JT38bx": "03_Finance_Trading/Trading_SOPs_Market_Strategy",
    "1g5hbYBGo-Q95bp8HYnPN0xF8GkgYflh9": "03_Finance_Trading/Economic_Research",
    "1f6honDav5gHksEOV6tM4CVlU7ZhI0oc-": "03_Finance_Trading/Local_Revenue_Prospectus",

    # 4. Real Estate & Commercial
    "1FBqzb_gmsXy9kD-cQP0wCY9EGPBKTfXy": "04_Real_Estate/NoCo_Real_Estate",
    "1zS7awgJlbETFxaHDDPVH6TglEyMP99ie": "04_Real_Estate/The_Simple_Chef",
    "1MUU9482JMKD87jwBDW8dpF4qmMxyr3x0": "04_Real_Estate/West_Michigan_Market_Leads",
    "19Lo5oh_F9dgdlV0HJj4RHDc26tGuaFfl": "04_Real_Estate/Recreational_Debut",

    # 5. Music & Audio
    "1SMHTEsz56uKShyEN5ce1sOh0KWH5E099": "05_Music_Audio/Suno_AI_Guides_Prompts",
    "1MwzZuqa0ZXdY5Uplm_oyTAG5Ptup1UCS": "05_Music_Audio/Music_Audio_Production",
    "1dZ5HeDTFlVRVtzLEQxbqFK-UPz6hDWCh": "05_Music_Audio/Audio_Stems_Stem_Vault",

    # 6. Health & Neural Recovery
    "1AIyyTx4_ws4BxVMGaP_p-Yzx7PKS4rmZ": "06_Health_Recovery/TBI_Psilocybin_Recovery",
    "1DF1zKb6jNYrWCQFcUM9kbc4HT2D1IvRf": "06_Health_Recovery/Fasting_Supplements_Health",
    "1Vf6Pu2Bidc0mxbXbLe2M7ic8qbQZXo1V": "06_Health_Recovery/Cognitive_Assessment_Clinical",

    # 7. Legal & Credentials
    "1PNGrAUt_yu-jxGReM59zN7kKqEqYt3Ap": "07_Legal_Credentials/PTCE_Pharmacy_Prep",
    "1QMe7DtuJRCV4HA4bFHUGmoP7gfqjO4ea": "07_Legal_Credentials/Legal_NDAs_Disputes",
    "1VKkSBXMgipdixRXwyttMISLRnz6OYdV9": "07_Legal_Credentials/Personal_Identity_Records",
    "1xD0KssY1RW77MO3BmumWwh5pdBGg0rCW": "07_Legal_Credentials/Professional_Credentials",
}

def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for c in invalid:
        name = name.replace(c, "_")
    return name.strip()

def list_folder_contents(folder_id: str) -> List[Dict[str, Any]]:
    cmd = ["gdrive.cmd", "readonly", "ls", folder_id, "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        return json.loads(proc.stdout)
    except Exception as e:
        print(f"  [ERROR] Listing folder {folder_id}: {e}")
        return []

def sync_file(item: Dict[str, Any], dest_dir: Path):
    file_id = item["id"]
    name = item["name"]
    mime = item.get("mimeType") or item.get("type") or ""
    safe_name = sanitize_filename(name)

    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        if mime == "application/vnd.google-apps.document":
            out_md = dest_dir / f"{safe_name}.md"
            out_txt = dest_dir / f"{safe_name}.txt"
            if not out_md.exists() and not out_txt.exists():
                print(f"    Exporting Doc: {name} -> {out_txt.name}", flush=True)
                res = subprocess.run(["gdrive.cmd", "readonly", "export", file_id, str(out_txt), "--format", "txt"], capture_output=True, timeout=15)
                if res.returncode != 0:
                    subprocess.run(["gdrive.cmd", "readonly", "export", file_id, str(out_md), "--format", "md"], capture_output=True, timeout=10)
        elif mime == "application/vnd.google-apps.spreadsheet":
            out_file = dest_dir / f"{safe_name}.csv"
            if not out_file.exists():
                print(f"    Exporting Sheet: {name} -> {out_file.name}", flush=True)
                subprocess.run(["gdrive.cmd", "readonly", "export", file_id, str(out_file), "--format", "csv"], capture_output=True, timeout=15)
        elif mime == "application/vnd.google-apps.presentation":
            out_file = dest_dir / f"{safe_name}.pdf"
            if not out_file.exists():
                print(f"    Exporting Presentation: {name} -> {out_file.name}", flush=True)
                subprocess.run(["gdrive.cmd", "readonly", "export", file_id, str(out_file), "--format", "pdf"], capture_output=True, timeout=15)
        elif mime != "application/vnd.google-apps.folder":
            # Regular binary/text file
            out_file = dest_dir / safe_name
            size_bytes = int(item.get("size", 0) or 0)
            if size_bytes > 100 * 1024 * 1024:
                print(f"    Skipping large file ({size_bytes / (1024*1024):.1f} MB): {name}", flush=True)
                return
            if not out_file.exists():
                print(f"    Downloading File ({size_bytes / 1024:.1f} KB): {name} -> {out_file.name}", flush=True)
                subprocess.run(["gdrive.cmd", "readonly", "download", file_id, "--out", str(out_file)], capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        print(f"    [WARN] Export/Download timed out for: {name} (skipping)", flush=True)
    except Exception as e:
        print(f"    [WARN] Failed to sync {name}: {e} (skipping)", flush=True)

def main():
    print("=" * 70)
    print("AI-BS GOOGLE DRIVE ASSET INVENTORY & SYNCHRONIZATION")
    print("=" * 70)

    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    if isinstance(catalog, dict):
        folder_items = list(catalog.items())
    elif isinstance(catalog, list):
        folder_items = [(f["id"], f) for f in catalog]
    else:
        raise ValueError("Invalid catalog format")

    inventory = {}
    total_files = 0
    synced_count = 0

    for idx, (folder_id, meta) in enumerate(folder_items, 1):
        folder_name = meta.get("name", "Unknown Folder")
        category_subpath = CATEGORY_MAP.get(folder_id, f"Miscellaneous/{folder_id}")
        target_dir = SYNC_ROOT / category_subpath
        
        print(f"\n[{idx:02d}/31] Scanning: {folder_name} ({folder_id})", flush=True)
        print(f"      Mapped to: {target_dir}", flush=True)

        files = list_folder_contents(folder_id)
        inventory[folder_id] = {
            "folder_name": folder_name,
            "category": category_subpath,
            "target_dir": str(target_dir),
            "file_count": len(files),
            "files": files
        }
        total_files += len(files)
        print(f"      Found {len(files)} files/folders.", flush=True)

        for file_item in files:
            sync_file(file_item, target_dir)
            synced_count += 1

    # Save full inventory
    with open(INVENTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)

    print("\n" + "=" * 70)
    print(f"INVENTORY & SYNC COMPLETE!")
    print(f"Total Folders Scanned: {len(folder_items)}")
    print(f"Total Files Cataloged: {total_files}")
    print(f"Inventory Saved: {INVENTORY_JSON}")
    print(f"Assets Synced To: {SYNC_ROOT}")
    print("=" * 70)

if __name__ == "__main__":
    main()
