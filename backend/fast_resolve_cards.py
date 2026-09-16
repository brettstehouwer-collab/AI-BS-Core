import requests
import bs4
import re
import json
from concurrent.futures import ThreadPoolExecutor

r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
soup = bs4.BeautifulSoup(r.text, 'html.parser')
cards = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and 'dl-card' in tag['class'] and 'dl-card-grid' not in tag['class'])

print(f"Total Cards on Drop Page: {len(cards)}")

card_titles = []
for c in cards:
    img = c.find('img')
    alt = img.get('alt', '').strip() if img else ''
    if alt and 'discount' not in alt.lower() and alt not in card_titles:
        card_titles.append(alt)

print(f"Unique Titles to Resolve: {len(card_titles)}")

def check_card(title):
    handle = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    try:
        r_p = requests.get(f'https://cymatics.fm/products/{handle}.json', headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if r_p.status_code == 200:
            prod = r_p.json().get('product', {})
            t = prod.get('title', title)
            matched_variants = []
            for v in prod.get('variants', []):
                matched_variants.append({
                    'title': t,
                    'handle': handle,
                    'price': v.get('price'),
                    'variant_id': v.get('id'),
                    'available': v.get('available')
                })
            return matched_variants
    except Exception:
        pass
    return []

results = []
with ThreadPoolExecutor(max_workers=20) as executor:
    for res in executor.map(check_card, card_titles):
        if res:
            results.extend(res)

print(f"\n=======================================================")
print(f"  RESOLVED DIRECT PRODUCTS & VARIANTS ({len(results)} Total)")
print(f"=======================================================")

free_variants = [item for item in results if item['price'] == '0.00']
paid_variants = [item for item in results if item['price'] != '0.00']

print(f"\n--- FREE ($0.00) DIRECT CLAIMS ({len(free_variants)}): ---")
for item in free_variants:
    print(f"  • {item['title']} -> Variant ID: {item['variant_id']} | Available: {item['available']} | https://cymatics.fm/cart/{item['variant_id']}:1?checkout")

print(f"\n--- PAID / SPECIAL VARIANTS ({len(paid_variants)}): ---")
for item in paid_variants:
    print(f"  • {item['title']} (${item['price']}) -> Variant ID: {item['variant_id']} | Available: {item['available']}")
