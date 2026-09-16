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

# 1. Audit dl-cards on drop page
r_page = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r_page.text, 'html.parser')
cards = soup.select('.dl-card')
unlocked = []
for c in cards:
    classes = c.get('class', [])
    if 'dl-card--locked' not in classes and 'locked' not in ' '.join(classes).lower():
        num = c.get('data-card-num', 'unknown')
        img = c.find('img')
        title = (img.get('alt') if img else '') or f"Card #{num}"
        cta = c.find('a') or c.find('button')
        vid = c.get('data-variant-id') or (cta.get('data-variant-id') if cta else '')
        link = cta.get('href', '') if cta else ''
        unlocked.append({'num': num, 'title': title, 'vid': vid, 'link': link})

print(f"Unlocked Cards on cymatics-c86v: {len(unlocked)}")
for u in unlocked:
    print(f"  -> Card #{u['num']}: {u['title']} | Variant: {u['vid']} | Link: {u['link']}")

# 2. Check Shopify products feed for active plugins
r_shop = requests.get('https://cymatics.fm/products.json?limit=50', headers=headers)
if r_shop.status_code == 200:
    products = r_shop.json().get('products', [])
    plugin_products = []
    for p in products:
        title = p.get('title', '')
        handle = p.get('handle', '')
        if any(w in (title + handle).lower() for w in ['plugin', 'engine', 'shifter', 'nc-73', 'phantom', 'corrosion', 'plinko', 'chili', '8bit', 'drumpod', 'occular', 'hooklab', 'origin', 'space', 'lotus', 'vortex', 'aurora', 'prism', 'pulse', 'memory']):
            plugin_products.append(p)
            
    print(f"\nDiscovered {len(plugin_products)} active plugin products in store feed:")
    for p in plugin_products:
        variants = p.get('variants', [])
        for v in variants:
            price = v.get('price')
            vid = v.get('id')
            avail = v.get('available')
            cart_url = f"https://cymatics.fm/cart/{vid}:1?checkout"
            print(f"  - {p.get('title')} ({v.get('title')}) | Price: ${price} | Available: {avail} | ID: {vid} | Cart: {cart_url}")
