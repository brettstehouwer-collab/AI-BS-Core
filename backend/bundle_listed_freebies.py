import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\AI-BS\saved_data\cymatics_discovered_free_drops.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

targets = [
    '2023 - 808 Collection', 'Amber', 'Winter',
    'PHANTOM', 'CORROSION', 'NC-73', 'PLINKO', 'Casino', 'Daydream',
    'Trinity - Wet Percussion', 'Duality - Vintage Melodies', 'BOOM', 'Whisper',
    'Cascade', 'Comet', 'HORIZON', 'Destiny',
    'Octagon', 'Phalanx', 'Trinity - MIDI', 'Duality - Ambient Melodies',
    'SHIFTER', 'EXODUS', 'Evolution',
    'Ripple'
]

found = []
seen_ids = set()

for t in targets:
    for p in catalog:
        title = p.get('title', '')
        vid = p.get('variant_id')
        if t.lower() in title.lower() and vid and vid not in seen_ids:
            seen_ids.add(vid)
            found.append(p)

print(f"Matched {len(found)} matching free products from inventory:")
for item in found:
    print(f"- {item.get('title')}: https://cymatics.fm/cart/{item.get('variant_id')}:1?checkout")

vids = [str(item.get('variant_id')) for item in found]
if vids:
    bundle_url = f"https://cymatics.fm/cart/{','.join([f'{v}:1' for v in vids])}?checkout"
    print("\n" + "="*80)
    print(f"📦 MASTER COMBINED 1-CLICK BUNDLE URL ({len(vids)} Items at $0.00):")
    print(bundle_url)
    print("="*80)
