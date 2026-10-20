import psutil, subprocess

print(f"Total PIDs in system: {len(psutil.pids())}")

games = []
for pid in psutil.pids():
    try:
        p = psutil.Process(pid)
        name = p.name()
        name_lower = name.lower()
        if any(g in name_lower for g in [
            'fortnite', 'cod', 'warzone', 'valorant', 'apex', 'roblox', 'minecraft', 
            'steam', 'overwatch', 'cyberpunk', 'shipping', 'r5apex', 'league', 
            'dota', 'csgo', 'cs2', 'gta', 'fivem', 'halo', 'destiny', 'rocketleague', 
            'pubg', 'tarkov', 'genshin', 'starfield', 'eldenring', 'unreal', 'unity', 'game'
        ]):
            games.append({"pid": pid, "name": name})
    except Exception:
        pass

print(f"Discovered {len(games)} matching games/launchers:")
for g in games:
    print(f"  - [{g['pid']}] {g['name']}")
