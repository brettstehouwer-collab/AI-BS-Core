"""
Script Name: aibs_antigravity_linker.py
Intent: Automatically discover, index, and wire all identified AI-BS master directories, 
        model vaults, vector memories, and resources across C:, D:, and E: drives into 
        the Google Antigravity / AI-BS master configuration framework.
"""

import os
import json
from pathlib import Path

# Master paths discovered across drives C:, D:, E:
AIBS_DISCOVERED_PATHS = {
    "core_workspaces": [
        r"C:\AI-BS",
        r"C:\AI-BS-Models",
        r"C:\BS-Studio",
        r"C:\M-AI_BS_Android_Build",
        r"C:\StehouwerPublishing.com",
        r"C:\Recreational-Debut"
    ],
    "storage_and_models": [
        r"D:\AI-BS-ComfyUI-Models",
        r"D:\AI-BS_Master_Memory",
        r"D:\Stehouwer_Server\AI-BS",
        r"D:\Stehouwer_Server\AI-BS_LLM_Core",
        r"D:\AndroidStudioProjects\AI-BS tunnel"
    ],
    "resources_and_media": [
        r"E:\AI_BS_Resources",
        r"E:\AI_BS_Resources\Ollama",
        r"E:\AI_BS_Resources\ChromaDB",
        r"E:\AI-BS Broadcast Studio",
        r"E:\Recordings\AI-BS Matrix",
        r"E:\.gemini\history\ai-bs",
        r"E:\.gemini\history\ai-bs-matrix"
    ]
}

CONFIG_TARGET = r"C:\AI-BS\saved_data\antigravity_omni_mounts.json"

def verify_and_link():
    manifest = {"active_mounts": {}, "missing_paths": []}
    
    for category, paths in AIBS_DISCOVERED_PATHS.items():
        manifest["active_mounts"][category] = {}
        for p in paths:
            path_obj = Path(p)
            if path_obj.exists():
                manifest["active_mounts"][category][str(path_obj)] = "CONNECTED"
            else:
                manifest["missing_paths"].append(str(path_obj))

    os.makedirs(os.path.dirname(CONFIG_TARGET), exist_ok=True)
    with open(CONFIG_TARGET, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
        
    print(f"[OK] Antigravity Omni-Mount configuration successfully written to {CONFIG_TARGET}")

if __name__ == "__main__":
    verify_and_link()
