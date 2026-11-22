import os
import psutil

target_scripts = [
    "discord_bot_daemon.py",
    "pearl_payout_watcher.py",
    "crypto_trader_bot.py"
]

current_pid = os.getpid()
killed = []

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.pid == current_pid:
            continue
        cmd = " ".join(p.info.get('cmdline') or [])
        for script in target_scripts:
            if script in cmd:
                print(f"Terminating stale instance {p.pid}: {cmd[:80]}")
                p.terminate()
                try:
                    p.wait(timeout=2)
                except psutil.TimeoutExpired:
                    p.kill()
                killed.append((p.pid, script))
                break
    except Exception as e:
        print(f"Error checking {p.pid}: {e}")

print(f"Purge complete. Terminated {len(killed)} zombie processes.")
