import os
import json

e_drive = "E:\\"
audio_packs = []
other_folders = []

sample_pack_keywords = [
    "cymatics", "dope", "generations", "sessions", "kingdom", "apocalypse",
    "destiny", "solace", "euphoria", "daydream", "duality", "phalanx", "ripple",
    "terra", "trinity", "whisper", "boom", "fugitive", "heritage", "octagon",
    "casino", "cascade", "cashmere", "evolution", "exodus", "zodiac", "dark",
    "lethal", "mirage", "cavern", "atomic", "rift", "tsunami", "diamonds",
    "vibes", "pharaoh", "dream", "deja", "genesis", "eternal", "muse hub"
]

total_files_all = 0
total_bytes_all = 0

for item in sorted(os.listdir(e_drive)):
    item_path = os.path.join(e_drive, item)
    if os.path.isdir(item_path):
        i_lower = item.lower()
        if any(k in i_lower for k in sample_pack_keywords):
            # Calculate size and file count
            f_count = 0
            b_count = 0
            try:
                for root, dirs, files in os.walk(item_path):
                    f_count += len(files)
                    for f in files:
                        b_count += os.path.getsize(os.path.join(root, f))
            except:
                pass
                
            total_files_all += f_count
            total_bytes_all += b_count
            
            sz_str = f"{round(b_count / (1024**3), 2)} GB" if b_count >= 1024**3 else f"{round(b_count / (1024**2), 1)} MB"
            audio_packs.append({
                "name": item,
                "path": item_path,
                "files": f_count,
                "size": sz_str,
                "bytes": b_count
            })

print(f"================================================================")
print(f"      E:\\ DRIVE AUDIO & SAMPLE PACK SUITES INVENTORY           ")
print(f"================================================================")
print(f"Total Sound Banks & Production Suites on E:\\: {len(audio_packs)}")
print(f"Total Audio Files, Stems & Presets: {total_files_all}")
print(f"Total Disk Space Consumed: {round(total_bytes_all / (1024**3), 2)} GB")
print(f"----------------------------------------------------------------\n")

for idx, p in enumerate(sorted(audio_packs, key=lambda x: x['name']), 1):
    print(f"{idx:2d}. {p['name']} ({p['files']} files | {p['size']})")
