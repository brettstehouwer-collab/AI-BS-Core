import sys
import requests
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

url = "https://cymatics.fm/products.json?limit=250"
r = requests.get(url, headers=headers)

if r.status_code == 200:
    products = r.json().get('products', [])
    print(f"Total products fetched from page 1: {len(products)}")
    
    # Sort by updated_at or created_at descending
    products.sort(key=lambda p: p.get('updated_at', ''), reverse=True)
    
    print("\nMost Recently Updated Products on Shopify:")
    for p in products[:15]:
        title = p.get('title')
        updated = p.get('updated_at')
        created = p.get('created_at')
        handle = p.get('handle')
        variants = p.get('variants', [])
        price = variants[0].get('price') if variants else 'N/A'
        var_id = variants[0].get('id') if variants else 'N/A'
        available = variants[0].get('available') if variants else False
        
        print(f"[{updated[:19]}] {title:<40} | Price: ${price} | Avail: {available} | Variant: {var_id} | Handle: {handle}")
else:
    print(f"Failed to fetch products.json: {r.status_code}")
