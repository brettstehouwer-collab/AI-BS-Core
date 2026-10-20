import os
import glob
import json

manifest_dir = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
for f in glob.glob(os.path.join(manifest_dir, "*.item")):
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            if data.get("DisplayName") == "Fortnite":
                print("FORTNITE MANIFEST:")
                print(f"  InstallLocation: {data.get('InstallLocation')}")
                print(f"  LaunchExecutable: {data.get('LaunchExecutable')}")
                print(f"  LaunchCommand: {data.get('LaunchCommand')}")
                print(f"  AppName: {data.get('AppName')}")
                print(f"  CatalogItemId: {data.get('CatalogItemId')}")
                print(f"  MainGameCatalogItemId: {data.get('MainGameCatalogItemId')}")
    except Exception as e:
        pass

# Check Epic Launcher crash logs
log_dir = os.path.expandvars(r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\Logs")
print(f"\nChecking Epic Launcher Logs in {log_dir}...")
if os.path.exists(log_dir):
    logs = sorted(glob.glob(os.path.join(log_dir, "*.log")), key=os.path.getmtime, reverse=True)
    if logs:
        print(f"Latest Log: {logs[0]}")
        with open(logs[0], "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
            print("Last 25 lines of latest log:")
            for line in lines[-25:]:
                print("  ", line.strip())
