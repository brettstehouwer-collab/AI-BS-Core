import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup
import json, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

# 1. Fetch live drop page
print("Fetching live drop page https://cymatics.fm/pages/cymatics-c86v...")
r = requests.get("https://cymatics.fm/pages/cymatics-c86v", headers=headers, timeout=8)
soup = BeautifulSoup(r.text, 'html.parser')

# Extract embedded JSON data from script tags
embedded_json = {}
for script in soup.find_all('script'):
    content = script.string or ""
    if "TriplePixelData" in content or "Shopify" in content or "LW_TYPES" in content or "GSC_COUNTDOWN" in content:
        # Extract json-like structures
        json_matches = re.findall(r'(\b[a-zA-Z0-9_]+\s*=\s*\{.*?\});', content, re.DOTALL)
        for jm in json_matches:
            k = jm.split('=')[0].strip()
            embedded_json[k] = jm[:300]

# 2. Fetch products.json
print("Fetching https://cymatics.fm/products.json?limit=250...")
pr = requests.get("https://cymatics.fm/products.json?limit=250", headers=headers, timeout=8)
products_data = pr.json().get('products', []) if pr.status_code == 200 else []

live_freebies = []
for p in products_data:
    for v in p.get('variants', []):
        if v.get('price') == '0.00':
            live_freebies.append({
                "title": p.get('title'),
                "handle": p.get('handle'),
                "id": p.get('id'),
                "variant_id": v.get('id'),
                "price": v.get('price'),
                "checkout_url": f"https://cymatics.fm/cart/{v.get('id')}:1?checkout"
            })

report = {
    "status": "SUCCESS",
    "timestamp": "2026-08-27 23:10:00",
    "total_products_scanned": len(products_data),
    "total_zero_cost_assets_active": len(live_freebies),
    "zero_cost_assets": live_freebies,
    "page_cards_count": len(soup.find_all(class_=lambda c: c and 'dl-card' in c)),
    "embedded_scripts_found": len(embedded_json)
}

with open("C:/AI-BS/saved_data/cymatics_full_dom_json_extraction.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print(f"\n=======================================================")
print(f"  DOM-LEVEL EXTRACTION COMPLETE")
print(f"  Total Products In Store: {len(products_data)}")
print(f"  Active Free ($0.00) Assets: {len(live_freebies)}")
print(f"  Cards In Drop Page DOM: {report['page_cards_count']}")
print(f"=======================================================")
for f in live_freebies[:15]:
    print(f" -> {f['title']} (Variant: {f['variant_id']}) -> {f['checkout_url']}")
