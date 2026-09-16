import json
import re

with open(r'C:\AI-BS\saved_data\cymatics_discovered_free_drops.json', 'r', encoding='utf-8') as f:
    discovered = json.load(f)

with open(r'C:\AI-BS\backend\aibs_cymatics_sniper.py', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'ALREADY_OWNED = \{([^}]+)\}', content)
owned = set()
if match:
    for line in match.group(1).split(','):
        t = line.strip().strip('"').strip("'").lower()
        if t:
            owned.add(t)

unclaimed = []
for item in discovered:
    t = item['title'].lower().strip()
    if not any(o in t or t in o for o in owned):
        unclaimed.append(item)

print(f"Total Discovered Free/Drop Items: {len(discovered)}")
print(f"Total Configured Exclusions: {len(owned)}")
print(f"Unclaimed Free Items Count: {len(unclaimed)}")
print("\n--- NEXT 15 UNCLAIMED FREE DROPS & DIRECT CHECKOUT LINKS ---")
for u in unclaimed[:15]:
    print(f"  • {u['title']:<40} | ID: {u['variant_id']} | Link: {u['direct_checkout']}")
