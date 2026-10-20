import psutil

for pid in [15744, 44140, 38296, 29084]:
    try:
        p = psutil.Process(pid)
        print(f"PID={pid} Name={p.name()} Cwd={p.cwd()} Cmd={' '.join(p.cmdline())}")
    except psutil.NoSuchProcess:
        print(f"PID={pid} exited")
    except Exception as e:
        print(f"PID={pid} error: {e}")
