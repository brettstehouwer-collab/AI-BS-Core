import socket
import urllib.request
import json
import psutil

print("==================================================")
print("BROADCAST KERNEL DAEMON (PORT 8005) DEEP AUDIT")
print("==================================================")
try:
    with socket.create_connection(("127.0.0.1", 8005), timeout=1.0):
        print("[SOCKET]: Port 8005 is OPEN and LISTENING.")
except Exception as e:
    print(f"[SOCKET ERROR]: Port 8005 connection failed: {e}")

# Find PID listening on 8005
pids_8005 = []
for conn in psutil.net_connections(kind="tcp"):
    if conn.laddr.port == 8005 and conn.status == "LISTEN":
        pids_8005.append(conn.pid)

for pid in pids_8005:
    try:
        proc = psutil.Process(pid)
        print(f"Process: {proc.name()} (PID: {pid})")
        print(f"CommandLine: {' '.join(proc.cmdline()[:3])}...")
        print(f"Memory RSS: {proc.memory_info().rss / (1024*1024):.2f} MB")
        print(f"Status: {proc.status()}")
    except Exception as e:
        print(f"PID {pid} info error: {e}")

# Test HTTP Request to 8005
try:
    req = urllib.request.Request("http://127.0.0.1:8005/openapi.json")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        schema = json.loads(resp.read().decode())
        title = schema.get("info", {}).get("title", "")
        routes = list(schema.get("paths", {}).keys())
        print(f"Title: {title}")
        print(f"Available HTTP/WebSocket Routes ({len(routes)}): {routes[:8]}...")
except Exception as e:
    print(f"HTTP Probe 8005: {e}")

print("\n==================================================")
print("BROADCAST NVENC HARDWARE ENCODER (PORT 8088) AUDIT")
print("==================================================")
try:
    with socket.create_connection(("127.0.0.1", 8088), timeout=1.0):
        print("[SOCKET]: Port 8088 is OPEN and LISTENING.")
except Exception as e:
    print(f"[SOCKET ERROR]: Port 8088 connection failed: {e}")

# Find PID listening on 8088
pids_8088 = []
for conn in psutil.net_connections(kind="tcp"):
    if conn.laddr.port == 8088 and conn.status == "LISTEN":
        pids_8088.append(conn.pid)

for pid in pids_8088:
    try:
        proc = psutil.Process(pid)
        print(f"Process: {proc.name()} (PID: {pid})")
        print(f"CommandLine: {' '.join(proc.cmdline()[:3])}...")
        print(f"Memory RSS: {proc.memory_info().rss / (1024*1024):.2f} MB")
        print(f"Status: {proc.status()}")
    except Exception as e:
        print(f"PID {pid} info error: {e}")

# Test HTTP Request to 8088
try:
    req = urllib.request.Request("http://127.0.0.1:8088/openapi.json")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        schema = json.loads(resp.read().decode())
        title = schema.get("info", {}).get("title", "")
        routes = list(schema.get("paths", {}).keys())
        print(f"Title: {title}")
        print(f"Available HTTP/WebSocket Routes ({len(routes)}): {routes[:8]}...")
except Exception as e:
    print(f"HTTP Probe 8088: {e}")
