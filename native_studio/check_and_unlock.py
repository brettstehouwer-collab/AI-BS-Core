import os
import sys
import psutil

target_dir = r"c:\ai-bs\native_studio\dist".lower()
print(f"Scanning for processes locking files in: {target_dir}")

killed = []
for p in psutil.process_iter(['pid', 'name']):
    try:
        pid = p.info['pid']
        name = p.info['name']
        if pid in (0, 4):
            continue
        proc = psutil.Process(pid)
        # Check exe
        try:
            exe = proc.exe().lower()
            if target_dir in exe or "ai_bs_studio" in exe:
                print(f"Killing matching exe process: PID {pid} ({name}) -> {exe}")
                proc.kill()
                killed.append(pid)
                continue
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        # Check memory maps (DLLs / pyd)
        try:
            maps = proc.memory_maps()
            for m in maps:
                if m.path and target_dir in m.path.lower():
                    print(f"Killing process with mapped file: PID {pid} ({name}) -> {m.path}")
                    proc.kill()
                    killed.append(pid)
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Done. Terminated {len(killed)} processes.")
