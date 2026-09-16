import os
import json

hub_db_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
vst3_dir = r"C:\Program Files\Common Files\VST3"
vst_dir = r"C:\Program Files\VSTPlugins"
cache_dir = r"C:\Users\footb\AppData\Roaming\Cymatics Hub\installer-cache"

# 1. Hub Installed Database
installed_json = os.path.join(hub_db_dir, "installed.json")
installed_db = {}
if os.path.exists(installed_json):
    installed_db = json.load(open(installed_json, "r", encoding="utf-8"))

# 2. Cached Plugin Installers
cached_exes = [f for f in os.listdir(cache_dir) if f.endswith(".exe") or "installer" in f.lower()] if os.path.exists(cache_dir) else []

# 3. System VST3 Plugins
system_vst3s = []
if os.path.exists(vst3_dir):
    for root, dirs, files in os.walk(vst3_dir):
        for d in dirs:
            if d.endswith(".vst3"):
                system_vst3s.append((d.replace(".vst3", ""), os.path.join(root, d)))
        for f in files:
            if f.endswith(".vst3"):
                system_vst3s.append((f.replace(".vst3", ""), os.path.join(root, f)))

# 4. System VST2 Plugins
system_vst2s = []
if os.path.exists(vst_dir):
    for f in os.listdir(vst_dir):
        if f.endswith(".dll"):
            system_vst2s.append((f.replace(".dll", ""), os.path.join(vst_dir, f)))

# Deduplicate
unique_vst3 = {}
for name, p in system_vst3s:
    clean_name = name.strip()
    if clean_name not in unique_vst3:
        unique_vst3[clean_name] = p

print("================================================================")
print("             CYMATICS HUB & SYSTEM PLUGIN AUDIT                 ")
print("================================================================")
print(f"1. Plugins Registered in Cymatics Hub DB: {len(installed_db)}")
print(f"2. Plugin Installers in Cache:            {len(cached_exes)}")
print(f"3. Unique VST3 Plugins on System:         {len(unique_vst3)}")
print(f"4. Legacy VST2 (.dll) on System:          {len(system_vst2s)}")
print("================================================================\n")

print("--- INSTALLED VST3 PLUGINS LIST ---")
for idx, (name, p) in enumerate(sorted(unique_vst3.items()), 1):
    category = "Cymatics Suite" if "cymatics" in name.lower() or "origin" in name.lower() or "daydream" in name.lower() or "pluto" in name.lower() or "space" in name.lower() or "diablo" in name.lower() else ("MuseFX Suite" if "muse" in p.lower() else "Third-Party")
    print(f"{idx:2d}. [{category}] {name}")

print("\n--- PLUGIN INSTALLER PACKAGES IN CACHE ---")
for idx, exe in enumerate(sorted(cached_exes), 1):
    print(f"{idx:2d}. {exe}")
