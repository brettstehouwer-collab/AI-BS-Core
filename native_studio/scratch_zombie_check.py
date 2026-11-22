import psutil
import os
import sys

print("=== AUDITING ACTIVE PROCESSES FOR ZOMBIES & ORPHANS ===")
zombies = []
running_pids = set(p.pid for p in psutil.process_iter())

for p in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'status', 'memory_info', 'create_time']):
    try:
        p_name = (p.info['name'] or '').lower()
        if any(token in p_name for token in ['python', 'node', 'uv', 'ffmpeg', 'gradle']):
            ppid = p.info['ppid']
            is_parent_alive = ppid in running_pids and ppid != 0
            cmdline = " ".join(p.info['cmdline'] or [])
            mem_mb = (p.info['memory_info'].rss if p.info['memory_info'] else 0) / (1024 * 1024)
            status = p.info['status']
            
            # Check if parent is dead, or process is zombie, or process has 0 memory / suspended
            is_orphan = not is_parent_alive
            if status == psutil.STATUS_ZOMBIE or (is_orphan and p.info['pid'] != os.getpid()):
                zombies.append({
                    "pid": p.info['pid'],
                    "ppid": ppid,
                    "name": p.info['name'],
                    "status": status,
                    "mem_mb": round(mem_mb, 2),
                    "is_orphan": is_orphan,
                    "cmdline": cmdline[:120]
                })
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Found {len(zombies)} potentially orphaned or zombie processes:")
for z in zombies:
    print(f"  PID {z['pid']} (PPID {z['ppid']}, Orphan: {z['is_orphan']}, Status: {z['status']}, Mem: {z['mem_mb']}MB): {z['name']} -> {z['cmdline']}")
