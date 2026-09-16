import os
import subprocess
import json

cache_dir = r"C:\Users\footb\AppData\Roaming\Cymatics Hub\installer-cache"
docs_dir = r"C:\AI-BS\docs"
vst3_dir = r"C:\Program Files\Common Files\VST3"

# Gather all installed VST3 names
installed_vst3s = set()
if os.path.exists(vst3_dir):
    for root, dirs, files in os.walk(vst3_dir):
        for d in dirs:
            if d.endswith(".vst3"):
                installed_vst3s.add(d.lower().replace(".vst3", "").replace("cymatics", "").replace("-", " ").replace("_", " ").strip())
        for f in files:
            if f.endswith(".vst3"):
                installed_vst3s.add(f.lower().replace(".vst3", "").replace("cymatics", "").replace("-", " ").replace("_", " ").strip())

# Gather all installer exe files
all_installers = []
for d in [cache_dir, docs_dir]:
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith(".exe") and any(k in f.lower() for k in ["installer", "setup", "cymatics", "dream", "nv73", "eqc"]):
                all_installers.append((f, os.path.join(d, f)))

# De-duplicate installers by name
unique_installers = {}
for name, p in all_installers:
    if name not in unique_installers:
        unique_installers[name] = p

uninstalled_installers = []

for name, p in unique_installers.items():
    # Clean name to match VST3
    clean = name.lower().replace("cymatics", "").replace("installer", "").replace("setup", "").replace("win", "").replace("pc", "").replace(".exe", "").replace("-", " ").replace("_", " ").replace("%20", " ")
    clean = "".join([c for c in clean if not c.isdigit() and c != '.']).strip()
    
    # Check if any installed VST3 matches
    matched = False
    for iv in installed_vst3s:
        if clean in iv or iv in clean or any(w in iv for w in clean.split() if len(w) > 3):
            matched = True
            break
            
    if not matched:
        uninstalled_installers.append((name, p, clean))

print(f"Total Unique Installers Scanned: {len(unique_installers)}")
print(f"Total Already Installed VST3s:   {len(installed_vst3s)}")
print(f"Installers Needing Installation: {len(uninstalled_installers)}\n")

for idx, (name, p, clean) in enumerate(uninstalled_installers, 1):
    print(f"{idx}. {name} (Clean: '{clean}')")
