import socket
import struct
import time
import sys

SERVER_IP = "192.168.10.1"
OFFER_IP = "192.168.10.2"
NETMASK = "255.255.255.0"
ROUTER = "192.168.10.1"
DNS_PRIMARY = "192.168.10.1"
DNS_SECONDARY = "1.1.1.1"
LEASE_TIME = 86400  # 24 hours
MAGIC_COOKIE = b"\x63\x82\x53\x63"

def ip_to_bytes(ip_str):
    return bytes(map(int, ip_str.split(".")))

def parse_options(options_bytes):
    opts = {}
    i = 0
    while i < len(options_bytes):
        tag = options_bytes[i]
        if tag == 255:  # End
            break
        if tag == 0:  # Pad
            i += 1
            continue
        if i + 1 >= len(options_bytes):
            break
        length = options_bytes[i + 1]
        val = options_bytes[i + 2 : i + 2 + length]
        opts[tag] = val
        i += 2 + length
    return opts

def build_reply(xid, chaddr, msg_type):
    packet = bytearray()
    packet += struct.pack("!BBBBIHH", 2, 1, 6, 0, xid, 0, 0x8000)
    packet += b"\x00\x00\x00\x00"  # ciaddr
    packet += ip_to_bytes(OFFER_IP)  # yiaddr
    packet += ip_to_bytes(SERVER_IP)  # siaddr
    packet += b"\x00\x00\x00\x00"  # giaddr
    packet += chaddr  # 16 bytes client hardware address
    packet += b"\x00" * 64  # sname
    packet += b"\x00" * 128  # file
    packet += MAGIC_COOKIE

    # Option 53: DHCP Message Type (2=OFFER, 5=ACK)
    packet += bytes([53, 1, msg_type])
    # Option 54: Server Identifier
    packet += bytes([54, 4]) + ip_to_bytes(SERVER_IP)
    # Option 51: Lease Time
    packet += bytes([51, 4]) + struct.pack("!I", LEASE_TIME)
    # Option 1: Subnet Mask
    packet += bytes([1, 4]) + ip_to_bytes(NETMASK)
    # Option 3: Router
    packet += bytes([3, 4]) + ip_to_bytes(ROUTER)
    # Option 6: DNS Servers
    packet += bytes([6, 8]) + ip_to_bytes(DNS_PRIMARY) + ip_to_bytes(DNS_SECONDARY)
    # Option 255: End
    packet += b"\xff"

    if len(packet) < 300:
        packet += b"\x00" * (300 - len(packet))

    return bytes(packet)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", 67))
    sock.settimeout(1.0)

    print(f"[*] Xbox Auto-DHCP & NAT Gateway Daemon running on {SERVER_IP}...", flush=True)

    while True:
        try:
            data, addr = sock.recvfrom(2048)
            if len(data) < 240:
                continue

            cookie_idx = data.find(MAGIC_COOKIE)
            if cookie_idx == -1:
                continue

            xid = struct.unpack("!I", data[4:8])[0]
            chaddr = data[28:44]
            mac_str = ":".join(f"{b:02x}" for b in chaddr[:6])

            options = parse_options(data[cookie_idx + 4 :])
            msg_type = options.get(53, b"\x00")[0]

            if msg_type == 1:  # DHCPDISCOVER
                print(f"[DHCPDISCOVER] from {mac_str} (XID: 0x{xid:08x}) -> Sending DHCPOFFER {OFFER_IP}", flush=True)
                offer = build_reply(xid, chaddr, msg_type=2)
                for dest in [("255.255.255.255", 68), ("192.168.10.255", 68), (OFFER_IP, 68)]:
                    try:
                        sock.sendto(offer, dest)
                    except Exception:
                        pass

            elif msg_type == 3:  # DHCPREQUEST
                print(f"[DHCPREQUEST] from {mac_str} -> Sending DHCPACK for {OFFER_IP}!", flush=True)
                ack = build_reply(xid, chaddr, msg_type=5)
                for dest in [("255.255.255.255", 68), ("192.168.10.255", 68), (OFFER_IP, 68)]:
                    try:
                        sock.sendto(ack, dest)
                    except Exception:
                        pass
                print(f"[+] LEASE CONFIRMED: {OFFER_IP} assigned to {mac_str}", flush=True)

        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(1)

    sock.close()

if __name__ == "__main__":
    main()
