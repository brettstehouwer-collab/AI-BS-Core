import socket
import struct
import time
import threading
import sys

# ==============================================================================
# TIER 1: IN-LINE TRAFFIC SHAPER & PROTOCOL MANIPULATOR
# Capable of transparently proxying, delaying, inspecting, or mutating UDP payloads
# ==============================================================================

class NetcodeProxy:
    def __init__(self, listen_host="192.168.10.1", listen_port=3074, target_host="192.168.10.2", target_port=3074, latency_ms=0):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.latency_ms = latency_ms
        self.running = False
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_host, self.listen_port))
        self.running = True

        print("=" * 75)
        print(" [*] TIER 1 IN-LINE UDP PROXY & TRAFFIC SHAPER")
        print(f" [*] Listening on:  {self.listen_host}:{self.listen_port}")
        print(f" [*] Forwarding to: {self.target_host}:{self.target_port}")
        print(f" [*] Synthetic Lag: {self.latency_ms} ms")
        print("=" * 75)

        client_endpoint = None

        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                
                # Apply synthetic latency if configured
                if self.latency_ms > 0:
                    time.sleep(self.latency_ms / 1000.0)

                # Route traffic bi-directionally
                if addr[0] == self.target_host:
                    # Packet came from Xbox -> route to external client
                    if client_endpoint:
                        self.sock.sendto(data, client_endpoint)
                        print(f"[XBOX -> EXT] {len(data)}B forwarded to {client_endpoint[0]}:{client_endpoint[1]}")
                else:
                    # Packet came from external client -> route to Xbox
                    client_endpoint = addr
                    self.sock.sendto(data, (self.target_host, self.target_port))
                    print(f"[EXT -> XBOX] {len(data)}B forwarded to {self.target_host}:{self.target_port}")

            except Exception as e:
                if self.running:
                    print(f"Proxy error: {e}")
                break

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3074
    lag = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    proxy = NetcodeProxy(listen_port=port, target_port=port, latency_ms=lag)
    try:
        proxy.start()
    except KeyboardInterrupt:
        proxy.stop()
        print("\nProxy stopped.")
