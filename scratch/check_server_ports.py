import psutil
import socket

print("=== RUNNING TARGET PROCESSES ===")
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        name = p.info['name'].lower() if p.info['name'] else ''
        if any(k in name for k in ['cloudflared', 'nginx', 'python', 'node', 'uvicorn', 'caddy', 'httpd']):
            print(f"PID: {p.info['pid']} | Name: {p.info['name']} | Cmd: {p.info['cmdline']}")
    except Exception:
        pass

print("\n=== CHECKING LOCAL PORTS ===")
for port in [80, 443, 8000, 8080, 8188, 3000, 5000, 8443, 8081]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    res = s.connect_ex(('127.0.0.1', port))
    s.close()
    status = "LISTENING" if res == 0 else "CLOSED"
    print(f"Port {port}: {status}")
