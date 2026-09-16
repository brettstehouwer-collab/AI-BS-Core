import json
import os
import re

hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"

installed_plugins = {}
pack_folders = {}
cached_products = {}

if os.path.exists(os.path.join(hub_dir, "installed.json")):
    with open(os.path.join(hub_dir, "installed.json"), "r", encoding="utf-8") as f:
        installed_plugins = json.load(f)

if os.path.exists(os.path.join(hub_dir, "pack-folders.json")):
    with open(os.path.join(hub_dir, "pack-folders.json"), "r", encoding="utf-8") as f:
        pack_folders = json.load(f)

if os.path.exists(os.path.join(hub_dir, "cached-products.json")):
    with open(os.path.join(hub_dir, "cached-products.json"), "r", encoding="utf-8") as f:
        cached_products = json.load(f)

# Also check physical downloads in sample library
download_folder = "E:\\AI_BS_Resources\\Cymatics_100GB_Drop"
downloaded_files = []
if os.path.exists(download_folder):
    downloaded_files = os.listdir(download_folder)

print(f"=== CYMATICS HUB INVENTORY ===")
print(f"Total Installed Plugins / Software: {len(installed_plugins)}")
print(f"Total Installed / Extracted Sample Packs in Hub: {len(pack_folders)}")
print(f"Total Cached Products in Hub: {len(cached_products)}")

print("\n--- INSTALLED PLUGINS IN CYMATICS HUB ---")
for slug in sorted(installed_plugins.keys()):
    print(f"  [Plugin] {slug}")

print("\n--- INSTALLED SAMPLE PACKS IN CYMATICS HUB ---")
for slug, path in sorted(pack_folders.items()):
    print(f"  [Pack] {slug:<30} -> {path}")

# Cross check against discovered free drops
with open(r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json", "r", encoding="utf-8") as f:
    free_drops = json.load(f)

# Build a comprehensive normalized owned set
all_owned_slugs = set(installed_plugins.keys()) | set(pack_folders.keys())
for item in cached_products.values():
    if isinstance(item, dict) and item.get('slug'):
        all_owned_slugs.add(item['slug'])

unclaimed_free = []
for drop in free_drops:
    if drop.get('price') != '0.00':
        continue
    drop_slug = drop.get('handle', '').lower()
    drop_title = drop.get('title', '').lower()
    
    # Check if matched in owned
    is_owned = False
    for owned in all_owned_slugs:
        o_clean = owned.replace('-', ' ').replace('_', ' ').strip()
        t_clean = drop_title.replace('-', ' ').replace('_', ' ').strip()
        s_clean = drop_slug.replace('-', ' ').replace('_', ' ').strip()
        if o_clean in t_clean or t_clean in o_clean or owned in drop_slug or drop_slug in owned:
            is_owned = True
            break
            
    if not is_owned:
        unclaimed_free.append(drop)

print(f"\n=======================================================")
print(f"  CROSS-CHECK SUMMARY")
print(f"=======================================================")
print(f"Total $0.00 Free Items in Catalog: {len([d for d in free_drops if d.get('price') == '0.00'])}")
print(f"Already Owned / Installed in Cymatics Hub: {len(all_owned_slugs)}")
print(f"Unclaimed $0.00 Free Packs: {len(unclaimed_free)}")

print("\n--- UNCLAIMED $0.00 FREE PACKS QUEUE (Top 25) ---")
for idx, item in enumerate(unclaimed_free[:25]):
    print(f"  [{idx+1}] {item['title']:<35} | Variant: {item['variant_id']} | URL: {item['direct_checkout']}")
