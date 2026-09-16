import os
import glob
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/vst", tags=["VST3 Audio Engine"])

VST_PATHS = [
    r"C:\Program Files\Common Files\VST3",
    r"C:\Program Files\VSTPlugins",
    r"E:\AI_BS_Resources\VST3_Plugins",
    r"C:\ProgramData\Cymatics",
    r"E:\Cymatics\ProgramData",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "vst3")
]

@router.get("/scan")
def scan_plugins():
    discovered = {}
    
    for base_path in VST_PATHS:
        if not os.path.exists(base_path):
            continue
        
        for root, dirs, files in os.walk(base_path):
            # Check directory bundles
            for d in dirs:
                if d.endswith(".vst3"):
                    clean_name = d.replace(".vst3", "")
                    if clean_name not in discovered:
                        cat = "Cymatics Suite" if "cymatics" in clean_name.lower() else ("MuseFX Suite" if "muse" in root.lower() or "muse" in clean_name.lower() else "General VST3")
                        vendor = "Cymatics" if "cymatics" in clean_name.lower() else ("Muse Hub" if "muse" in root.lower() or "muse" in clean_name.lower() else "Third-Party")
                        discovered[clean_name] = {
                            "name": clean_name,
                            "path": os.path.join(root, d),
                            "category": cat,
                            "vendor": vendor,
                            "is_instrument": any(k in clean_name.lower() for k in ["synth", "pluck", "piano", "omnivox", "keys", "guitar", "bass", "drum", "8bit"])
                        }
            # Check standalone vst3 binary files
            for f in files:
                if f.endswith(".vst3"):
                    clean_name = f.replace(".vst3", "")
                    if clean_name not in discovered:
                        cat = "Cymatics Suite" if "cymatics" in clean_name.lower() else ("MuseFX Suite" if "muse" in root.lower() or "muse" in clean_name.lower() else "General VST3")
                        vendor = "Cymatics" if "cymatics" in clean_name.lower() else ("Muse Hub" if "muse" in root.lower() or "muse" in clean_name.lower() else "Third-Party")
                        discovered[clean_name] = {
                            "name": clean_name,
                            "path": os.path.join(root, f),
                            "category": cat,
                            "vendor": vendor,
                            "is_instrument": any(k in clean_name.lower() for k in ["synth", "pluck", "piano", "omnivox", "keys", "guitar", "bass", "drum", "8bit"])
                        }

    sorted_plugins = sorted(list(discovered.values()), key=lambda x: (x["category"], x["name"]))
    return {
        "status": "success",
        "total_count": len(sorted_plugins),
        "plugins": sorted_plugins
    }

@router.get("/theme-state")
def get_theme_state():
    return {
        "status": "online",
        "theme": "neutral",
        "active_modulations": {
            "drive": 0.0,
            "reverb_wet": 0.15,
            "filter_cutoff_hz": 20000,
            "resonance": 1.0,
            "spatial_width": 1.0
        }
    }


@router.post("/trigger-theme")
@router.post("/api/vst/trigger-theme")
def trigger_theme(payload: Optional[dict] = None):
    theme_name = (payload or {}).get("theme", "neutral")
    return {
        "status": "success",
        "theme": theme_name,
        "action": f"Theme '{theme_name}' audio modulations engaged."
    }
