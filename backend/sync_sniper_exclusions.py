import json
import os
import re

hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
installed_plugins = {}
pack_folders = {}

if os.path.exists(os.path.join(hub_dir, "installed.json")):
    with open(os.path.join(hub_dir, "installed.json"), "r", encoding="utf-8") as f:
        installed_plugins = json.load(f)

if os.path.exists(os.path.join(hub_dir, "pack-folders.json")):
    with open(os.path.join(hub_dir, "pack-folders.json"), "r", encoding="utf-8") as f:
        pack_folders = json.load(f)

owned_items = set()

# Add all plugins
for k in installed_plugins.keys():
    owned_items.add(k.lower().strip())
    owned_items.add(k.lower().replace("-", " ").strip())

# Add all sample packs
for k, v in pack_folders.items():
    owned_items.add(k.lower().strip())
    owned_items.add(k.lower().replace("-", " ").strip())
    folder_name = v.get("folder_name", "")
    if folder_name:
        clean_f = folder_name.replace("Cymatics - ", "").replace("Cymatics-", "").lower().strip()
        owned_items.add(clean_f)
        owned_items.add(clean_f.replace("(", "").replace(")", "").replace("-", " ").strip())

# Also add known claimed ones
extra_claimed = [
    "dope collection - bonus stash",
    "dope collection - vocals",
    "dope collection - drums",
    "dope collection - melodies",
    "mystery - 11 year anniversary edition",
    "destiny - analog melodies",
    "casino - baby keem inspired pack",
    "daydream - vocal loops",
    "cascade - vocal loops",
    "boom'n - drum loops",
    "boom'n - melodies",
    "apocalypse - launch edition"
]
for item in extra_claimed:
    owned_items.add(item.lower().strip())

# Format ALREADY_OWNED set for python file
lines = [f'    "{x}",' for x in sorted(owned_items)]
set_code = "ALREADY_OWNED = {\n" + "\n".join(lines) + "\n}"

# Replace in aibs_cymatics_sniper.py
sniper_path = r"C:\AI-BS\backend\aibs_cymatics_sniper.py"
with open(sniper_path, "r", encoding="utf-8") as f:
    content = f.read()

new_content = re.sub(r'ALREADY_OWNED = \{[^}]+\}', set_code, content)

with open(sniper_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Updated ALREADY_OWNED in aibs_cymatics_sniper.py with {len(owned_items)} unique owned entries!")
