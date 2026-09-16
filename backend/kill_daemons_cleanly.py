import psutil
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

current_pid = os.getpid()

target_scripts = [
    'auto_healer_daemon.py',
    'context_ingestor_daemon.py',
    'research_agent_daemon.py',
    'wallet_tracker_daemon.py',
    'discord_bot_daemon.py',
    'aibs_social_daemon.py',
    'growth_marketing_daemon.py',
    'aibs_drop_stream_watcher.py',
    'track_live_giveaways.py'
]

killed_count = 0
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['pid'] == current_pid:
            continue
        cmd = ' '.join(p.info['cmdline'] or [])
        for script in target_scripts:
            if script in cmd:
                print(f"Terminating PID {p.info['pid']} -> {script}")
                p.kill()
                killed_count += 1
                break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"\nAll watchdog and sniffer daemons terminated ({killed_count} processes killed).")
