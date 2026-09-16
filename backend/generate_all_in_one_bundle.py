import json
import os
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

appdata_hub = os.path.expandvars(r'%APPDATA%\Cymatics\Cymatics Hub')

installed_packs = {}
if os.path.exists(os.path.join(appdata_hub, 'pack-folders.json')):
    with open(os.path.join(appdata_hub, 'pack-folders.json'), 'r', encoding='utf-8') as f:
        installed_packs = json.load(f)

installed_plugins = {}
if os.path.exists(os.path.join(appdata_hub, 'installed.json')):
    with open(os.path.join(appdata_hub, 'installed.json'), 'r', encoding='utf-8') as f:
        installed_plugins = json.load(f)

e_folders = [d.lower() for d in os.listdir(r'E:\\') if os.path.isdir(os.path.join(r'E:\\', d))]

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

unowned_vids = []
for item in catalog:
    title = item.get('title', '')
    vid = str(item.get('variant_id', ''))
    if vid and not is_owned(title):
        unowned_vids.append(vid)

all_in_one_url = "https://cymatics.fm/cart/" + ",".join([f"{v}:1" for v in unowned_vids]) + "?checkout"

print(f"Total Unowned Variants: {len(unowned_vids)}")
print(f"URL Character Length: {len(all_in_one_url)}")

# Test URL with Shopify
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
r = requests.get(all_in_one_url, headers=headers, allow_redirects=False)
print(f"Shopify Response Status: HTTP {r.status_code}")
if r.headers.get('Location'):
    print("Redirect Location:", r.headers.get('Location')[:140])

print("\n" + "="*80)
print(f"🌟 ALL-IN-ONE 97-ITEM MASTER BUNDLE CHECKOUT URL ($0.00):")
print(all_in_one_url)
print("="*80)
