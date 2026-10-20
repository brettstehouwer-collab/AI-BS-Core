import psutil
import os

CURRENT_PID = os.getpid()

KEEP_CMDLINE_KEYWORDS = [
    'gpu_thermal_guardian.py',
    'salad_ledger_daemon_godmode.py'
]

KEEP_PROCESS_NAMES = [
    'salad',
    'rigel',
    'antigravity'
]

killed = []

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        pid = proc.info['pid']
        if pid == CURRENT_PID:
            continue
        
        name = (proc.info['name'] or '').lower()
        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
        
        # Keep essential Salad, guardian, and editor
        if any(kp in name for kp in KEEP_PROCESS_NAMES):
            continue
        if any(kc in cmdline for kc in KEEP_CMDLINE_KEYWORDS):
            continue
        if 'antigravity' in name or 'antigravity' in cmdline:
            continue
            
        # Target all non-essential AI/Python/Node/Ollama background processes
        should_kill = False
        if name in ['python.exe', 'pythonw.exe', 'ollama.exe', 'llama-server.exe', 'node.exe', 'chroma.exe']:
            should_kill = True
            
        if should_kill:
            proc.kill()
            killed.append((pid, name, cmdline[:80]))
            
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Terminated {len(killed)} non-Salad processes:")
for pid, name, preview in killed:
    print(f" - [PID {pid}] {name}: {preview}")
