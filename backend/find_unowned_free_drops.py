import os
import json
import re

free_drops_file = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"
output_unowned_file = r"C:\AI-BS\saved_data\cymatics_unowned_free_drops.json"

# Collect all owned assets across ALL directories
owned_tokens = set()

# 1. E:\ drive
if os.path.exists("E:\\"):
    for item in os.listdir("E:\\"):
        clean = re.sub(r'[^a-zA-Z0-9]', ' ', item.lower())
        for token in clean.split():
            if len(token) > 3 and token not in ['cymatics', 'steven', 'pack', 'collection', 'sample', 'samples']:
                owned_tokens.add(token)
        owned_tokens.add(clean.strip())

# 2. C:\AI-BS\shared_cloud_drive\4 media
media_dir = r"C:\AI-BS\shared_cloud_drive\4 media"
if os.path.exists(media_dir):
    for root, dirs, files in os.walk(media_dir):
        for d in dirs:
            owned_tokens.add(d.lower().strip())
        for f in files:
            owned_tokens.add(f.lower().strip())

# 3. Cymatics Hub
hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
for jf in ["installed.json", "pack-folders.json"]:
    jp = os.path.join(hub_dir, jf)
    if os.path.exists(jp):
        try:
            data = json.load(open(jp, "r", encoding="utf-8"))
            for k in data.keys():
                owned_tokens.add(k.lower().strip())
        except:
            pass

# 4. VST3 plugins
vst3_dir = r"C:\Program Files\Common Files\VST3"
if os.path.exists(vst3_dir):
    for root, dirs, files in os.walk(vst3_dir):
        for f in files:
            owned_tokens.add(f.lower().replace('.vst3', '').strip())

# 5. Downloads folder
dl_dir = r"C:\Users\footb\Downloads"
if os.path.exists(dl_dir):
    for f in os.listdir(dl_dir):
        owned_tokens.add(f.lower().strip())

# Load all free catalog items
free_items = []
if os.path.exists(free_drops_file):
    free_items = json.load(open(free_drops_file, "r", encoding="utf-8"))

unowned_free = []
seen_variants = set()

def is_item_owned(title):
    t_clean = re.sub(r'[^a-zA-Z0-9]', ' ', title.lower()).strip()
    words = [w for w in t_clean.split() if len(w) > 3 and w not in ['cymatics', 'steven', 'pack', 'collection', 'sample', 'samples', 'type', 'free', 'edition', 'vault']]
    
    # Check direct match
    for o in owned_tokens:
        if t_clean in o or o in t_clean:
            return True
            
    # Check significant word matches
    if words:
        for o in owned_tokens:
            if all(w in o for w in words):
                return True
    return False

for item in free_items:
    vid = str(item.get("variant_id"))
    if vid in seen_variants:
        continue
    seen_variants.add(vid)
    
    title = item.get("title", "")
    price = str(item.get("price", "0.00"))
    
    if price not in ["0.00", "0", "$0.00"]:
        continue
        
    if not is_item_owned(title):
        checkout_link = f"https://cymatics.fm/cart/{vid}:1?checkout"
        unowned_free.append({
            "title": title,
            "variant_id": vid,
            "price": "$0.00 FREE",
            "checkout_url": checkout_link
        })

# Save unowned free drops
with open(output_unowned_file, "w", encoding="utf-8") as f:
    json.dump(unowned_free, f, indent=2)

print(f"Total Completely Unowned $0.00 Free Drops: {len(unowned_free)}")
for u in unowned_free[:30]:
    print(f"  -> [{u['title']}] : {u['checkout_url']}")
