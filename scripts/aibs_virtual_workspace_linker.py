"""
Script Name: aibs_virtual_workspace_linker.py
Intent: Register multi-drive AI-BS paths into a virtual VS Code / Antigravity workspace 
        via symbolic linking and workspace folder arrays without moving physical files.
"""

import json
from pathlib import Path

VIRTUAL_WORKSPACE_PATH = r"C:\AI-BS\saved_data\ai_bs_virtual_omni.code-workspace"

ALL_DISCOVERED_PATHS = [
    r"C:\AI-BS",
    r"C:\AI-BS-Models",
    r"C:\BS-Studio",
    r"C:\M-AI_BS_Android_Build",
    r"C:\StehouwerPublishing.com",
    r"C:\Recreational-Debut",
    r"D:\AI-BS-ComfyUI-Models",
    r"D:\AI-BS_Master_Memory",
    r"D:\Stehouwer_Server\AI-BS",
    r"D:\Stehouwer_Server\AI-BS_LLM_Core",
    r"D:\AndroidStudioProjects\AI-BS tunnel",
    r"E:\AI_BS_Resources",
    r"E:\AI-BS Broadcast Studio",
    r"E:\Recordings\AI-BS Matrix"
]

def generate_virtual_workspace():
    workspace_folders = []
    for p in ALL_DISCOVERED_PATHS:
        path_obj = Path(p)
        if path_obj.exists():
            workspace_folders.append({
                "name": f"[{path_obj.drive}] {path_obj.name}",
                "path": str(path_obj)
            })

    workspace_payload = {
        "folders": workspace_folders,
        "settings": {
            "files.watcherExclude": {
                "**/.git/objects/**": True,
                "**/node_modules/**": True,
                "**/__pycache__/**": True
            }
        }
    }

    Path(VIRTUAL_WORKSPACE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(VIRTUAL_WORKSPACE_PATH, "w", encoding="utf-8") as f:
        json.dump(workspace_payload, f, indent=4)

    print(f"[OK] Virtual workspace configuration generated at {VIRTUAL_WORKSPACE_PATH} containing {len(workspace_folders)} mounted roots.")

if __name__ == "__main__":
    generate_virtual_workspace()
