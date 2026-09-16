import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json

headers = {'User-Agent': 'Mozilla/5.0'}
targets = [
    'Trinity - Wet Percussion', 'Comet - Drum Loops', 'Duality - Vintage Melodies',
    'Duality - Ambient Melodies', 'Dream Cassette', 'Chili Clip', 'DRUMPOD',
    'Mystery 11 Year Anniversary', 'PANDORA', 'QUAKE', 'Pulse', 'TITAN'
]

print(f'Checking {len(targets)} targets against Shopify API...')
findings = []

for t in targets:
    url = f'https://cymatics.fm/search/suggest.json?q={requests.utils.quote(t)}&resources[type]=product'
    try:
        r = requests.get(url, headers=headers, timeout=3)
        res = r.json().get('resources', {}).get('results', {}).get('products', [])
        found_matches = []
        for p in res:
            handle = p.get('handle', '')
            p_id = p.get('id')
            title = p.get('title', '')
            
            # Fetch variant ID
            vr = requests.get(f'https://cymatics.fm/products/{handle}.json', headers=headers, timeout=3)
            v_id = None
            price = "0.00"
            if vr.status_code == 200:
                var_list = vr.json().get('product', {}).get('variants', [])
                if var_list:
                    v_id = var_list[0].get('id')
                    price = var_list[0].get('price', '0.00')
            
            found_matches.append({
                "title": title,
                "handle": handle,
                "product_id": p_id,
                "variant_id": v_id,
                "price": price,
                "checkout_link": f"https://cymatics.fm/cart/{v_id}:1?checkout" if v_id else None
            })
            
        findings.append({
            "query": t,
            "count": len(found_matches),
            "matches": found_matches
        })
    except Exception as e:
        findings.append({
            "query": t,
            "error": str(e)
        })

print(json.dumps(findings, indent=2))
with open("C:/AI-BS/saved_data/cymatics_12_assets_sweep.json", "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)
