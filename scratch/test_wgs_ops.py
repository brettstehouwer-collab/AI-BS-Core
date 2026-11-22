import sys
import os
sys.path.append(r"C:\AI-BS\native_studio")
from xbox_wgs_save_engine import WGSEngine

engine = WGSEngine()
games = engine.discover_wgs_games()
if games:
    g = games[0]
    print(f"[*] Creating safe backup for {g['package_name']}...")
    bpath = engine.create_backup(g["wgs_path"])
    
    blob = r"C:\Users\footb\AppData\Local\Packages\38985CA0.MW4Beta_5bkah9njm3e9g\SystemAppData\wgs\00090000057C2E28_0000000000000000000000006422D247\6CA9AA7D330147EA81194F5AA5897C89\E56BDCC41F3C4408A23E7C6903662C5C"
    print("\n" + engine.hex_dump(blob, 96))
