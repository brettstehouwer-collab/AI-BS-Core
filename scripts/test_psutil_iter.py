import psutil

print("Scanning processes with psutil...")
games = []
for p in psutil.process_iter():
    try:
        pname = p.name()
        pid = p.pid
        pname_lower = pname.lower()
        
        # Check if known game
        is_game = any(g in pname_lower for g in [
            'fortnite', 'cod', 'warzone', 'valorant', 'apex', 'roblox', 'minecraft', 
            'steam', 'overwatch', 'cyberpunk', 'shipping', 'r5apex', 'league', 
            'dota', 'csgo', 'cs2', 'gta', 'fivem', 'halo', 'destiny', 'rocketleague', 
            'pubg', 'tarkov', 'genshin', 'starfield', 'eldenring', 'unreal', 'unity'
        ])
        
        try:
            mem_mb = p.memory_info().rss / (1024 * 1024)
        except Exception:
            mem_mb = 0
            
        if is_game or mem_mb > 500:
            print(f"  🎮 Process: {pname} (PID {pid}) | RAM: {mem_mb:.1f} MB")
            if is_game:
                games.append({"name": pname, "pid": pid, "ram_mb": mem_mb})
    except Exception:
        pass

print(f"\nDiscovered {len(games)} game processes:")
for g in games:
    print(f"  >>> ACTIVE GAME: {g['name']} (PID: {g['pid']})")
