import json
import os
import re

audit_file = r"C:\AI-BS\saved_data\drop_page_all_cards_audit.json"
data = json.load(open(audit_file, "r", encoding="utf-8"))

free_matched = data.get("free_matched_cards", [])

# Collect owned tokens across all disk directories
owned_tokens = set()

if os.path.exists("E:\\"):
    for item in os.listdir("E:\\"):
        clean = re.sub(r'[^a-zA-Z0-9]', ' ', item.lower())
        for token in clean.split():
            if len(token) > 3 and token not in ['cymatics', 'steven', 'pack', 'collection', 'sample', 'samples']:
                owned_tokens.add(token)
        owned_tokens.add(clean.strip())

hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
for jf in ["installed.json", "pack-folders.json"]:
    jp = os.path.join(hub_dir, jf)
    if os.path.exists(jp):
        try:
            d = json.load(open(jp, "r", encoding="utf-8"))
            for k in d.keys():
                owned_tokens.add(k.lower().strip())
        except:
            pass

vst3_dir = r"C:\Program Files\Common Files\VST3"
if os.path.exists(vst3_dir):
    for root, dirs, files in os.walk(vst3_dir):
        for f in files:
            owned_tokens.add(f.lower().replace('.vst3', '').strip())

def is_owned(title):
    t_clean = re.sub(r'[^a-zA-Z0-9]', ' ', title.lower()).strip()
    words = [w for w in t_clean.split() if len(w) > 3 and w not in ['cymatics', 'steven', 'pack', 'collection', 'sample', 'samples', 'type', 'free', 'edition', 'vault', 'premium']]
    
    for o in owned_tokens:
        if t_clean in o or o in t_clean:
            return True
            
    if words:
        for o in owned_tokens:
            if all(w in o for w in words):
                return True
    return False

unowned_cards_to_grab = []
seen_variants = set()

for c in free_matched:
    vid = str(c.get("matched_variant_id"))
    if vid in seen_variants:
        continue
    seen_variants.add(vid)
    
    t = c.get("title", "")
    if not is_owned(t):
        unowned_cards_to_grab.append({
            "card_num": c.get("card_num"),
            "title": t,
            "variant_id": vid,
            "checkout_url": c.get("checkout_url")
        })

print(f"Total Free Cards on Drop Page Resolved: {len(free_matched)}")
print(f"Total Unowned Free Cards Ready to Grab: {len(unowned_cards_to_grab)}")
print("\n--- UNOWNED FREE CARDS READY TO GRAB ---")
for idx, uc in enumerate(unowned_cards_to_grab, 1):
    print(f"{idx}. [{uc['title']}] (Card #{uc['card_num']}) -> {uc['checkout_url']}")
