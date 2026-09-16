import socket
import psutil

ports = [8000, 8188, 11434, 5173, 8001, 8002, 8005, 3000]
print("=== PORT LISTENER AUDIT ===")
for p in ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    res = sock.connect_ex(("127.0.0.1", p))
    status = "ACTIVE / OCCUPIED" if res == 0 else "CLEAR"
    print(f"Port {p:5d}: {status}")
    sock.close()

print("\n=== RUNNING PYTHON PROCESSES ===")
python_count = 0
for proc in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        if proc.info["name"] and "python" in proc.info["name"].lower():
            python_count += 1
            cmd = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else "N/A"
            print(f"PID {proc.info['pid']:6d} | {cmd}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if python_count == 0:
    print("No running Python processes found.")

print("\n=== RUNNING OLLAMA / CLOUDFLARED PROCESSES ===")
for proc in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        name = proc.info["name"].lower() if proc.info["name"] else ""
        if any(k in name for k in ["cloudflared", "ollama"]):
            cmd = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else "N/A"
            print(f"PID {proc.info['pid']:6d} | Name: {name} | {cmd}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
