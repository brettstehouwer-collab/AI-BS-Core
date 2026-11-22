import socket
import struct
import time
import subprocess

def test_dns_lookup(domain, server="192.168.10.1"):
    # Build simple DNS query packet
    tx_id = b"\x12\x34"
    flags = b"\x01\x00" # Standard query, recursion desired
    counts = b"\x00\x01\x00\x00\x00\x00\x00\x00" # QD=1
    
    # QNAME
    qname = bytearray()
    for part in domain.split("."):
        qname.append(len(part))
        qname.extend(part.encode("ascii"))
    qname.append(0)
    
    qtype = b"\x00\x01" # Type A
    qclass = b"\x00\x01" # Class IN
    
    query = tx_id + flags + counts + qname + qtype + qclass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    s.sendto(query, (server, 53))
    
    try:
        resp, _ = s.recvfrom(2048)
        # Extract IP from last 4 bytes of response
        if len(resp) >= 16:
            ip = socket.inet_ntoa(resp[-4:])
            return ip
    except Exception as e:
        return f"Error: {e}"
    finally:
        s.close()
    return "No response"

def test_raknet_ping(server="192.168.10.1", port=19132):
    magic = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"
    ping = bytearray()
    ping.append(0x01) # ID_UNCONNECTED_PING
    ping += struct.pack("!Q", int(time.time() * 1000))
    ping += magic
    ping += struct.pack("!Q", 0x987654321)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    s.sendto(ping, (server, port))

    try:
        resp, _ = s.recvfrom(2048)
        if resp and resp[0] == 0x1C: # ID_UNCONNECTED_PONG
            str_len = struct.unpack("!H", resp[33:35])[0]
            motd = resp[35:35+str_len].decode("utf-8", errors="replace")
            return motd
    except Exception as e:
        return f"Error: {e}"
    finally:
        s.close()
    return "No response"

if __name__ == "__main__":
    print("Sending test query for intercepted domain 'play.inpvp.net'...")
    res1 = test_dns_lookup("play.inpvp.net")
    print(f"  -> Resolved 'play.inpvp.net' to: {res1}")

    print("Sending test query for passthrough domain 'google.com'...")
    res2 = test_dns_lookup("google.com")
    print(f"  -> Resolved 'google.com' to: {res2}")

    print("Sending test RakNet Unconnected Ping to port 19132...")
    res3 = test_raknet_ping()
    print(f"  -> Received Server MOTD: {res3}")
