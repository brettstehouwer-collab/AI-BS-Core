import os
import sys
import json
import time

sys.path.insert(0, "C:/AI-BS/native_studio")
from xbox_tier4_deployer import XboxDevicePortalPipeline, AppxPackageInspector

PACKAGES_DIR = r"C:\XboxStaging\Packages"

PACKAGES = [
    "duckstation-uwp_1.0.0.0_x64_ReleaseUWP.appx",
    "DolphinWinRT_1.1.7.0.appx",
    "PPSSPP_UWP_1.17.0.0_x64_UWP_Gold.msix",
    "xbsx2_2.0.2.0_x64.appx"
]

DEPS = [
    os.path.join(PACKAGES_DIR, "Microsoft.VCLibs.x64.14.00.appx"),
    os.path.join(PACKAGES_DIR, "Microsoft.UI.Xaml.2.7.appx")
]

def main():
    print("=" * 80)
    print("DEPLOYING STANDALONE UWP EMULATORS TO XBOX ONE OVER 1 GBPS WIRE")
    print("=" * 80)

    pipe = XboxDevicePortalPipeline()
    ok, msg = pipe.test_connection()
    if not ok:
        print(f"[-] Cannot connect to Device Portal: {msg}")
        return

    print(f"[+] Device Portal Online: {msg}")

    # Inspect all packages first
    print("\n--- Pre-flight Package Manifest Inspection ---")
    for pkg_name in PACKAGES:
        pkg_path = os.path.join(PACKAGES_DIR, pkg_name)
        if not os.path.exists(pkg_path):
            print(f"[-] Missing: {pkg_name}")
            continue
        info = AppxPackageInspector.inspect_package(pkg_path)
        name = info.get("identity", {}).get("Name", pkg_name)
        ver = info.get("identity", {}).get("Version", "1.0")
        print(f"[*] {name} (v{ver}) | Size: {info['size_mb']} MB")
        if info.get("dependencies"):
            print(f"    Dependencies: {', '.join(info['dependencies'])}")

    # Check available dependency files
    valid_deps = [d for d in DEPS if os.path.exists(d)]
    print(f"\n[+] Staged dependencies available: {[os.path.basename(d) for d in valid_deps]}")

    results = {}
    for idx, pkg_name in enumerate(PACKAGES, 1):
        pkg_path = os.path.join(PACKAGES_DIR, pkg_name)
        print("\n" + "=" * 80)
        print(f"[{idx}/{len(PACKAGES)}] DEPLOYING: {pkg_name}")
        print("=" * 80)

        # Deploy package with staged dependencies
        success = pipe.deploy_package(pkg_path, dependencies=valid_deps)
        results[pkg_name] = success
        if success:
            print(f"[+] Successfully deployed and registered {pkg_name}!")
        else:
            print(f"[-] Deployment failed for {pkg_name}")
        time.sleep(2)

    print("\n" + "=" * 80)
    print("DEPLOYMENT SUMMARY")
    print("=" * 80)
    for pkg, res in results.items():
        status_str = "SUCCESS" if res else "FAILED"
        print(f"  {pkg:45s} -> [{status_str}]")

    print("\nQuerying installed packages from Xbox...")
    time.sleep(2)
    apps = pipe.list_installed_apps()
    installed_names = [a.get("Name", "") for a in apps]
    print(f"[+] Total packages registered on Xbox: {len(installed_names)}")
    for pkg_name in PACKAGES:
        # Check by filename fragment or app name
        found = any(pkg_name.lower().replace(".appx", "").replace(".msix", "") in n.lower() for n in installed_names)
        print(f"  Verified on Xbox: {pkg_name} -> {found}")

if __name__ == "__main__":
    main()
