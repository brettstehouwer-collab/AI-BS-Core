import socket
import struct
import json
import time
import os
import sys

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "xbox_dns_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading config: {e}")
    return {
        "spoof_target_ip": "192.168.10.1",
        "upstream_dns": ["1.1.1.1", "8.8.8.8"],
        "intercept_domains": ["play.inpvp.net", "play.cubecraft.net", "geo.hivebedrock.network"],
        "custom_redirects": {}
    }

def decode_qname(data, offset):
    labels = []
    while True:
        length = data[offset]
        if length == 0:
            offset += 1
            break
        # Pointer check
        if (length & 0xC0) == 0xC0:
            pointer_offset = struct.unpack("!H", data[offset:offset+2])[0] & 0x3FFF
            sub_labels, _ = decode_qname(data, pointer_offset)
            labels.extend(sub_labels)
            offset += 2
            break
        offset += 1
        labels.append(data[offset:offset+length].decode("ascii", errors="replace"))
        offset += length
    return labels, offset

def build_dns_response(query_data, qname, answer_ip, qtype):
    # Header: Transaction ID, Flags (Standard response, no error: 0x8180)
    tx_id = query_data[:2]
    flags = b"\x81\x80"
    counts = struct.pack("!HHHH", 1, 1, 0, 0)  # QD=1, AN=1, NS=0, AR=0
    
    # Extract original question section
    offset = 12
    _, offset = decode_qname(query_data, offset)
    question_section = query_data[12:offset+4] # QNAME + QTYPE(2) + QCLASS(2)

    # Answer section using compression pointer to QNAME (0xc00c)
    ans_name = b"\xc0\x0c"
    ans_type = struct.pack("!H", 1)   # Type A
    ans_class = struct.pack("!H", 1)  # Class IN
    ans_ttl = struct.pack("!I", 10)   # TTL 10 seconds (short for dynamic changes)
    ip_bytes = socket.inet_aton(answer_ip)
    ans_rdlen = struct.pack("!H", len(ip_bytes))
    
    answer_section = ans_name + ans_type + ans_class + ans_ttl + ans_rdlen + ip_bytes
    return tx_id + flags + counts + question_section + answer_section

class XboxDNSInjector:
    def __init__(self, bind_ip="192.168.10.1", bind_port=53):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.config = load_config()
        self.sock = None
        self.running = False

    def query_upstream(self, raw_query, upstream_ip):
        try:
            up_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            up_sock.settimeout(2.0)
            up_sock.sendto(raw_query, (upstream_ip, 53))
            resp, _ = up_sock.recvfrom(2048)
            up_sock.close()
            return resp
        except Exception:
            return None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind_ip, self.bind_port))
        self.sock.settimeout(0.5)
        self.running = True

        print("=" * 80)
        print(f" [*] TIER 2: AUTHORITATIVE DNS INJECTOR ACTIVE ON {self.bind_ip}:{self.bind_port}")
        print(f" [*] Spoof Redirect Target: {self.config.get('spoof_target_ip', '192.168.10.1')}")
        print(f" [*] Intercept Target Domains: {len(self.config.get('intercept_domains', []))} domains active")
        print(f" [*] Upstream Resolvers:      {', '.join(self.config.get('upstream_dns', ['1.1.1.1']))}")
        print("=" * 80)

        while self.running:
            try:
                data, client_addr = self.sock.recvfrom(2048)
                if len(data) < 12:
                    continue

                labels, offset = decode_qname(data, 12)
                domain = ".".join(labels).lower()
                qtype = struct.unpack("!H", data[offset:offset+2])[0] if len(data) >= offset+2 else 1

                # Reload dynamic config occasionally
                if int(time.time()) % 10 == 0:
                    self.config = load_config()

                intercept_list = [d.lower() for d in self.config.get("intercept_domains", [])]
                custom_map = {k.lower(): v for k, v in self.config.get("custom_redirects", {}).items()}
                spoof_ip = self.config.get("spoof_target_ip", "192.168.10.1")

                # Check for intercept matches
                if domain in custom_map:
                    target = custom_map[domain]
                    print(f" [!] [CUSTOM REDIRECT] {domain:<30} -> {target} (for {client_addr[0]})", flush=True)
                    resp = build_dns_response(data, domain, target, qtype)
                    self.sock.sendto(resp, client_addr)

                elif domain in intercept_list:
                    print(f" [*] [INTERCEPT SPOOF] {domain:<30} -> {spoof_ip} (for {client_addr[0]})", flush=True)
                    resp = build_dns_response(data, domain, spoof_ip, qtype)
                    self.sock.sendto(resp, client_addr)

                else:
                    # Forward upstream
                    resp = None
                    for upstream in self.config.get("upstream_dns", ["1.1.1.1"]):
                        resp = self.query_upstream(data, upstream)
                        if resp:
                            break
                    if resp:
                        self.sock.sendto(resp, client_addr)
                        # Silent or compact log for clean terminal
                        # print(f" [.] [PASSTHROUGH]     {domain:<30} -> Upstream", flush=True)

            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[!] DNS Loop Error: {e}")
                time.sleep(0.5)

        self.stop()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
            print("\nDNS Injector stopped.")

if __name__ == "__main__":
    injector = XboxDNSInjector()
    injector.start()
