import os
import sys
import time
import subprocess
import json

# Ensure native_studio is on path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from xbox_netcode_engine import NetcodeAnalyzer
from xbox_tier4_deployer import XboxDevicePortalPipeline, AppxPackageInspector
from xbox_tier5_ftp_engine import XboxFTPEngine, STAGING_ROOT
from xbox_wgs_save_engine import WGSEngine

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def check_xbox_ping() -> tuple[bool, str]:
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Test-Connection -ComputerName 192.168.10.2 -Count 1 -Quiet"],
            capture_output=True, text=True, timeout=3
        )
        is_up = "True" in res.stdout
        return is_up, "< 1 ms" if is_up else "Offline"
    except Exception:
        return False, "Error"

def check_portal_status() -> str:
    try:
        pipe = XboxDevicePortalPipeline()
        ok, msg = pipe.test_connection()
        return "[ONLINE - Dev Mode]" if ok else "[OFFLINE - Retail Mode]"
    except Exception:
        return "[UNKNOWN]"

def print_banner():
    clear_screen()
    is_up, ping_str = check_xbox_ping()
    portal_str = check_portal_status()

    link_badge = "[ONLINE]" if is_up else "[OFFLINE]"
    print("=" * 80)
    print("      █████╗ ██╗      ██████╗ ███████╗   ██╗   ██╗██████╗  ██████╗ ")
    print("     ██╔══██╗██║      ██╔══██╗██╔════╝   ██║   ██║██╔══██╗██╔════╝ ")
    print("     ███████║██║█████╗██████╔╝███████╗   ██║   ██║██████╔╝██║  ███╗")
    print("     ██╔══██║██║╚════╝██╔══██╗╚════██║   ╚██╗ ██╔╝██╔═══╝ ██║   ██║")
    print("     ██║  ██║██║      ██████╔╝███████║    ╚████╔╝ ██║     ╚██████╔╝")
    print("     ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚══════╝     ╚═══╝  ╚═╝      ╚═════╝ ")
    print("              XBOX ONE ADVANCED MISSION CONTROL WORKSTATION")
    print("=" * 80)
    print(f" Host Gateway:  192.168.10.1 (Realtek 2.5GbE @ 1 Gbps)  | Internet NAT: Active")
    print(f" Target Xbox:   192.168.10.2 {link_badge} (Ping: {ping_str})     | Device Portal: {portal_str}")
    print("=" * 80)

def menu_tier1():
    print("\n--- [TIER 1] LIVE PACKET SNIFFER & NETCODE HUD ---")
    print("Interprets raw IP frames, verifies RFC 1071 checksums, and decodes layer 4.")
    dur = input("Enter capture duration in seconds (default 15, or 'c' for continuous): ").strip()
    sec = None if dur.lower() == 'c' else (int(dur) if dur.isdigit() else 15)
    
    analyzer = NetcodeAnalyzer()
    try:
        analyzer.start(sec)
    except KeyboardInterrupt:
        pass
    input("\nPress Enter to return to main menu...")

def menu_tier2():
    print("\n--- [TIER 2] DNS SPOOFER & MULTIPLAYER SERVER INJECTOR ---")
    cfg_file = os.path.join(SCRIPT_DIR, "xbox_dns_config.json")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r") as f:
            cfg = json.load(f)
        print(f"Current Target Server: {cfg.get('server_proxy', {}).get('target_server_host')}:{cfg.get('server_proxy', {}).get('target_server_port')}")
        print(f"Current Custom MOTD:   {cfg.get('server_proxy', {}).get('custom_motd')}")
        print(f"Intercepted Domains:   {len(cfg.get('intercept_domains', []))} domains active")
        
        choice = input("\n[1] Change Target Server | [2] Change MOTD | [B] Back: ").strip().lower()
        if choice == "1":
            new_host = input("Enter new Target Server host (e.g. play.cubecraft.net or custom IP): ").strip()
            new_port = input("Enter new Target Server port (default 19132): ").strip()
            if new_host:
                cfg["server_proxy"]["target_server_host"] = new_host
                cfg["server_proxy"]["target_server_port"] = int(new_port) if new_port.isdigit() else 19132
                with open(cfg_file, "w") as f:
                    json.dump(cfg, f, indent=2)
                print("[+] Configuration updated! Daemon reloads automatically in 5 seconds.")
        elif choice == "2":
            new_motd = input("Enter new MOTD string (supports § colors): ").strip()
            if new_motd:
                cfg["server_proxy"]["custom_motd"] = new_motd
                with open(cfg_file, "w") as f:
                    json.dump(cfg, f, indent=2)
                print("[+] MOTD updated! Console server list will show new title.")
    input("\nPress Enter to return to main menu...")

def menu_tier3():
    print("\n--- [TIER 3] XBOX CLOUD SAVE (WGS) DESERIALIZER & MODDER ---")
    engine = WGSEngine()
    games = engine.discover_wgs_games()
    if not games:
        print("No active Xbox Connected Storage packages found.")
    else:
        for i, g in enumerate(games):
            print(f" [{i+1}] {g['package_name']} ({g['total_files']} files)")
        g_idx = input("\nSelect game number to inspect (or 'b' to cancel): ").strip()
        if g_idx.isdigit() and 1 <= int(g_idx) <= len(games):
            sel_game = games[int(g_idx) - 1]
            print(f"\n[*] Creating safe backup...")
            bpath = engine.create_backup(sel_game["wgs_path"])
            print(f"[+] Backup secured: {bpath}")
            
            # List blobs in selected game
            blobs = []
            for root, dirs, files in os.walk(sel_game["wgs_path"]):
                for f in files:
                    if not f.startswith("container"):
                        blobs.append(os.path.join(root, f))
            print(f"\nDiscovered {len(blobs)} data blob(s). Displaying largest save file:")
            if blobs:
                largest = max(blobs, key=os.path.getsize)
                print(engine.hex_dump(largest, 128))
    input("\nPress Enter to return to main menu...")

def menu_tier4():
    print("\n--- [TIER 4] XBOX DEVICE PORTAL APP & EMULATOR DEPLOYER ---")
    pipe = XboxDevicePortalPipeline()
    ok, msg = pipe.test_connection()
    print(f"Portal Status: {msg}")
    
    choice = input("\n[1] Inspect .appx / .msix Package | [2] Deploy Package to Console | [3] Remote Reboot | [B] Back: ").strip().lower()
    if choice == "1":
        pkg_path = input("Enter path to package file: ").strip().strip('"')
        if os.path.exists(pkg_path):
            info = AppxPackageInspector.inspect_package(pkg_path)
            print("\nPre-Flight Inspection:")
            print(json.dumps(info, indent=2))
        else:
            print("[-] File not found.")
    elif choice == "2":
        if not ok:
            print("[-] Cannot deploy: Console is in Retail Mode or Port 11443 is unreachable.")
            print("    Please switch console to Developer Mode first.")
        else:
            pkg_path = input("Enter path to .appx or .msixbundle file: ").strip().strip('"')
            if os.path.exists(pkg_path):
                pipe.deploy_package(pkg_path)
    elif choice == "3":
        if ok:
            if input("Reboot Xbox One console now? (y/n): ").strip().lower() == "y":
                if pipe.reboot_console():
                    print("[+] Reboot signal acknowledged by Xbox.")
        else:
            print("[-] Remote control requires Developer Mode.")
    input("\nPress Enter to return to main menu...")

def menu_tier5():
    print("\n--- [TIER 5] WIRE-SPEED EMULATION ASSET & ROM PUSHER ---")
    from xbox_rom_pusher import XboxRomPusher, ROMS_DIR, BIOS_DIR
    pusher = XboxRomPusher()
    
    print("\nLocal Staging Directories:")
    print(f"  ROMs:  {ROMS_DIR} (PS2, GameCube, Wii, N64, Dreamcast, PS1, GBA, SNES...)")
    print(f"  BIOS:  {BIOS_DIR} (System BIOS files)")
    print(f"  Target: Xbox RetroArch (/LocalState/ROMs & /LocalState/system)")

    choice = input("\n[1] Sync All Staged ROMs & BIOS | [2] Start Live Auto-Push Watcher | [3] Init Emulation Tree on Xbox | [B] Back: ").strip().lower()
    if choice == "1":
        pusher.sync_all()
    elif choice == "2":
        pusher.watch()
    elif choice == "3":
        pusher.init_console_structure()
    input("\nPress Enter to return to main menu...")

def menu_emulation_assistant():
    print("\n" + "=" * 80)
    print(" [*] OPTION 3: XBOX DEV MODE & EMULATION SETUP ASSISTANT")
    print("=" * 80)
    print("Follow this step-by-step roadmap to turn your Xbox into an Emulation Machine:")
    print()
    print(" STEP 1: CONSOLE ACTIVATION (On your TV / Xbox)")
    print("   1. Open the Microsoft Store on your Xbox One.")
    print("   2. Search for 'Xbox Dev Mode Activation' and install it (free download).")
    print("   3. Launch the app. Note the 6-character activation code displayed.")
    print("   4. On your PC browser, go to: https://partner.microsoft.com/xboxconfig/activate")
    print("   5. Sign in with your Microsoft account, enter the code, and confirm.")
    print("   6. On your Xbox, select 'Switch and restart'. The console reboots into Dev Mode!")
    print()
    print(" STEP 2: VERIFY DEVICE PORTAL ACCESS")
    print("   * When Dev Mode boots, note the IP on the bottom-right of your TV screen.")
    print("   * It will display: https://192.168.10.2:11443")
    print("   * Select 'Dev Home' > ensure 'Xbox Device Portal' is set to Enabled.")
    print()
    print(" STEP 3: 1-CLICK DEPLOY RETROARCH")
    print("   * Once Dev Mode is active, choose option [4] in this menu or run:")
    print("     python xbox_tier4_deployer.py deploy C:\\XboxStaging\\Packages\\RetroArch.msixbundle")
    print()
    print(" STEP 4: LOAD YOUR ROMS VIA DIRECT ETHERNET")
    print("   * Drop your game files into your PC's staging folders:")
    print(f"     PS2 / GameCube / N64:  {os.path.join(STAGING_ROOT, 'ROMs')}")
    print("   * Choose option [5] in this menu to push them at 110 MB/s!")
    print("=" * 80)
    input("\nPress Enter to return to main menu...")

def main():
    while True:
        print_banner()
        print(" [1] Tier 1: Real-Time Packet Sniffer & Netcode HUD")
        print(" [2] Tier 2: DNS Spoofer & Server Injector (Custom Multiplayer)")
        print(" [3] Tier 3: Binary Game Save Deserializer & Modder (WGS)")
        print(" [4] Tier 4: Device Portal App & Emulator Deployer (.msix/.appx)")
        print(" [5] Tier 5: Wire-Speed FTP ROM & Asset Pusher (110 MB/s)")
        print("--------------------------------------------------------------------------------")
        print(" [6] Emulation & Dev Mode Setup Roadmap (Step-by-Step)")
        print(" [7] Quick Network Diagnostic & Ping Benchmark")
        print(" [0] Exit")
        print("=" * 80)
        
        choice = input("Enter selection [0-7]: ").strip()
        if choice == "1":
            menu_tier1()
        elif choice == "2":
            menu_tier2()
        elif choice == "3":
            menu_tier3()
        elif choice == "4":
            menu_tier4()
        elif choice == "5":
            menu_tier5()
        elif choice == "6":
            menu_emulation_assistant()
        elif choice == "7":
            is_up, ping_str = check_xbox_ping()
            print(f"\nPing Test: {'REACHABLE' if is_up else 'UNREACHABLE'} (Latency: {ping_str})")
            input("Press Enter to continue...")
        elif choice == "0":
            print("\nExiting Mission Control. Background network daemons remain active.")
            break

if __name__ == "__main__":
    main()
