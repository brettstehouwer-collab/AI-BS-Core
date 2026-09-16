import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# 1. Fetch all pages of products.json to find every $0.00 product / bundle
all_free_items = []
page = 1
while True:
    url = f"https://cymatics.fm/products.json?limit=250&page={page}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        break
    data = r.json()
    products = data.get('products', [])
    if not products:
        break
    for p in products:
        for v in p.get('variants', []):
            if v.get('price') in ['0.00', 0, '0'] and v.get('available'):
                all_free_items.append({
                    'title': p.get('title'),
                    'handle': p.get('handle'),
                    'variant_id': v.get('id'),
                    'price': v.get('price'),
                    'created_at': p.get('created_at'),
                    'updated_at': p.get('updated_at')
                })
    if len(products) < 250:
        break
    page += 1

print(f"Total available $0.00 free items found across all products: {len(all_free_items)}")

# Find specific Anniversary / Mystery / Full Bundles
anniversary_bundles = [it for it in all_free_items if any(k in it['title'].lower() for k in ['anniversary', 'mystery', 'bundle', 'suite', 'collection', 'exodus'])]

print("\n--- Key Free Bundles & Anniversary Packs ---")
for b in anniversary_bundles:
    print(f"Title: {b['title']}")
    print(f"  Handle: https://cymatics.fm/products/{b['handle']}")
    print(f"  1-Click Checkout: https://cymatics.fm/cart/{b['variant_id']}:1?checkout\n")

# Construct multi-item combined cart URLs
# Top 20 stream freebies in a single link:
recent_free_variants = [str(it['variant_id']) for it in all_free_items[:25]]
combined_url = f"https://cymatics.fm/cart/{','.join([f'{vid}:1' for vid in recent_free_variants])}?checkout"
print(f"--- COMBINED 25-ITEM 1-CLICK FREE MEGA BUNDLE URL ---")
print(combined_url)
