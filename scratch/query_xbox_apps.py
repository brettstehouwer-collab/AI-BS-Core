import sys
import json
sys.path.insert(0, "C:/AI-BS/native_studio")
from xbox_tier4_deployer import XboxDevicePortalPipeline

p = XboxDevicePortalPipeline()
ok, msg = p.test_connection()
print(f"Connection test: {ok} -> {msg}")
apps = p.list_installed_apps()
print(f"Total installed apps: {len(apps)}")
user_apps = []
for a in apps:
    name = a.get("Name", "")
    full_name = a.get("PackageFullName", "")
    if not any(name.startswith(pfx) for pfx in ["Microsoft.", "Windows.", "Xbox."]):
        user_apps.append((name, full_name))

print("\n--- Non-System Installed Apps ---")
for name, fn in sorted(user_apps):
    clean_name = name.encode("ascii", "replace").decode("ascii")
    print(f"- {clean_name}: {fn}")

