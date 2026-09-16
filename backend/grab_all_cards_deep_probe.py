import requests
from bs4 import BeautifulSoup
import json
import re

# 1. Fetch drop page HTML
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

r_dom = requests.get('https://cymatics.fm/pages/cymatics-c86v', headers=headers)
soup = BeautifulSoup(r_dom.text, 'html.parser')

cards = soup.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and 'dl-card' in tag['class'] and 'dl-card-grid' not in tag['class'])
print(f"Total Cards on Drop Page DOM: {len(cards)}")

# Extract card details
card_entries = []
for idx, c in enumerate(cards):
    classes = c.get('class', [])
    is_locked = any('locked' in cls.lower() for cls in classes)
    card_num = c.get('data-card-num', str(idx + 1))
    
    img = c.find('img')
    img_alt = img.get('alt', '').strip() if img else ''
    img_src = img.get('src', '') if img else ''
    
    btn = c.find(['button', 'a'])
    btn_text = btn.get_text(strip=True) if btn else ''
    variant_id = btn.get('data-variant-id') or btn.get('data-id') if btn else None
    href = btn.get('href', '') if btn else ''
    
    card_entries.append({
        "index": idx + 1,
        "card_num": card_num,
        "title": img_alt or f"Card #{idx+1}",
        "is_locked": is_locked,
        "variant_id": variant_id,
        "href": href,
        "btn_text": btn_text,
        "img_src": img_src
    })

# 2. Fetch full store catalog
print("Fetching full Cymatics Shopify product catalog...")
catalog = {}
page = 1
while page <= 5:
    r_cat = requests.get(f'https://cymatics.fm/products.json?limit=250&page={page}', headers=headers)
    if r_cat.status_code != 200:
        break
    prods = r_cat.json().get('products', [])
    if not prods:
        break
    for p in prods:
        title = p.get('title', '').strip()
        handle = p.get('handle', '')
        for v in p.get('variants', []):
            vid = str(v.get('id'))
            price = str(v.get('price', '0.00'))
            catalog[title.lower()] = {
                "title": title,
                "variant_id": vid,
                "price": price,
                "handle": handle,
                "direct_checkout": f"https://cymatics.fm/cart/{vid}:1?checkout"
            }
    page += 1

print(f"Total Products in Catalog: {len(catalog)}")

# 3. Match cards against store catalog
matched_cards = []
for c in card_entries:
    t = c['title'].lower()
    match = None
    
    # Direct match
    if t in catalog:
        match = catalog[t]
    else:
        # Partial match
        for cat_k, cat_v in catalog.items():
            if len(t) > 3 and (t in cat_k or cat_k in t):
                match = cat_v
                break
                
    if match:
        c['matched_variant_id'] = match['variant_id']
        c['matched_price'] = match['price']
        c['checkout_url'] = match['direct_checkout']
        matched_cards.append(c)

print(f"\nTotal Cards Matched to Catalog: {len(matched_cards)}")

free_matched = [m for m in matched_cards if m.get('matched_price') in ['0.00', '0']]
print(f"Total Free ($0.00) Matched Cards: {len(free_matched)}")

output_file = r"C:\AI-BS\saved_data\drop_page_all_cards_audit.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "total_cards": len(card_entries),
        "card_entries": card_entries,
        "matched_cards": matched_cards,
        "free_matched_cards": free_matched
    }, f, indent=2)

print(f"Audit saved to {output_file}")
