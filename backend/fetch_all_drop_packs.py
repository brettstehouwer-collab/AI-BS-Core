import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://cymatics.fm/products.json?limit=250', headers=headers)
data = r.json()
products = data.get('products', [])
print(f'Total products fetched: {len(products)}')

drop_packs = []
for p in products:
    for v in p['variants']:
        price = v['price']
        title = p['title']
        if price == '0.00' or any(k in title.lower() for k in ['trinity', 'percussion', 'mystery', 'anniversary', 'destiny', 'evolution', 'ripple', 'boom', 'phalanx', 'midi']):
            drop_packs.append({
                'title': title,
                'handle': p['handle'],
                'price': price,
                'variant_id': v['id'],
                'direct_checkout': f"https://cymatics.fm/cart/{v['id']}:1?checkout"
            })

print(f'Found {len(drop_packs)} matching free/drop packs:')
for dp in drop_packs:
    print(f" - {dp['title']} (${dp['price']}) -> Variant: {dp['variant_id']}")
    print(f"   Checkout: {dp['direct_checkout']}")

with open('C:/AI-BS/saved_data/cymatics_discovered_free_drops.json', 'w', encoding='utf-8') as f:
    json.dump(drop_packs, f, indent=2)
