import os
import re

search_targets = [
    ("Dream Cassette", ["dream", "cassette"]),
    ("VIBES Premium Collection", ["vibes"]),
    ("DAWGS Hip Hop Sample Pack", ["dawgs"]),
    ("Artifact Foley Collection", ["artifact"]),
    ("NC-73 / NV73", ["nc-73", "nc73", "nv73", "nv-73"]),
    ("EQC1A / EQC-1A", ["eqc1a", "eqc-1a", "eqc 1a"])
]

search_directories = [
    r"C:\AI-BS",
    r"C:\Users\footb\Downloads",
    r"C:\Users\footb\Desktop",
    r"C:\Users\footb\Documents",
    r"C:\Users\footb\Music",
    r"C:\Users\footb\AppData\Roaming\Cymatics",
    r"C:\Users\footb\AppData\Roaming\Cymatics Hub",
    r"C:\Users\footb\AppData\Local\Programs",
    r"C:\ProgramData\Cymatics",
    r"C:\Program Files\Common Files\VST3",
    r"C:\Program Files\VSTPlugins",
    r"E:\\"
]

found_records = {target[0]: [] for target in search_targets}

print("=== DEEP FILESYSTEM SEARCH FOR REMAINING ASSETS ===")
print("Scanning across all system directories on C:\\ and E:\\...\n")

for base_dir in search_directories:
    if not os.path.exists(base_dir):
        continue
    try:
        for root, dirs, files in os.walk(base_dir):
            # Skip large unrelated subtrees like node_modules or .git
            if any(skip in root.lower() for skip in ["node_modules", ".git", ".gradle", "appdata\\local\\microsoft"]):
                continue
                
            for d in dirs:
                d_lower = d.lower()
                for target_name, kws in search_targets:
                    if all(k in d_lower for k in kws):
                        found_records[target_name].append(os.path.join(root, d))
                        
            for f in files:
                f_lower = f.lower()
                for target_name, kws in search_targets:
                    if all(k in f_lower for k in kws):
                        found_records[target_name].append(os.path.join(root, f))
    except Exception as e:
        print(f"Error scanning {base_dir}: {e}")

print("--------------------------------------------------")
print("               DEEP SEARCH RESULTS                ")
print("--------------------------------------------------")

for target_name, matches in found_records.items():
    unique_matches = list(set(matches))
    if unique_matches:
        print(f"\n[FOUND ON DISK] {target_name} ({len(unique_matches)} matches):")
        for m in unique_matches[:5]:
            print(f"  -> {m}")
    else:
        print(f"\n[NOT FOUND ANYWHERE] {target_name} -> 0 matches across all scanned drives")
