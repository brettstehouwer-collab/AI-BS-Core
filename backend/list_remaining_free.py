import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('C:/AI-BS/saved_data/cymatics_discovered_free_drops.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total Free Discovered Items: {len(items)}")
for it in items:
    title = it.get('title', '')
    link = it.get('direct_checkout', '')
    print(f" - {title}: {link}")
