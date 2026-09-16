import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

handles = [
    'chili-clip-max', 
    'mystery-11-year-anniversary-gold-edition', 
    'drumpod-max', 
    'occular-max', 
    'daydream-max', 
    'prism-max', 
    'radar-max', 
    'dream-cassette-max', 
    'hotline-max',
    'chili-clip',
    'dream-cassette',
    'drumpod-lite',
    'daydream-lite',
    'pandora-plugin',
    'exodus-various-drums',
    'exodus-various-melodies'
]

print("=== CHECKING ACCURATE PRICES ON SHOPIFY ===")
for h in handles:
    r = requests.get(f"https://cymatics.fm/products/{h}.json", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    if r.status_code == 200:
        prod = r.json().get("product", {})
        t = prod.get("title", "")
        for v in prod.get("variants", []):
            p = v.get("price", "0.00")
            print(f" -> {t:<45} | Price: ${p} | Variant: {v.get('id')}")
