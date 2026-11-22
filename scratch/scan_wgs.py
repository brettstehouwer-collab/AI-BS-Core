import os
import glob

local_app_data = os.environ.get("LOCALAPPDATA", "")
packages_dir = os.path.join(local_app_data, "Packages")

found_games = []

if os.path.exists(packages_dir):
    for entry in os.listdir(packages_dir):
        wgs_dir = os.path.join(packages_dir, entry, "SystemAppData", "wgs")
        if os.path.exists(wgs_dir):
            files = list(glob.glob(os.path.join(wgs_dir, "**", "*"), recursive=True))
            file_count = len([f for f in files if os.path.isfile(f)])
            found_games.append((entry, wgs_dir, file_count))

print(f"Total Xbox Connected Storage (wgs) packages found: {len(found_games)}")
for name, path, count in found_games:
    print(f"  [+] {name} -> {count} save files ({path})")
