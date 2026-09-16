import os

from shell_adapter import run_assembled_command

target_parent = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sample_Packs"
os.makedirs(target_parent, exist_ok=True)

e_folders = [f for f in os.listdir("E:\\") if os.path.isdir(os.path.join("E:\\", f))]

sample_pack_keywords = [
    "cymatics", "dope", "generations", "sessions", "kingdom", "apocalypse",
    "destiny", "solace", "euphoria", "daydream", "duality", "phalanx", "ripple",
    "terra", "trinity", "whisper", "boom", "fugitive", "heritage", "octagon",
    "casino", "cascade", "cashmere", "evolution", "exodus", "zodiac", "dark",
    "lethal", "mirage", "cavern", "atomic", "rift", "tsunami", "diamonds",
    "vibes", "pharaoh", "dream", "deja", "genesis", "eternal"
]

created = []
already_exists = []

for folder in sorted(e_folders):
    f_lower = folder.lower()
    if any(k in f_lower for k in sample_pack_keywords):
        src_path = os.path.join("E:\\", folder)
        dst_path = os.path.join(target_parent, folder)
        
        if not os.path.exists(dst_path):
            # Create directory junction via mklink /J without shell string interpolation.
            res = run_assembled_command("cmd", "/c", "mklink", "/J", dst_path, src_path)
            if res.returncode == 0:
                created.append((folder, src_path))
            else:
                print(f"Error creating junction for {folder}: {res.stderr}")
        else:
            already_exists.append(folder)

print(f"=== CYMATICS SAMPLE PACK JUNCTIONS LINKED TO DAW ===")
print(f"Newly Linked Junctions: {len(created)}")
for f, src in created:
    print(f"  [+] Linked: {f} -> {src}")

print(f"\nAlready Existing: {len(already_exists)}")
for f in already_exists:
    print(f"  [=] Verified: {f}")

total_packs = len(os.listdir(target_parent))
print(f"\nTotal Sample Packs Active in DAW Media Vault: {total_packs}")
