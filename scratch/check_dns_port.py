import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.bind(("192.168.10.1", 53))
    print("SUCCESS: Port 53 on 192.168.10.1 is available!")
    s.close()
except Exception as e:
    print(f"FAILED: {e}")
