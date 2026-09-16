import sys
import os
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

items_to_check = [
    "PHANTOM - Ghost Reverb Engine",
    "CORROSION: Tonal & Noise Enhancer",
    "NC-73",
    "PLINKO",
    "Casino - Baby Keem Inspired Pack",
    "Daydream - Vocal Loops",
    "Trinity - Wet Percussion",
    "Duality - Vintage Melodies",
    "BOOM'N - Melodies",
    "Whisper - Melody Collection",
    "Cascade - Vocal Loops",
    "Comet - Drum Loops",
    "HORIZON",
    "Destiny - Analog Melodies",
    "Octagon - Don Toliver Pack",
    "Phalanx - 808 & Bass",
    "Trinity - MIDI Collection",
    "Duality - Ambient Melodies",
    "BOOM’N - Drum Loops",
    "SHIFTER",
    "EXODUS Various Melodies",
    "EXODUS Various Drums",
    "Evolution - Guitar Melodies",
    "Ripple - Pop Guitars"
]

# 1. Local disk scan
e_drive = [f for f in os.listdir("E:\\") if os.path.isdir(os.path.join("E:\\", f))] if os.path.exists("E:\\") else []
vst3_files = os.listdir(r"C:\Program Files\Common Files\VST3") if os.path.exists(r"C:\Program Files\Common Files\VST3") else []
prog_files = os.listdir(r"C:\Program Files\Cymatics") if os.path.exists(r"C:\Program Files\Cymatics") else []
hub_pack_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
hub_packs = {}
if os.path.exists(os.path.join(hub_pack_dir, "pack-folders.json")):
    with open(os.path.join(hub_pack_dir, "pack-folders.json"), "r", encoding="utf-8") as f:
        hub_packs = json.load(f)

# 2. Free catalog drops scan
free_catalog_file = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"
free_catalog = []
if os.path.exists(free_catalog_file):
    with open(free_catalog_file, "r", encoding="utf-8") as f:
        free_catalog = json.load(f)

# 3. Live shopify search helper
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def search_shopify(keyword):
    clean_k = keyword.split('-')[0].split(':')[0].strip().lower()
    for item in free_catalog:
        if clean_k in item.get('title', '').lower() or clean_k in item.get('handle', '').lower():
            return item
    try:
        r = requests.get(f"https://cymatics.fm/products/{clean_k.replace(' ', '-')}.js", headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            variants = data.get('variants', [])
            return {
                'title': data.get('title'),
                'price': f"{variants[0].get('price', 0)/100:.2f}" if variants else 'N/A',
                'variant_id': variants[0].get('id') if variants else 'N/A',
                'direct_checkout': f"https://cymatics.fm/cart/{variants[0].get('id')}:1?checkout" if variants else ''
            }
    except:
        pass
    return None

results = []

for item_name in items_to_check:
    clean = item_name.lower().replace(":", "").replace("-", " ")
    tokens = [t.strip() for t in clean.split() if len(t.strip()) > 2 and t.strip() not in ["collection", "inspired", "pack", "various", "engine", "enhancer"]]
    
    # Check VST3
    vst_match = [v for v in vst3_files if any(t in v.lower() for t in tokens if len(t) > 3)]
    prog_match = [p for p in prog_files if any(t in p.lower() for t in tokens if len(t) > 3)]
    
    # Check E:\ drive
    e_match = [e for e in e_drive if any(t in e.lower() for t in tokens if len(t) > 3)]
    
    # Check Hub packs
    hub_match = [hp for hp, data in hub_packs.items() if any(t in hp.lower() or t in data.get('folder_name', '').lower() for t in tokens if len(t) > 3)]
    
    # Check free catalog / live shopify
    shop_match = search_shopify(item_name)
    
    is_on_disk = bool(vst_match or e_match or hub_match or prog_match)
    disk_loc = []
    if vst_match: disk_loc.append(f"VST3: {vst_match[0]}")
    if e_match: disk_loc.append(f"E:\\ Drive: {e_match[0]}")
    if hub_match: disk_loc.append(f"Hub: {hub_match[0]}")
    if prog_match and not vst_match: disk_loc.append(f"Program: {prog_match[0]}")
    
    results.append({
        "item": item_name,
        "is_on_disk": is_on_disk,
        "disk_location": ", ".join(disk_loc) if is_on_disk else "Not on disk",
        "shopify_info": shop_match
    })

print(f"{'Item Name':<35} | {'On Disk?':<10} | {'Disk Location':<30} | {'Shopify Variant / Link'}")
print("-" * 115)
for r in results:
    on_disk_str = "YES" if r["is_on_disk"] else "NO"
    shop_str = ""
    if r["shopify_info"]:
        shop_str = f"Variant: {r['shopify_info'].get('variant_id')} (${r['shopify_info'].get('price')})"
    print(f"{r['item']:<35} | {on_disk_str:<10} | {r['disk_location']:<30} | {shop_str}")
