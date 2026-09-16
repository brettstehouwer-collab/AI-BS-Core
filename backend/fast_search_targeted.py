import os

search_targets = [
    ("Dream Cassette", ["dream", "cassette"]),
    ("VIBES Premium Collection", ["vibes"]),
    ("DAWGS Hip Hop Sample Pack", ["dawgs"]),
    ("Artifact Foley Collection", ["artifact", "foley"]),
    ("NC-73 Preset Bank", ["nc-73", "nc73"]),
    ("EQC1A Preset Bank", ["eqc1a", "eqc-1a", "eqc 1a"])
]

e_folders = [f for f in os.listdir("E:\\")] if os.path.exists("E:\\") else []
media_folders = []
media_path = r"C:\AI-BS\shared_cloud_drive\4 media"
if os.path.exists(media_path):
    for root, dirs, files in os.walk(media_path):
        media_folders.extend(dirs)
        media_folders.extend(files)

vst_folders = os.listdir(r"C:\Program Files\Common Files\VST3") if os.path.exists(r"C:\Program Files\Common Files\VST3") else []
progdata_folders = os.listdir(r"C:\ProgramData\Cymatics") if os.path.exists(r"C:\ProgramData\Cymatics") else []
downloads_folders = os.listdir(r"C:\Users\footb\Downloads") if os.path.exists(r"C:\Users\footb\Downloads") else []

all_entries = e_folders + media_folders + vst_folders + progdata_folders + downloads_folders

print("=== FAST TARGETED SEARCH RESULTS ===")
for target_name, kws in search_targets:
    matches = []
    for entry in all_entries:
        entry_lower = entry.lower()
        if all(k in entry_lower for k in kws):
            matches.append(entry)
    
    unique_matches = list(set(matches))
    if unique_matches:
        print(f"[FOUND] {target_name} -> Matches: {unique_matches}")
    else:
        print(f"[NOT FOUND] {target_name} -> 0 matches in audio/media repositories")
