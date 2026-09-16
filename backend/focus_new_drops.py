import requests
import json
from datetime import datetime, timezone
import sys

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Cache-Control': 'no-cache'}

r = requests.get('https://cymatics.fm/products.json?limit=250', headers=headers)
if r.status_code == 200:
    products = r.json().get('products', [])
    free_items = []
    for p in products:
        for v in p.get('variants', []):
            if str(v.get('price')) in ['0.00', '0'] and v.get('available'):
                free_items.append({
                    'title': p.get('title'),
                    'variant_title': v.get('title'),
                    'id': v.get('id'),
                    'updated_at': p.get('updated_at'),
                    'created_at': p.get('created_at')
                })

    # Sort by updated_at descending
    free_items.sort(key=lambda x: x['updated_at'], reverse=True)

    print(f"Total Available $0.00 Free Products: {len(free_items)}")
    print("\n--- TOP 15 NEWEST / MOST RECENTLY UPDATED FREE DROPS ---")
    for idx, item in enumerate(free_items[:15], 1):
        print(f"{idx}. {item['title']} (Variant ID: {item['id']})")
        print(f"   Updated: {item['updated_at']}")
        print(f"   Direct Claim: https://cymatics.fm/cart/{item['id']}:1?checkout\n")
