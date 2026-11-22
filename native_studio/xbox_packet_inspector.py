import socket
import struct
import time
import sys

def parse_ip_header(data):
    version_ihl = data[0]
    ihl = (version_ihl & 0x0F) * 4
    total_len = struct.unpack("!H", data[2:4])[0]
    proto = data[9]
    src = socket.inet_ntoa(data[12:16])
    dst = socket.inet_ntoa(data[16:20])
    return ihl, proto, src, dst, total_len

def proto_name(num):
    table = {1: "ICMP", 6: "TCP", 17: "UDP", 2: "IGMP"}
    return table.get(num, f"Proto-{num}")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
    s.bind(("192.168.10.1", 0))
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    
    print("=" * 65)
    print(" [*] Xbox Wire-Speed Packet Sniffer & Netcode Inspector")
    print(" [*] Bound to: 192.168.10.1 (Realtek 2.5GbE @ 1Gbps)")
    print(" [*] Target: 192.168.10.2 (Xbox One)")
    print(" [*] Press Ctrl+C to stop")
    print("=" * 65)

    pkt_count = 0
    try:
        while True:
            data, addr = s.recvfrom(65535)
            ihl, proto, src, dst, total_len = parse_ip_header(data)
            
            # Filter Xbox traffic
            if src == "192.168.10.2" or dst == "192.168.10.2":
                pkt_count += 1
                p_name = proto_name(proto)
                payload_len = total_len - ihl
                
                info = ""
                if proto == 1:  # ICMP
                    icmp_type = data[ihl]
                    info = "Echo Request" if icmp_type == 8 else "Echo Reply" if icmp_type == 0 else f"Type {icmp_type}"
                elif proto == 17 and len(data) >= ihl + 4:  # UDP
                    src_port, dst_port = struct.unpack("!HH", data[ihl : ihl + 4])
                    info = f"{src_port} -> {dst_port}"
                elif proto == 6 and len(data) >= ihl + 4:  # TCP
                    src_port, dst_port = struct.unpack("!HH", data[ihl : ihl + 4])
                    info = f"{src_port} -> {dst_port}"

                print(f"[{pkt_count:04d}] {src:<15} -> {dst:<15} | {p_name:<6} | {payload_len:4d}B | {info}")

    except KeyboardInterrupt:
        print("\nStopping sniffer.")
    finally:
        s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        s.close()

if __name__ == "__main__":
    main()
