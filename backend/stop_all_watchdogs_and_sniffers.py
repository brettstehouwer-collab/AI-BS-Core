import psutil
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

current_pid = os.getpid()

target_keywords = [
    'aibs_drop',
    'track_live',
    'audit_all_cards',
    'focus_new_drops',
    'auto_healer_daemon',
    'context_ingestor_daemon',
    'research_agent_daemon',
    'wallet_tracker_daemon',
    'aibs_social_daemon',
    'discord_bot_daemon',
    'growth_marketing_daemon',
    'lead_forager',
    'sniffer',
    'watchdog',
    'watcher'
]

killed = []
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['pid'] == current_pid:
            continue
        cmd = ' '.join(p.info['cmdline'] or []).lower()
        name = p.info['name'].lower()
        
        if any(k in cmd for k in target_keywords):
            print(f"Terminating PID {p.info['pid']} ({p.info['name']}): {cmd[:120]}")
            psutil.Process(p.info['pid']).kill()
            killed.append((p.info['pid'], p.info['name'], cmd))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"\nSuccessfully terminated {len(killed)} watchdog / sniffer / polling background processes.")
