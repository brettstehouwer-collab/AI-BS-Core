import socket

target = "192.168.10.2"
ports = [21, 53, 80, 88, 443, 3074, 5000, 8080, 11443, 11444, 42017, 2869, 10243]

print(f"Scanning common Xbox ports on {target}...")
for p in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    res = s.connect_ex((target, p))
    if res == 0:
        print(f"  [+] Port {p} is OPEN!")
    s.close()
print("Scan complete.")
