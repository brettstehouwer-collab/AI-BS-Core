import os
import psutil

def check_status():
    python_env = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
    if not os.path.exists(python_env):
        return f"Error: Python environment not found at {python_env}"
    
    processes_to_check = [
        "AI_BS_Backend.py",
        "zombie_node_cleaner.py",
        "shm_websocket_gateway.py",
        "crypto_trader_bot.py",
        "unified_crypto_pearl_watchdog.py",
        "pearl_payout_watcher.py"
    ]
    
    active_matches = {p: [] for p in processes_to_check}
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline)
            for p in processes_to_check:
                if p.lower() in cmd_str.lower():
                    active_matches[p].append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    active_summary = []
    for p, pids in active_matches.items():
        if pids:
            active_summary.append(f"{p} (PID: {', '.join(map(str, pids))})")
            
    if not active_summary:
        return "All target backend processes are inactive."
    return "Active backend processes:\n  - " + "\n  - ".join(active_summary)

if __name__ == "__main__":
    print(check_status())
