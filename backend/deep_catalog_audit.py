import requests
from bs4 import BeautifulSoup
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

print("=== 1. AUDITING DROP GRID (cymatics-c86v) ===")
r_page = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
if r_page.status_code == 200:
    soup = BeautifulSoup(r_page.text, 'html.parser')
    cards = soup.select('.dl-card[data-card-num]')
    unlocked = [c for c in cards if 'dl-card--locked' not in c.get('class', [])]
    print(f"Total Cards: {len(cards)} | Unlocked on Page: {len(unlocked)}")

print("\n=== 2. AUDITING LIVE SHOPIFY STORE CATALOG (250 items) ===")
r_shop = requests.get('https://cymatics.fm/products.json?limit=250', headers=headers)
if r_shop.status_code == 200:
    products = r_shop.json().get('products', [])
    free_items = []
    for p in products:
        for v in p.get('variants', []):
            if str(v.get('price')) in ['0.00', '0'] and v.get('available'):
                free_items.append({
                    'title': p.get('title'),
                    'variant_title': v.get('title'),
                    'id': v.get('id'),
                    'updated_at': p.get('updated_at')
                })
    print(f"Total Active $0.00 Products in Catalog: {len(free_items)}")
    print("\n12 Most Recently Updated Free Drops:")
    for item in free_items[:12]:
        print(f"  - {item['title']} (ID: {item['id']}) | Updated: {item['updated_at']}")
        print(f"    -> Cart: https://cymatics.fm/cart/{item['id']}:1?checkout")
