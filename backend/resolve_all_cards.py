import requests
import bs4
import re
import json

r = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers={'User-Agent': 'Mozilla/5.0'})
soup = bs4.BeautifulSoup(r.text, 'html.parser')
cards = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and 'dl-card' in tag['class'] and 'dl-card-grid' not in tag['class'])

print(f"Checking {len(cards)} drop cards against store catalog...")
results = []
for c in cards:
    img = c.find('img')
    alt = img.get('alt', '').strip() if img else ''
    if not alt or 'discount' in alt.lower():
        continue
    handle = re.sub(r'[^a-z0-9]+', '-', alt.lower()).strip('-')
    try:
        r_p = requests.get(f'https://cymatics.fm/products/{handle}.json', headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        if r_p.status_code == 200:
            prod = r_p.json().get('product', {})
            title = prod.get('title', alt)
            for v in prod.get('variants', []):
                results.append({
                    'title': title,
                    'handle': handle,
                    'price': v.get('price'),
                    'variant_id': v.get('id'),
                    'available': v.get('available')
                })
    except Exception:
        pass

print(f"\nFound {len(results)} matching live product entries:")
for item in results:
    print(f"  • {item['title']} (${item['price']}) -> Variant: {item['variant_id']} | Available: {item['available']} | URL: https://cymatics.fm/cart/{item['variant_id']}:1?checkout")
