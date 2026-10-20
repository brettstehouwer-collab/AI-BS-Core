import os, psutil

print("Current Process PID:", os.getpid())

print("\n--- All Running Processes and their Main Window or Game Signature ---")
games = []
for p in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
    try:
        pname = p.info['name']
        pname_lower = pname.lower()
        
        # Check if process is known game or high-resource 3D application
        is_game = any(g in pname_lower for g in [
            'fortnite', 'cod', 'warzone', 'valorant', 'apex', 'roblox', 'minecraft', 
            'steam', 'overwatch', 'cyberpunk', 'shipping', 'r5apex', 'league', 
            'dota', 'csgo', 'cs2', 'gta', 'fivem', 'halo', 'destiny', 'rocketleague', 
            'pubg', 'tarkov', 'genshin', 'starfield', 'eldenring', 'unreal', 'unity'
        ])
        
        mem_mb = p.info['memory_info'].rss / (1024 * 1024) if p.info['memory_info'] else 0
        if is_game or mem_mb > 500:
            print(f"  🎮 Process: {pname} (PID {p.info['pid']}) | RAM: {mem_mb:.1f} MB")
            if is_game:
                games.append({"name": pname, "pid": p.info['pid'], "ram_mb": mem_mb})
    except Exception:
        pass

print("\n--- Games Detected via Process Scan ---")
for g in games:
    print(f"  >>> ACTIVE GAME DETECTED: {g['name']} (PID: {g['pid']}, RAM: {g['ram_mb']:.1f} MB)")
