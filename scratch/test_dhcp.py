import socket
import struct

# Small DHCP server for 192.168.10.x direct link
# PC IP: 192.168.10.1
# Xbox IP to offer: 192.168.10.2

SERVER_IP = "192.168.10.1"
OFFER_IP = "192.168.10.2"
NETMASK = "255.255.255.0"
GATEWAY = "192.168.10.1"
DNS = "1.1.1.1"

def ip_to_bytes(ip_str):
    return bytes(map(int, ip_str.split(".")))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(("", 67))
sock.settimeout(3.0)

print("DHCP listener ready on UDP 67...")
try:
    data, addr = sock.recvfrom(2048)
    xid = data[4:8]
    client_mac = data[28:34]
    mac_str = ":".join(f"{b:02x}" for b in client_mac)
    print(f"Captured DHCP request from MAC: {mac_str}, XID: {xid.hex()}")
except socket.timeout:
    print("No DHCP request received in 3s.")
finally:
    sock.close()
