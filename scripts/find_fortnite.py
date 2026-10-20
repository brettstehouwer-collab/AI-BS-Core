import os
import glob
import json
import winreg

print("Searching Epic Games Manifests...")
manifest_dir = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
found = False
if os.path.exists(manifest_dir):
    for f in glob.glob(os.path.join(manifest_dir, "*.item")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                display_name = data.get("DisplayName", "")
                install_loc = data.get("InstallLocation", "")
                launch_exe = data.get("LaunchExecutable", "")
                app_name = data.get("AppName", "")
                print(f"Found Installed App: '{display_name}' ({app_name}) at '{install_loc}' (Launch: {launch_exe})")
                if "fortnite" in display_name.lower() or "fortnite" in app_name.lower():
                    found = True
        except Exception as e:
            print(f"Error reading {f}: {e}")

# Also check Registry for Uninstall keys or Epic keys
print("\nChecking Registry...")
reg_paths = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\Epic Games\EpicGamesLauncher",
    r"SOFTWARE\EpicGames",
]

for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
    for sub in reg_paths:
        try:
            with winreg.OpenKey(hive, sub) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                dname, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                if "fortnite" in str(dname).lower():
                                    iloc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                    print(f"Registry found Fortnite: {dname} at {iloc}")
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

# Check common drives for Fortnite directories
print("\nChecking drive roots...")
candidates = [
    r"C:\Program Files\Epic Games\Fortnite",
    r"D:\Epic Games\Fortnite",
    r"E:\Epic Games\Fortnite",
    r"C:\Fortnite",
    r"D:\Fortnite",
    r"E:\Fortnite",
    r"C:\Games\Fortnite",
    r"D:\Games\Fortnite",
    r"E:\Games\Fortnite",
    r"D:\EpicGames\Fortnite",
    r"E:\EpicGames\Fortnite",
]

for c in candidates:
    if os.path.exists(c):
        print(f"FOUND DIRECTORY: {c}")
        bin_dir = os.path.join(c, "FortniteGame", "Binaries", "Win64")
        if os.path.exists(bin_dir):
            print(f"  Binaries exist: {bin_dir}")
            for exe in os.listdir(bin_dir):
                if exe.endswith(".exe"):
                    print(f"    Exe: {exe}")
