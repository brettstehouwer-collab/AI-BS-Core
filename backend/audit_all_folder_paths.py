import os
import json
import re

paths_to_audit = [
    ("1. Cymatics Hub App", r"C:\Users\footb\AppData\Local\Programs\cymatics-hub"),
    ("2. Cymatics Hub Database", r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"),
    ("3. Installer Cache", r"C:\Users\footb\AppData\Roaming\Cymatics Hub\installer-cache"),
    ("4. DAW Sample Packs Vault", r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sample_Packs"),
    ("5. DAW Sound Banks Vault", r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sound_Banks"),
    ("6. VST3 System Plugins", r"C:\Program Files\Common Files\VST3"),
    ("7. Downloads Folder", r"C:\Users\footb\Downloads"),
    ("8. E:\\ Physical Storage", r"E:\\"),
    ("9. Muse Hub Orchestral Suite", r"E:\Muse Hub\Instruments"),
    ("10. AI-BS Docs Vault", r"C:\AI-BS\docs")
]

results = {}
total_files_all = 0
total_size_all = 0

for label, p in paths_to_audit:
    exists = os.path.exists(p)
    file_count = 0
    dir_count = 0
    size_bytes = 0
    top_items = []
    
    if exists:
        try:
            items = os.listdir(p)
            for item in items:
                ip = os.path.join(p, item)
                if os.path.isdir(ip):
                    dir_count += 1
                else:
                    file_count += 1
                    size_bytes += os.path.getsize(ip)
            top_items = sorted(items)[:20]
        except Exception as e:
            top_items = [f"Error: {e}"]
            
    results[label] = {
        "path": p,
        "exists": exists,
        "file_count": file_count,
        "dir_count": dir_count,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "sample_items": top_items
    }

# 17 Stream Drops Verification
stream_items = [
    ('DOPE Collection - Melodies', ['dope', 'melod']),
    ('DOPE Collection - Drums', ['dope', 'drum']),
    ('DOPE Collection - Vocals', ['dope', 'vocal']),
    ('DOPE Collection - Bonus Stash', ['dope', 'stash']),
    ('Solace - Acapellas', ['solace']),
    ('Daydream - Vocal Loops', ['daydream']),
    ('Euphoria - Vocal Chops', ['euphoria']),
    ('SESSIONS: Melody Compositions', ['sessions']),
    ('Generations - 1970s Samples', ['generations', '1970']),
    ('Generations - 1960s Samples', ['generations', '1960']),
    ('Kingdom: Electronic MIDI', ['kingdom']),
    ('Pandora - EDM MIDI', ['pandora']),
    ('Pandora - RnB MIDI', ['pandora']),
    ('Pandora - Trap MIDI', ['pandora']),
    ('Pandora: Paradise Expansion', ['pandora']),
    ('Pandora: Echoes Expansion', ['pandora']),
    ('MIDI Shredder', ['midi', 'shredder'])
]

# Check VSTs
vst_list = [f for f in os.listdir(r"C:\Program Files\Common Files\VST3")] if os.path.exists(r"C:\Program Files\Common Files\VST3") else []
e_dirs = [f for f in os.listdir("E:\\") if os.path.isdir(os.path.join("E:\\", f))] if os.path.exists("E:\\") else []

stream_verification = []
for title, kws in stream_items:
    found = False
    location = "Not found"
    
    # Check E:\
    for ed in e_dirs:
        if all(k in ed.lower() for k in kws):
            found = True
            location = f"E:\\{ed}"
            break
            
    # Check VSTs
    if not found:
        for v in vst_list:
            if all(k in v.lower() for k in kws):
                found = True
                location = f"VST3: {v}"
                break
                
    stream_verification.append({
        "title": title,
        "found": found,
        "location": location
    })

print("=== COMPLETE MULTI-PATH SYSTEM AUDIT ===")
for label, data in results.items():
    status = "ONLINE" if data["exists"] else "MISSING"
    print(f"\n[{status}] {label} ({data['path']})")
    print(f"  Files: {data['file_count']} | Dirs: {data['dir_count']}")
    print(f"  Top Entries: {', '.join(data['sample_items'][:6])}...")

print("\n=== 17 STREAM DROPS STATUS ===")
for sv in stream_verification:
    s_sym = "[CHECKED OFF]" if sv["found"] else "[MISSING]"
    print(f"  {s_sym} {sv['title']} -> {sv['location']}")

found_cnt = len([s for s in stream_verification if s["found"]])
print(f"\nStream Drops Verified: {found_cnt} of {len(stream_verification)} ({round(found_cnt/len(stream_verification)*100, 1)}%)")
