import socket
import time

target_ip = "192.168.10.2"
port = 11443

print(f"Waiting for Xbox Device Portal (HTTPS {target_ip}:{port}) to open...")
start = time.time()
connected = False

while time.time() - start < 45:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    res = s.connect_ex((target_ip, port))
    s.close()
    if res == 0:
        connected = True
        break
    time.sleep(1.0)

if connected:
    print(f"\n[+] SUCCESS: Xbox Device Portal is OPEN on port {port}!")
else:
    print(f"\n[-] Port {port} not open yet (still booting into Dev Mode or portal needs enabling in Dev Home).")
