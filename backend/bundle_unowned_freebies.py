import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

appdata_hub = os.path.expandvars(r'%APPDATA%\Cymatics\Cymatics Hub')

# 1. Load installed packs & plugins
installed_packs = {}
if os.path.exists(os.path.join(appdata_hub, 'pack-folders.json')):
    with open(os.path.join(appdata_hub, 'pack-folders.json'), 'r', encoding='utf-8') as f:
        installed_packs = json.load(f)

installed_plugins = {}
if os.path.exists(os.path.join(appdata_hub, 'installed.json')):
    with open(os.path.join(appdata_hub, 'installed.json'), 'r', encoding='utf-8') as f:
        installed_plugins = json.load(f)

# 2. Load physical folders on E:
e_folders = [d.lower() for d in os.listdir(r'E:\\') if os.path.isdir(os.path.join(r'E:\\', d))]

# 3. Load discovered free catalog products
with open(r'C:\AI-BS\saved_data\cymatics_discovered_free_drops.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

def is_owned(title):
    t_clean = title.lower().replace('cymatics -', '').replace('cymatics', '').strip()
    for p in installed_packs.keys():
        if t_clean in p.lower() or p.lower() in t_clean:
            return True
    for f in e_folders:
        if t_clean in f or f in t_clean:
            return True
    for pl in installed_plugins.keys():
        if pl.replace('-', '') in t_clean.replace('-', '').replace(' ', ''):
            return True
    return False

unowned = []
owned_count = 0
for item in catalog:
    title = item.get('title', '')
    vid = str(item.get('variant_id', ''))
    if not vid:
        continue
    if is_owned(title):
        owned_count += 1
    else:
        unowned.append(item)

print(f"Total Free Catalog Products: {len(catalog)}")
print(f"Already in Local Library / NVMe: {owned_count}")
print(f"Unclaimed / Not in Library: {len(unowned)}")

# Chunk into bundles of 25 for 100% browser URL safety
vids = [str(u['variant_id']) for u in unowned if u.get('variant_id')]
chunks = [vids[i:i + 25] for i in range(0, len(vids), 25)]

print("\n" + "="*80)
print(f"📦 GENERATED {len(chunks)} AUTO-BUNDLE CLAIM LINKS FOR ALL {len(vids)} UNOWNED FREEBIES:")
print("="*80)

for idx, chunk in enumerate(chunks, 1):
    items_in_chunk = [u['title'] for u in unowned if str(u.get('variant_id')) in chunk]
    link = f"https://cymatics.fm/cart/{','.join([f'{v}:1' for v in chunk])}?checkout"
    print(f"\n--- BUNDLE PART {idx} of {len(chunks)} ({len(chunk)} Items at $0.00) ---")
    print(f"Includes: {', '.join(items_in_chunk[:5])}...")
    print(f"Direct Claim URL: {link}")
