import os
import sys
import json
import psutil

# 1. Check if any process has DesktopProfile in command line
found_procs = []
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = " ".join(p.info['cmdline'] or [])
        if 'DesktopProfile' in cmd or 'BroadcastProfile' in cmd:
            found_procs.append((p.info['pid'], p.info['name'], cmd))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Found {len(found_procs)} processes using Studio profiles.")
for pid, name, cmd in found_procs:
    print(f"PID {pid} ({name}): {cmd[:120]}...")

# 2. Update Preferences in DesktopProfile and BroadcastProfile
origins = [
    "http://127.0.0.1:5173,*",
    "http://localhost:5173,*",
    "https://ai-bs-dashboard.web.app,*"
]

for profile in ['DesktopProfile', 'BroadcastProfile']:
    pref_path = os.path.expandvars(rf'%LOCALAPPDATA%\AI_BS_Studio\{profile}\Default\Preferences')
    if os.path.exists(pref_path):
        try:
            with open(pref_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            profile_sec = data.setdefault('profile', {})
            content_settings = profile_sec.setdefault('content_settings', {})
            exceptions = content_settings.setdefault('exceptions', {})
            
            # media_stream_mic: 1 = Allow, 2 = Block
            mic_sec = exceptions.setdefault('media_stream_mic', {})
            # media_stream_camera: 1 = Allow, 2 = Block
            cam_sec = exceptions.setdefault('media_stream_camera', {})
            
            for orig in origins:
                mic_sec[orig] = {
                    'last_modified': '134331751899147752',
                    'setting': 1
                }
                cam_sec[orig] = {
                    'last_modified': '134331751899147752',
                    'setting': 1
                }
            
            with open(pref_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Successfully updated {profile} Preferences to Allow (setting: 1) for microphone and camera.")
        except Exception as ex:
            print(f"Error updating {profile}: {ex}")
    else:
        print(f"Preferences not found at {pref_path}")
