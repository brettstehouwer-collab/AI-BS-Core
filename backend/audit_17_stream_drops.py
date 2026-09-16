import json
import os

items_to_check = [
    ("DOPE Collection - Melodies", "42703045132373", "https://cymatics.fm/cart/42703045132373:1?checkout"),
    ("DOPE Collection - Drums", "42703113420885", "https://cymatics.fm/cart/42703113420885:1?checkout"),
    ("DOPE Collection - Vocals", "42703162277973", "https://cymatics.fm/cart/42703162277973:1?checkout"),
    ("DOPE Collection - Bonus Stash", "42703163228245", "https://cymatics.fm/cart/42703163228245:1?checkout"),
    ("Solace - Acapellas", "42703166439509", "https://cymatics.fm/cart/42703166439509:1?checkout"),
    ("Daydream - Vocal Loops", "42703168700501", "https://cymatics.fm/cart/42703168700501:1?checkout"),
    ("Euphoria - Vocal Chops", "42703179022421", "https://cymatics.fm/cart/42703179022421:1?checkout"),
    ("SESSIONS: Melody Compositions", "40635706343509", "https://cymatics.fm/cart/40635706343509:1?checkout"),
    ("Generations - 1970s Samples", "40620833570901", "https://cymatics.fm/cart/40620833570901:1?checkout"),
    ("Generations - 1960s Samples", "40620731498581", "https://cymatics.fm/cart/40620731498581:1?checkout"),
    ("Kingdom: Electronic MIDI", "40666743111765", "https://cymatics.fm/cart/40666743111765:1?checkout"),
    ("Pandora - EDM MIDI", "42703201370197", "https://cymatics.fm/cart/42703201370197:1?checkout"),
    ("Pandora - RnB MIDI", "42703204712533", "https://cymatics.fm/cart/42703204712533:1?checkout"),
    ("Pandora - Trap MIDI", "42703211626581", "https://cymatics.fm/cart/42703211626581:1?checkout"),
    ("Pandora: Paradise Expansion", "42703223881813", "https://cymatics.fm/cart/42703223881813:1?checkout"),
    ("Pandora: Echoes Expansion", "42703249342549", "https://cymatics.fm/cart/42703249342549:1?checkout"),
    ("MIDI Shredder", "42520328962133", "https://cymatics.fm/cart/42520328962133:1?checkout")
]

hub_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"
pack_folders = {}
if os.path.exists(os.path.join(hub_dir, "pack-folders.json")):
    with open(os.path.join(hub_dir, "pack-folders.json"), "r", encoding="utf-8") as f:
        pack_folders = json.load(f)

installed_plugins = {}
if os.path.exists(os.path.join(hub_dir, "installed.json")):
    with open(os.path.join(hub_dir, "installed.json"), "r", encoding="utf-8") as f:
        installed_plugins = json.load(f)

print("Total Hub Installed Plugins:", len(installed_plugins))
print("Total Hub Sample Packs:", len(pack_folders))

print("\n--- INDIVIDUAL AUDIT OF 17 STREAM DROPS ---")
downloaded = []
pending = []

for title, var_id, url in items_to_check:
    title_clean = title.lower().replace(":", "").replace("-", " ").strip()
    is_installed = False
    match_detail = ""

    # 1. Check plugins
    for p_k in installed_plugins.keys():
        if p_k.lower().replace("-", " ") in title_clean or title_clean in p_k.lower().replace("-", " "):
            is_installed = True
            match_detail = f"Installed Plugin VST3: {p_k}"
            break

    # 2. Check sample pack folders
    if not is_installed:
        for p_k, p_v in pack_folders.items():
            folder_name = p_v.get("folder_name", p_k).lower()
            # check exact keywords
            if "dope" in title_clean and "dope" in folder_name:
                if "melod" in title_clean and "melod" in folder_name:
                    is_installed = True; match_detail = folder_name; break
                elif "drum" in title_clean and "drum" in folder_name:
                    is_installed = True; match_detail = folder_name; break
                elif "vocal" in title_clean and "vocal" in folder_name:
                    is_installed = True; match_detail = folder_name; break
                elif "stash" in title_clean and "stash" in folder_name:
                    is_installed = True; match_detail = folder_name; break
            elif "daydream" in title_clean and "daydream" in folder_name:
                is_installed = True; match_detail = folder_name; break
            elif "solace" in title_clean and "solace" in folder_name:
                is_installed = True; match_detail = folder_name; break
            elif "euphoria" in title_clean and "euphoria" in folder_name:
                is_installed = True; match_detail = folder_name; break

    if is_installed:
        downloaded.append((title, var_id, match_detail))
    else:
        pending.append((title, var_id, url))

print(f"\n[DOWNLOADED IN HUB]: {len(downloaded)} / 17")
for t, v, m in downloaded:
    print(f"  [CHECKED OFF] {t} (Variant: {v}) -> {m}")

print(f"\n[PENDING UNCLAIMED]: {len(pending)} / 17")
for t, v, u in pending:
    print(f"  [CLAIM LINK]  {t} (Variant: {v}) -> {u}")
