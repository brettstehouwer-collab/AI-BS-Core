import subprocess
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

FOLDER_IDS = [
    "1LkvLlv26CtdvJgYNvuR-Yw03r1eMyJA4",
    "1qfPSt1VP0T7RAt5t8FsdWD7LBEcAjn-3",
    "1EP7kfZ2zxEzS6WdvB2ipzQXlc3LbAHse",
    "1siuY6PGT0MFtfzFN6SWsgtgTyhHt9d6m",
    "1G_S80cLrKEpoZwPD0wMcG64Dg2LU0uO4",
    "1SfUxwQU-jw9f9VjqxRJCMD0zC-vpRR7U",
    "1DF1zKb6jNYrWCQFcUM9kbc4HT2D1IvRf",
    "1vXhImRqX4Uxtkb9eOKy4cHwSsATStK2B",
    "1vbmmJcitPsA0408xqXeTYlzuB3JT38bx",
    "1VKkSBXMgipdixRXwyttMISLRnz6OYdV9",
    "1dZ5HeDTFlVRVtzLEQxbqFK-UPz6hDWCh",
    "1PNGrAUt_yu-jxGReM59zN7kKqEqYt3Ap",
    "1OzQre4Cnkq3oNNkSZ0mu0j4JKZkiFzJF",
    "1g4y2J6dveKoZ72hKWhpk9PpbAViKGCLF",
    "1VWKkUaB7Zz2KQcevcltmXvxTm1lSIN29",
    "1SMHTEsz56uKShyEN5ce1sOh0KWH5E099",
    "1g5hbYBGo-Q95bp8HYnPN0xF8GkgYflh9",
    "1f6honDav5gHksEOV6tM4CVlU7ZhI0oc-",
    "1uQpPzflF83pg6IYEsyyXM_QjiA5BiZwr",
    "1ou4GhTN0pPxmCNKABV2MNUIGdIVOFJDz",
    "1FBqzb_gmsXy9kD-cQP0wCY9EGPBKTfXy",
    "1C-zl9s8Eh9rej9Os1EKn4bXaeHazJtzF",
    "1MwzZuqa0ZXdY5Uplm_oyTAG5Ptup1UCS",
    "1AIyyTx4_ws4BxVMGaP_p-Yzx7PKS4rmZ",
    "1MUU9482JMKD87jwBDW8dpF4qmMxyr3x0",
    "1zS7awgJlbETFxaHDDPVH6TglEyMP99ie",
    "1Vf6Pu2Bidc0mxbXbLe2M7ic8qbQZXo1V",
    "1QMe7DtuJRCV4HA4bFHUGmoP7gfqjO4ea",
    "1AuKV45cCnZhiNSVEt9BqVXn9VlyxcLLF",
    "1xD0KssY1RW77MO3BmumWwh5pdBGg0rCW",
    "19Lo5oh_F9dgdlV0HJj4RHDc26tGuaFfl"
]

def inspect_folder(folder_id: str):
    record = {
        "id": folder_id,
        "name": None,
        "modified": None,
        "owners": [],
        "children": [],
        "error": None
    }
    # 1. Info
    try:
        res = subprocess.run(
            ["gdrive.cmd", "readonly", "info", folder_id, "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0:
            info = json.loads(res.stdout)
            record["name"] = info.get("name")
            record["modified"] = info.get("modifiedTime")
            record["owners"] = [o.get("displayName") for o in info.get("owners", [])]
        else:
            record["error"] = res.stderr.strip() or "Failed to fetch info"
    except Exception as e:
        record["error"] = str(e)

    # 2. Children / contents
    try:
        res = subprocess.run(
            ["gdrive.cmd", "readonly", "ls", folder_id, "--max", "15", "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0:
            items = json.loads(res.stdout)
            if isinstance(items, list):
                record["children"] = [
                    {"id": item.get("id"), "name": item.get("name"), "type": item.get("mimeType"), "size": item.get("size")}
                    for item in items
                ]
    except Exception as e:
        if not record["error"]:
            record["error"] = f"ls error: {e}"

    return record

if __name__ == "__main__":
    print(f"Starting inspection of {len(FOLDER_IDS)} scattered Google Drive folders...")
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for idx, res in enumerate(executor.map(inspect_folder, FOLDER_IDS)):
            results.append(res)
            print(f"[{idx+1:02d}/{len(FOLDER_IDS)}] {res['name'] or 'ERROR'} ({res['id']}) - {len(res['children'])} items")

    out_file = Path(r"C:\AI-BS\docs\scattered_drive_folders_catalog.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCompleted! Written to {out_file}")
