import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json

headers = {'User-Agent': 'Mozilla/5.0'}

target_assets = [
    "Trinity - Wet Percussion",
    "Comet - Drum Loops",
    "Duality - Vintage Melodies",
    "Duality - Ambient Melodies",
    "Dream Cassette Plugin",
    "Chili Clip",
    "DRUMPOD",
    "Mystery 11 Year Anniversary",
    "PANDORA Plugin",
    "QUAKE - Bass Engine",
    "Pulse Plugin",
    "TITAN Production Suite"
]

results = []

for asset in target_assets:
    # 1. Search via suggest API
    query_url = f"https://cymatics.fm/search/suggest.json?q={requests.utils.quote(asset)}&resources[type]=product"
    try:
        r = requests.get(query_url, headers=headers, timeout=5)
        found = False
        if r.status_code == 200:
            data = r.json()
            products = data.get('resources', {}).get('results', {}).get('products', [])
            for p in products:
                handle = p.get('handle', '')
                p_id = p.get('id')
                
                # Fetch full product json for variants
                pr = requests.get(f"https://cymatics.fm/products/{handle}.json", headers=headers, timeout=5)
                if pr.status_code == 200:
                    p_data = pr.json().get('product', {})
                    for v in p_data.get('variants', []):
                        results.append({
                            "target": asset,
                            "matched_title": p_data.get('title'),
                            "handle": handle,
                            "variant_id": v.get('id'),
                            "price": v.get('price'),
                            "direct_checkout": f"https://cymatics.fm/cart/{v.get('id')}:1?checkout"
                        })
                        found = True
        if not found:
            # Try handle direct guess
            clean_handle = asset.lower().replace(' - ', '-').replace(' ', '-').replace('plugin', '').strip('-')
            pr = requests.get(f"https://cymatics.fm/products/{clean_handle}.json", headers=headers, timeout=5)
            if pr.status_code == 200:
                p_data = pr.json().get('product', {})
                for v in p_data.get('variants', []):
                    results.append({
                        "target": asset,
                        "matched_title": p_data.get('title'),
                        "handle": clean_handle,
                        "variant_id": v.get('id'),
                        "price": v.get('price'),
                        "direct_checkout": f"https://cymatics.fm/cart/{v.get('id')}:1?checkout"
                    })
                    found = True
            if not found:
                results.append({
                    "target": asset,
                    "matched_title": "Not Yet Published in Store Index",
                    "handle": None,
                    "variant_id": None,
                    "price": None,
                    "direct_checkout": None
                })
    except Exception as e:
        results.append({
            "target": asset,
            "error": str(e)
        })

print(json.dumps(results, indent=2))
with open("C:/AI-BS/saved_data/cymatics_12_assets_sweep.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
