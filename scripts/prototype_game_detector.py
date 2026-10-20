import subprocess, csv, io, psutil, win32gui, win32process

KNOWN_GAME_MAP = {
    "fortniteclient-win64-shipping.exe": "Fortnite",
    "fortnitelauncher.exe": "Fortnite Launcher",
    "fortniteclient-win64-shipping_eac_eos.exe": "Fortnite (EAC)",
    "cod.exe": "Call of Duty",
    "bootcamp.exe": "Call of Duty: Warzone",
    "r5apex.exe": "Apex Legends",
    "valorant-win64-shipping.exe": "Valorant",
    "cs2.exe": "Counter-Strike 2",
    "csgo.exe": "Counter-Strike: Global Offensive",
    "overwatch.exe": "Overwatch 2",
    "robloxplayerbeta.exe": "Roblox",
    "javaw.exe": "Minecraft",
    "minecraft.exe": "Minecraft",
    "gta5.exe": "Grand Theft Auto V",
    "fivem.exe": "FiveM (GTA V)",
    "rocketleague.exe": "Rocket League",
    "leagueclientux.exe": "League of Legends",
    "league of legends.exe": "League of Legends",
    "dota2.exe": "Dota 2",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "eldenring.exe": "Elden Ring",
    "starfield.exe": "Starfield",
    "genshinimpact.exe": "Genshin Impact",
    "tarkov.exe": "Escape from Tarkov",
    "escapefromtarkov.exe": "Escape from Tarkov",
    "pubg.exe": "PUBG: BATTLEGROUNDS",
    "tslgame.exe": "PUBG: BATTLEGROUNDS",
    "helldivers2.exe": "HELLDIVERS 2",
    "destiny2.exe": "Destiny 2",
    "halo_infinite.exe": "Halo Infinite",
    "haloinfinite.exe": "Halo Infinite"
}

IGNORE_TITLES = {
    "N/A", "OleMainThreadWndName", "Default IME", "MSCTFIME UI",
    "Program Manager", "Settings", "Windows Input Experience",
    "DWM Notification Window", "NvSvc", "UxdService", "BroadcastListenerWindow",
    "Flyout window", "Windows Push Notifications Platform", "Task Host Window",
    "CrossDeviceResumeWindow", "Search", "Start", "Player Location Check",
    "OLEChannelWnd", "GDI+ Window", "Logi Plugin Service", "Logi_Devio_MainWindow",
    "RealtekAudioBackgroundProcessClass", "Temp Window", "WingetMessageOnlyWindow",
    "CRC Message Loop Wnd", "Quick Settings"
}

def scan_system_windows_and_games():
    windows = []
    active_game = None
    
    # 1. Fast & Resilient Tasklist Window Enumeration
    try:
        res = subprocess.run(["tasklist", "/v", "/fo", "csv"], capture_output=True, text=True, errors='ignore')
        reader = csv.DictReader(io.StringIO(res.stdout))
        for row in reader:
            title = (row.get("Window Title") or "").strip()
            pname = (row.get("Image Name") or "").strip()
            pname_lower = pname.lower()
            pid_str = row.get("PID", "0")
            try:
                pid = int(pid_str)
            except ValueError:
                pid = 0
                
            if not title or title in IGNORE_TITLES or title.startswith("GDI+ Window") or title.startswith(".NET-Broadcast"):
                continue
                
            # Filter studio loopback
            if any(studio_name in title for studio_name in ["AI-BS Broadcast Studio", "Antigravity IDE", "cmd.exe", "powershell.exe"]):
                continue

            # Identify if it's a game
            is_game = False
            friendly_game_name = None
            if pname_lower in KNOWN_GAME_MAP:
                is_game = True
                friendly_game_name = KNOWN_GAME_MAP[pname_lower]
            elif any(g in pname_lower or g in title.lower() for g in ["game", "shipping", "unreal", "unity"]):
                if "steam" not in pname_lower and "service" not in pname_lower:
                    is_game = True
                    friendly_game_name = title or pname

            display_name = f"[GAME] {friendly_game_name or title} ({pname})" if is_game else f"[WIN] {title} ({pname})"
            
            entry = {
                "title": title,
                "process_name": pname,
                "pid": pid,
                "is_game": is_game,
                "game_name": friendly_game_name or title,
                "display_name": display_name
            }
            windows.append(entry)
            
            if is_game and not active_game:
                active_game = entry
    except Exception as e:
        print("Tasklist scan error:", e)

    # Sort games to top
    windows.sort(key=lambda x: (not x["is_game"], x["title"]))
    return {"windows": windows, "active_game": active_game}

result = scan_system_windows_and_games()
print("=== Active Game Detected ===")
ag = result["active_game"]
if ag:
    print(f"  Game: {ag['game_name']} | Process: {ag['process_name']} | PID: {ag['pid']}")
else:
    print("  No active game detected.")

print(f"\n=== Found {len(result['windows'])} Application Windows ===")
for w in result["windows"]:
    print(f"  {w['display_name']} | PID {w['pid']} | is_game: {w['is_game']}")
