"""
Script Name: aibs_workspace_syncer.py
Intent: Automatically bind and register all discovered multi-drive AI-BS paths 
        directly into the active workspace configuration and VS Code/Antigravity workspace file.
"""

import json
from pathlib import Path

WORKSPACE_FILE = r"C:\AI-BS\AI-BS_Sovereign.code-workspace"

DISCOVERED_FOLDERS = [
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

def update_workspace():
    folders = [{"path": p} for p in DISCOVERED_FOLDERS if Path(p).exists()]
    workspace_data = {
        "folders": folders,
        "settings": {
            "files.exclude": {
                "**/.git": True,
                "**/__pycache__": True,
                "**/.aibs_backups": True
            }
        }
    }
    
    with open(WORKSPACE_FILE, "w", encoding="utf-8") as f:
        json.dump(workspace_data, f, indent=4)
        
    print(f"[OK] Workspace successfully updated with {len(folders)} multi-drive folders at {WORKSPACE_FILE}")

if __name__ == "__main__":
    update_workspace()
