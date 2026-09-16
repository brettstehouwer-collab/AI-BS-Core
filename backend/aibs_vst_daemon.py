import os
import glob
import numpy as np
import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
try:
    from pedalboard import load_plugin
except ImportError:
    load_plugin = None

app = FastAPI(title="AI-BS VST3 Bridge Daemon")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hybrid VST3 Search Paths (incorporating Cymatics and MuseFX suites)
VST_PATHS = [
    r"C:\Program Files\Common Files\VST3",
    r"C:\Program Files\VSTPlugins",
    r"E:\AI_BS_Resources\VST3_Plugins",
    r"C:\ProgramData\Cymatics",
    r"E:\Cymatics\ProgramData",
    os.path.join(os.path.dirname(__file__), "vst3")
]

# Global state to hold loaded plugins
active_plugins = {}

@app.get("/api/vst/scan")
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

@app.post("/api/vst/load")
def load_vst(payload: dict):
    plugin_path = payload.get("path")
    if not plugin_path or not os.path.exists(plugin_path):
        return {"status": "error", "message": "Invalid plugin path"}
    
    try:
        plugin_id = os.path.basename(plugin_path)
        if plugin_id not in active_plugins:
            active_plugins[plugin_id] = load_plugin(plugin_path)
        return {"status": "success", "plugin_id": plugin_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/vst/active")
def get_active_plugins():
    """Lists currently instantiated VST3 plugins."""
    return {"status": "success", "active_plugins": list(active_plugins.keys())}

@app.get("/api/vst/parameters/{plugin_id}")
def get_vst_parameters(plugin_id: str):
    """Returns granular parameter schema, min/max bounds, and current values for a loaded VST."""
    if plugin_id not in active_plugins:
        # Fallback: if not loaded, try to find and load
        for path in VST_PATHS:
            candidate = os.path.join(path, plugin_id)
            if os.path.exists(candidate):
                try:
                    active_plugins[plugin_id] = load_plugin(candidate)
                    break
                except Exception:
                    pass

    if plugin_id not in active_plugins:
        return {"status": "error", "message": f"Plugin {plugin_id} not loaded"}

    plugin = active_plugins[plugin_id]
    params = []
    
    try:
        if hasattr(plugin, "parameters"):
            for name, param in plugin.parameters.items():
                p_info = {
                    "name": name,
                    "label": getattr(param, "label", name),
                    "min_value": float(getattr(param, "min_value", 0.0)),
                    "max_value": float(getattr(param, "max_value", 1.0)),
                    "default_value": float(getattr(param, "default_value", 0.5)),
                    "raw_value": float(getattr(param, "raw_value", getattr(plugin, name, 0.5))),
                    "unit": str(getattr(param, "unit", "")),
                }
                params.append(p_info)
    except Exception as e:
        print(f"Error reading parameters for {plugin_id}: {e}")

    # If parameters dictionary was empty, extract common known VST attributes
    if not params:
        common_attrs = ["gain", "drive", "distortion", "cutoff", "resonance", "reverb", "delay", "mix", "threshold", "ratio"]
        for attr in common_attrs:
            if hasattr(plugin, attr):
                try:
                    val = float(getattr(plugin, attr, 0.5))
                    params.append({
                        "name": attr,
                        "label": attr.capitalize(),
                        "min_value": 0.0,
                        "max_value": 1.0 if val <= 1.0 else 20000.0,
                        "default_value": val,
                        "raw_value": val,
                        "unit": "Hz" if "cutoff" in attr else "%"
                    })
                except Exception:
                    pass

    return {"status": "success", "plugin_id": plugin_id, "parameters": params}

@app.post("/api/vst/set-param")
def set_vst_param(payload: dict):
    """Mutates a single parameter on a loaded VST plugin in real time."""
    plugin_id = payload.get("plugin_id")
    param_name = payload.get("param_name")
    value = payload.get("value")

    if not plugin_id or plugin_id not in active_plugins:
        return {"status": "error", "message": f"Plugin {plugin_id} not active"}

    plugin = active_plugins[plugin_id]
    try:
        if hasattr(plugin, param_name):
            setattr(plugin, param_name, float(value))
        elif hasattr(plugin, "parameters") and param_name in plugin.parameters:
            setattr(plugin, param_name, float(value))
        else:
            return {"status": "error", "message": f"Parameter {param_name} not found"}
        
        return {"status": "success", "plugin_id": plugin_id, "param_name": param_name, "value": value}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Thematic Audio Modulation Profile Maps
THEME_PARAM_PROFILES = {
    "aggressive": {
        "drive": 0.85,
        "distortion": 0.80,
        "gain": 0.90,
        "feedback": 0.65,
        "cutoff": 8000,
        "decay": 0.20
    },
    "calm": {
        "drive": 0.10,
        "distortion": 0.05,
        "gain": 0.45,
        "reverb": 0.70,
        "cutoff": 1200,
        "decay": 0.85
    },
    "hype": {
        "rate": 0.95,
        "resonance": 0.75,
        "cutoff": 12000,
        "mix": 0.80,
        "speed": 0.90
    },
    "analytical": {
        "drive": 0.05,
        "distortion": 0.00,
        "gain": 0.50,
        "reverb": 0.15,
        "cutoff": 5000,
        "clarity": 0.90
    }
}

current_theme_state = {"theme": "neutral", "active_modulations": {}}

@app.get("/api/vst/theme-state")
def get_theme_state():
    return current_theme_state

@app.post("/api/vst/trigger-theme")
def trigger_vst_theme(payload: dict):
    theme = (payload.get("theme") or "neutral").lower().strip()
    profile = THEME_PARAM_PROFILES.get(theme, {})
    modulations_applied = {}

    for plugin_id, plugin in active_plugins.items():
        applied_for_plugin = {}
        for target_param, target_val in profile.items():
            # Check if parameter exists on pedalboard plugin
            if hasattr(plugin, target_param):
                try:
                    setattr(plugin, target_param, target_val)
                    applied_for_plugin[target_param] = target_val
                except Exception as e:
                    print(f"Failed to set {target_param} on {plugin_id}: {e}")
            else:
                # Iterate through plugin parameters dynamically
                if hasattr(plugin, "parameters"):
                    for param_name in plugin.parameters.keys():
                        if target_param in param_name.lower():
                            try:
                                setattr(plugin, param_name, target_val)
                                applied_for_plugin[param_name] = target_val
                            except Exception:
                                pass
        if applied_for_plugin:
            modulations_applied[plugin_id] = applied_for_plugin

    current_theme_state["theme"] = theme
    current_theme_state["active_modulations"] = modulations_applied or profile
    print(f"[VST Daemon] Applied Thematic Audio Modulation for '{theme}': {current_theme_state['active_modulations']}")
    return {
        "status": "success",
        "theme": theme,
        "modulations": current_theme_state["active_modulations"]
    }

@app.websocket("/ws/vst/{plugin_id}")
async def websocket_vst_processor(websocket: WebSocket, plugin_id: str):
    await websocket.accept()
    if plugin_id not in active_plugins:
        await websocket.send_json({"status": "error", "message": "Plugin not loaded"})
        await websocket.close()
        return

    plugin = active_plugins[plugin_id]
    sample_rate = 44100 # Default fallback, can be configured via first message

    try:
        while True:
            # Receive raw binary float32 audio data from Tone.js ScriptProcessor/AudioWorklet
            data = await websocket.receive_bytes()
            
            # Convert binary to numpy array
            audio_data = np.frombuffer(data, dtype=np.float32)
            
            # Pedalboard expects shape (channels, samples). Tone.js usually sends mono or interleaved stereo.
            # Assuming mono for this simple bridge
            audio_data = audio_data.reshape(1, -1)
            
            # Process through VST
            processed = plugin(audio_data, sample_rate)
            
            # Send back processed binary float32 data
            await websocket.send_bytes(processed.tobytes())
            
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
