import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

targets = [
    'dope-collection-melodies',
    'dope-collection-drums',
    'dope-collection-vocals',
    'dope-collection-bonus-stash',
    'solace-acapellas',
    'euphoria-vocal-chops',
    'sessions-guitar',
    'magic-hip-hop-drum-kit'
]

print("=== RESOLVED DIRECT $0 CLAIM URLS FOR NEW LOCKED BATCH ===")
for t in targets:
    r = requests.get(f"https://cymatics.fm/products/{t}.json", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    if r.status_code == 200:
        prod = r.json().get("product", {})
        title = prod.get("title", "")
        for v in prod.get("variants", []):
            if v.get("price") == "0.00":
                vid = v.get("id")
                print(f" -> {title:<35} | Variant: {vid} | URL: https://cymatics.fm/cart/{vid}:1?checkout")
