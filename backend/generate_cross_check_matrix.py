import json
import os

hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
free_drops_file = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"
output_matrix_file = r"C:\AI-BS\saved_data\cymatics_cross_check_matrix.json"

# Scan E:\ drive directly
e_drive_folders = [f for f in os.listdir("E:\\") if os.path.isdir(os.path.join("E:\\", f))] if os.path.exists("E:\\") else []

installed_plugins = {}
if os.path.exists(os.path.join(hub_dir, "installed.json")):
    with open(os.path.join(hub_dir, "installed.json"), "r", encoding="utf-8") as f:
        installed_plugins = json.load(f)

pack_folders = {}
if os.path.exists(os.path.join(hub_dir, "pack-folders.json")):
    with open(os.path.join(hub_dir, "pack-folders.json"), "r", encoding="utf-8") as f:
        pack_folders = json.load(f)

owned_map = {}

# 1. Add all VST plugins
for p_slug, p_data in installed_plugins.items():
    owned_map[p_slug.lower().strip()] = {
        "name": p_slug.replace("-", " ").title(),
        "type": "Plugin",
        "details": f"VST3: Cymatics {p_slug.title()}"
    }

# 2. Add all Hub pack folders
for pack_slug, pack_data in pack_folders.items():
    folder_name = pack_data.get("folder_name", pack_slug)
    clean_name = folder_name.replace("Cymatics - ", "").replace("Cymatics-", "").replace("Steven Cymatics - ", "").strip()
    owned_map[clean_name.lower().strip()] = {
        "name": clean_name,
        "type": "Sample Pack",
        "details": f"Hub Folder: {folder_name}"
    }

# 3. Add all E:\ root sample packs
for ef in e_drive_folders:
    if any(k in ef.lower() for k in ["cymatics", "dope", "generations", "sessions", "kingdom", "apocalypse", "destiny", "solace", "euphoria", "daydream", "duality", "phalanx", "ripple", "terra", "trinity", "whisper", "boom"]):
        clean_name = ef.replace("Cymatics - ", "").replace("Cymatics-", "").replace("Steven Cymatics - ", "").strip()
        owned_map[clean_name.lower().strip()] = {
            "name": clean_name,
            "type": "Sample Pack",
            "details": f"E:\\{ef}"
        }

matrix = []
seen_titles = set()

# Add all owned items as checked off
for k, data in owned_map.items():
    t = data["name"]
    seen_titles.add(t.lower().strip())
    matrix.append({
        "title": t,
        "category": data["type"],
        "status": "CHECKED_OFF",
        "status_label": "CLAIMED & VERIFIED ON DISK",
        "is_owned": True,
        "price": "$0.00",
        "details": data["details"],
        "direct_link": None
    })

# Add remaining free catalog drops if any
free_catalog = []
if os.path.exists(free_drops_file):
    with open(free_drops_file, "r", encoding="utf-8") as f:
        free_catalog = json.load(f)

for item in free_catalog:
    if item.get("price") != "0.00":
        continue
    t = item.get("title", "")
    t_clean = t.lower().strip()
    
    is_match = False
    for o_k in owned_map.keys():
        if o_k in t_clean or t_clean in o_k:
            is_match = True
            break
            
    if not is_match and t_clean not in seen_titles:
        seen_titles.add(t_clean)
        matrix.append({
            "title": t,
            "category": "Sample Pack" if "plugin" not in t_clean else "Plugin",
            "status": "UNCLAIMED_FREE",
            "status_label": "AVAILABLE FREE ($0.00)",
            "is_owned": False,
            "price": "$0.00 FREE",
            "variant_id": item.get("variant_id"),
            "direct_link": item.get("direct_checkout", f"https://cymatics.fm/cart/{item.get('variant_id')}:1?checkout"),
            "details": f"Shopify Variant: {item.get('variant_id')}"
        })

with open(output_matrix_file, "w", encoding="utf-8") as f:
    json.dump(matrix, f, indent=2)

print(f"Master Cross-Check Matrix (with E:\\ Drive Ingestion):")
print(f"  -> Checked Off / Verified on Disk: {len([m for m in matrix if m['is_owned']])}")
print(f"  -> Unclaimed Free: {len([m for m in matrix if not m['is_owned']])}")
print(f"  -> Total Matrix Items: {len(matrix)}")
