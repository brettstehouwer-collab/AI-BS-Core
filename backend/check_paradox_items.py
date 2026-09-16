import sys
import requests
from bs4 import BeautifulSoup
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

url = "https://cymatics.fm/pages/paradox-iii-launch-edition-overview"
r = requests.get(url, headers=headers)

print("Page Status:", r.status_code)
soup = BeautifulSoup(r.text, 'html.parser')
title = soup.title.string if soup.title else 'No Title'
print("Page Title:", title.strip())

# Check for pricing or buttons on the page
buttons = soup.find_all(['button', 'a'])
print("\nLinks / CTAs on Page:")
for b in buttons:
    href = b.get('href', '')
    txt = b.get_text(strip=True)
    if any(k in href.lower() or k in txt.lower() for k in ['cart', 'checkout', 'free', 'price', '$', 'get', 'download', 'buy']):
        print(f"  [{txt}] -> {href}")

# Search Shopify catalog for all PARADOX items
print("\nSearching Shopify catalog for 'Paradox' items...")
page = 1
all_paradox = []
while True:
    res = requests.get(f"https://cymatics.fm/products.json?limit=250&page={page}", headers=headers)
    if res.status_code != 200:
        break
    prods = res.json().get('products', [])
    if not prods:
        break
    for p in prods:
        if 'paradox' in p.get('title', '').lower() or 'paradox' in p.get('handle', '').lower():
            for v in p.get('variants', []):
                all_paradox.append({
                    'title': p.get('title'),
                    'handle': p.get('handle'),
                    'price': v.get('price'),
                    'available': v.get('available'),
                    'variant_id': v.get('id'),
                    'direct_checkout': f"https://cymatics.fm/cart/{v.get('id')}:1?checkout"
                })
    if len(prods) < 250:
        break
    page += 1

print(f"Total Paradox products found in Shopify catalog: {len(all_paradox)}")
for p in all_paradox:
    print(f"  -> Title: {p['title']:<40} | Price: ${p['price']} | Avail: {p['available']} | Checkout: {p['direct_checkout']}")

# Check local disk
print("\nChecking Local Disk (E:\\ and shared_cloud_drive):")
e_drive = os.listdir("E:\\") if os.path.exists("E:\\") else []
for f in e_drive:
    if 'paradox' in f.lower():
        print(f"  Found on E:\\: {f}")

hub_pack_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub\pack-folders.json"
if os.path.exists(hub_pack_dir):
    with open(hub_pack_dir, "r", encoding="utf-8") as f:
        hub_data = json.load(f)
        for k, v in hub_data.items():
            if 'paradox' in k.lower() or 'paradox' in str(v).lower():
                print(f"  Found in Hub: {k} -> {v}")
