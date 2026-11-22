import socket
import struct
import time
import json
import os
import sys
import threading

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "xbox_dns_config.json")
RAKNET_MAGIC = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading config: {e}")
    return {
        "server_proxy": {
            "listen_port": 19132,
            "target_server_host": "play.cubecraft.net",
            "target_server_port": 19132,
            "custom_motd": "§6AI-BS §bCustom Server Bridge §r[1 Gbps]"
        }
    }

class RakNetServerInjector:
    def __init__(self, bind_ip="192.168.10.1"):
        self.bind_ip = bind_ip
        self.config = load_config()
        self.proxy_cfg = self.config.get("server_proxy", {})
        self.listen_port = self.proxy_cfg.get("listen_port", 19132)
        self.sock = None
        self.running = False
        self.client_sessions = {} # client_addr -> (target_sock, last_activity)

    def build_pong(self, client_time, motd_str):
        packet = bytearray()
        packet.append(0x1C) # ID_UNCONNECTED_PONG
        packet += client_time # 8 bytes echoed timestamp
        packet += struct.pack("!Q", 0x123456789ABCDEF0) # Server GUID
        packet += RAKNET_MAGIC
        
        motd_bytes = motd_str.encode("utf-8")
        packet += struct.pack("!H", len(motd_bytes))
        packet += motd_bytes
        return bytes(packet)

    def forward_target_to_client(self, target_sock, client_addr):
        while self.running:
            try:
                data, _ = target_sock.recvfrom(65535)
                if not data:
                    break
                self.sock.sendto(data, client_addr)
            except Exception:
                break
        target_sock.close()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind_ip, self.listen_port))
        self.sock.settimeout(0.5)
        self.running = True

        motd = self.proxy_cfg.get("custom_motd", "§6AI-BS §bCustom Server Bridge")
        target_host = self.proxy_cfg.get("target_server_host", "play.cubecraft.net")
        target_port = self.proxy_cfg.get("target_server_port", 19132)

        print("=" * 80)
        print(f" [*] TIER 2: RAKNET MULTIPLAYER SERVER INJECTOR ACTIVE ON {self.bind_ip}:{self.listen_port}")
        print(f" [*] Injected MOTD:     {motd}")
        print(f" [*] Forwarding Target: {target_host}:{target_port}")
        print("=" * 80)

        # Pre-resolve target IP
        try:
            target_ip = socket.gethostbyname(target_host)
            print(f" [*] Target Server IP:  {target_ip}")
        except Exception as e:
            target_ip = target_host
            print(f" [!] Warning: Could not pre-resolve {target_host}: {e}")

        while self.running:
            try:
                data, client_addr = self.sock.recvfrom(65535)
                if not data:
                    continue

                packet_id = data[0]

                # 0x01 or 0x02 = Unconnected Ping
                if packet_id in (0x01, 0x02) and len(data) >= 25:
                    client_time = data[1:9]
                    server_motd = f"MCPE;{motd};589;1.20.0;0;100;123456789;Dedicated;Survival;1;{self.listen_port};19133;"
                    pong = self.build_pong(client_time, server_motd)
                    self.sock.sendto(pong, client_addr)
                    # print(f" [*] [PING-PONG] Responded to Xbox server list ping from {client_addr[0]}")
                    continue

                # Game session packet -> Relay to Target Server
                if client_addr not in self.client_sessions:
                    print(f" [+] [NEW SESSION] Xbox ({client_addr[0]}:{client_addr[1]}) connecting -> Relay to {target_ip}:{target_port}")
                    t_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    t_sock.settimeout(10.0)
                    self.client_sessions[client_addr] = t_sock

                    # Spawn worker to relay replies from target server back to client
                    t = threading.Thread(target=self.forward_target_to_client, args=(t_sock, client_addr), daemon=True)
                    t.start()

                target_sock = self.client_sessions[client_addr]
                target_sock.sendto(data, (target_ip, target_port))

            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[!] Server Proxy Loop Error: {e}")
                time.sleep(0.5)

        self.stop()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
        for s in self.client_sessions.values():
            try: s.close()
            except: pass
        print("\nServer Injector stopped.")

if __name__ == "__main__":
    injector = RakNetServerInjector()
    injector.start()
