import socket
import time

s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
s.bind(("192.168.10.1", 0))
s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
s.settimeout(4.0)

print("Listening on 192.168.10.1 for 4 seconds...")
start = time.time()
try:
    while time.time() - start < 4:
        data, addr = s.recvfrom(65535)
        if addr[0] != "192.168.10.1":
            print(f"Packet received from: {addr[0]} size: {len(data)}")
except socket.timeout:
    pass
finally:
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
    s.close()
print("Finished listening.")
