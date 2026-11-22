import threading
import time
import sys
import os

from xbox_dns_injector import XboxDNSInjector
from xbox_server_injector import RakNetServerInjector

def main():
    print("=" * 80)
    print(" [*] TIER 2 MASTER CONTROLLER: DNS INTERCEPTOR & MULTIPLAYER SERVER INJECTOR")
    print(" [*] Host Subnet: 192.168.10.1 (PC Gateway & DNS Resolver)")
    print(" [*] Target Console: 192.168.10.2 (Xbox One @ 1 Gbps)")
    print("=" * 80)

    dns_service = XboxDNSInjector(bind_ip="192.168.10.1", bind_port=53)
    server_service = RakNetServerInjector(bind_ip="192.168.10.1")

    # Thread 1: DNS Service
    t_dns = threading.Thread(target=dns_service.start, daemon=True)
    t_dns.start()

    # Thread 2: Server Proxy Service
    t_srv = threading.Thread(target=server_service.start, daemon=True)
    t_srv.start()

    time.sleep(1)
    print("\n [+] Both Tier 2 Services running in synchronized multi-threaded event loop.")
    print(" [+] Point your Xbox DNS to 192.168.10.1 (already assigned via auto-DHCP).")
    print(" [+] Press Ctrl+C at any time to halt services.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Tier 2 Services...")
        dns_service.stop()
        server_service.stop()
        print("[+] All Tier 2 Services safely terminated.")

if __name__ == "__main__":
    main()
