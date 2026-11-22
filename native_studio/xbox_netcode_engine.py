import socket
import struct
import time
import threading
import sys
from collections import defaultdict

# ==============================================================================
# TIER 1: LOW-LEVEL PACKET DISSECTION, CHECKSUM & NETCODE ENGINE
# Architecture: Direct Raw IP Socket & Stateful Flow Tracker on 192.168.10.1
# ==============================================================================

def calculate_checksum(msg: bytes) -> int:
    """
    Standard RFC 1071 One's Complement Internet Checksum Algorithm.
    Used by IPv4, ICMP, UDP, and TCP headers for hardware/software verification.
    """
    if len(msg) % 2 == 1:
        msg += b"\x00"
    
    total = sum(struct.unpack("!%dH" % (len(msg) // 2), msg))
    while (total >> 16) > 0:
        total = (total & 0xFFFF) + (total >> 16)
    
    return ~total & 0xFFFF

class PacketDissector:
    """Decodes low-level binary framing into structured protocol metrics."""

    @staticmethod
    def dissect_ipv4(packet_bytes: bytes):
        if len(packet_bytes) < 20:
            return None
        
        v_ihl = packet_bytes[0]
        version = v_ihl >> 4
        ihl = (v_ihl & 0x0F) * 4
        tos, total_len, identification, flags_frag, ttl, protocol, hdr_chk = struct.unpack("!BHHHBBH", packet_bytes[1:12])
        src_ip = socket.inet_ntoa(packet_bytes[12:16])
        dst_ip = socket.inet_ntoa(packet_bytes[16:20])
        payload = packet_bytes[ihl:total_len]
        
        # Verify IP header checksum
        raw_header = packet_bytes[:10] + b"\x00\x00" + packet_bytes[12:ihl]
        expected_chk = calculate_checksum(raw_header)
        is_chk_valid = (expected_chk == hdr_chk)

        return {
            "version": version,
            "ihl": ihl,
            "tos": tos,
            "total_len": total_len,
            "id": identification,
            "ttl": ttl,
            "protocol": protocol,
            "checksum": hdr_chk,
            "checksum_valid": is_chk_valid,
            "src": src_ip,
            "dst": dst_ip,
            "payload": payload
        }

    @staticmethod
    def dissect_udp(payload_bytes: bytes):
        if len(payload_bytes) < 8:
            return None
        src_port, dst_port, length, chk = struct.unpack("!HHHH", payload_bytes[:8])
        data = payload_bytes[8:]
        return {
            "src_port": src_port,
            "dst_port": dst_port,
            "length": length,
            "checksum": chk,
            "data": data
        }

    @staticmethod
    def dissect_icmp(payload_bytes: bytes):
        if len(payload_bytes) < 8:
            return None
        icmp_type, code, chk, ident, seq = struct.unpack("!BBHHH", payload_bytes[:8])
        return {
            "type": icmp_type,
            "code": code,
            "checksum": chk,
            "id": ident,
            "seq": seq,
            "data": payload_bytes[8:]
        }

    @staticmethod
    def dissect_tcp(payload_bytes: bytes):
        if len(payload_bytes) < 20:
            return None
        src_port, dst_port, seq, ack, offset_flags, win, chk, urg = struct.unpack("!HHIIHHHH", payload_bytes[:20])
        data_offset = (offset_flags >> 12) * 4
        flags = offset_flags & 0x01FF
        
        flag_names = []
        if flags & 0x0002: flag_names.append("SYN")
        if flags & 0x0010: flag_names.append("ACK")
        if flags & 0x0001: flag_names.append("FIN")
        if flags & 0x0004: flag_names.append("RST")
        if flags & 0x0008: flag_names.append("PSH")
        if flags & 0x0020: flag_names.append("URG")

        return {
            "src_port": src_port,
            "dst_port": dst_port,
            "seq": seq,
            "ack": ack,
            "flags": ",".join(flag_names) or "NONE",
            "window": win,
            "checksum": chk,
            "data": payload_bytes[data_offset:]
        }

class NetcodeAnalyzer:
    """Stateful traffic and latency profiling for console communications."""

    def __init__(self, bind_ip="192.168.10.1", target_ip="192.168.10.2"):
        self.bind_ip = bind_ip
        self.target_ip = target_ip
        self.running = False
        self.flow_stats = defaultdict(lambda: {"packets": 0, "bytes": 0, "last_seen": 0, "jitter_samples": []})
        self.total_packets = 0
        self.total_bytes = 0

    def start(self, duration_sec=None):
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        raw_sock.bind((self.bind_ip, 0))
        raw_sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        raw_sock.settimeout(0.5)

        self.running = True
        start_time = time.time()

        print("=" * 80)
        print(f" [!] TIER 1 NETCODE ENGINE INITIALIZED ON {self.bind_ip}")
        print(f" [!] Target Console Filter: {self.target_ip}")
        print(" [!] Intercepting raw IP frames, validating checksums & calculating jitter...")
        print("=" * 80)
        print(f"{'TIMESTAMP':<10} | {'PROTOCOL':<6} | {'SOURCE':<21} -> {'DESTINATION':<21} | {'SIZE':<5} | {'METRICS'}")
        print("-" * 80)

        try:
            while self.running:
                if duration_sec and (time.time() - start_time) >= duration_sec:
                    break
                try:
                    raw_data, _ = raw_sock.recvfrom(65535)
                except socket.timeout:
                    continue

                ip = PacketDissector.dissect_ipv4(raw_data)
                if not ip:
                    continue

                # Filter packets involving target Xbox console
                if ip["src"] != self.target_ip and ip["dst"] != self.target_ip:
                    continue

                now = time.time()
                self.total_packets += 1
                self.total_bytes += ip["total_len"]

                flow_key = (ip["src"], ip["dst"], ip["protocol"])
                stat = self.flow_stats[flow_key]
                if stat["last_seen"] > 0:
                    delta_ms = (now - stat["last_seen"]) * 1000.0
                    stat["jitter_samples"].append(delta_ms)
                    if len(stat["jitter_samples"]) > 20:
                        stat["jitter_samples"].pop(0)
                stat["packets"] += 1
                stat["bytes"] += ip["total_len"]
                stat["last_seen"] = now

                # Dissect layer 4
                proto_name = "RAW"
                details = ""
                src_endpoint = f"{ip['src']}"
                dst_endpoint = f"{ip['dst']}"

                if ip["protocol"] == 1:  # ICMP
                    proto_name = "ICMP"
                    icmp = PacketDissector.dissect_icmp(ip["payload"])
                    if icmp:
                        t_name = "Echo Req" if icmp["type"] == 8 else "Echo Rep" if icmp["type"] == 0 else f"T{icmp['type']}"
                        details = f"Type={t_name} Seq={icmp['seq']} Chk=0x{icmp['checksum']:04x}"
                elif ip["protocol"] == 17:  # UDP
                    proto_name = "UDP"
                    udp = PacketDissector.dissect_udp(ip["payload"])
                    if udp:
                        src_endpoint += f":{udp['src_port']}"
                        dst_endpoint += f":{udp['dst_port']}"
                        details = f"Len={udp['length']} Chk=0x{udp['checksum']:04x}"
                elif ip["protocol"] == 6:  # TCP
                    proto_name = "TCP"
                    tcp = PacketDissector.dissect_tcp(ip["payload"])
                    if tcp:
                        src_endpoint += f":{tcp['src_port']}"
                        dst_endpoint += f":{tcp['dst_port']}"
                        details = f"Flags=[{tcp['flags']}] Seq={tcp['seq']} Win={tcp['window']}"

                t_str = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
                chk_flag = "OK" if ip["checksum_valid"] else "BAD"
                print(f"{t_str:<10} | {proto_name:<6} | {src_endpoint:<21} -> {dst_endpoint:<21} | {ip['total_len']:<5} | {details} [{chk_flag}]")

        finally:
            raw_sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            raw_sock.close()
            self._print_summary()

    def _print_summary(self):
        print("\n" + "=" * 80)
        print(" [!] TIER 1 TRAFFIC PROFILING & SESSION SUMMARY")
        print("=" * 80)
        print(f" Total Captured Frames: {self.total_packets}")
        print(f" Total Wire Volume:     {self.total_bytes / 1024:.2f} KB ({self.total_bytes} bytes)")
        print("\n Active Session Flows:")
        for (src, dst, proto), data in self.flow_stats.items():
            p_name = {1: "ICMP", 6: "TCP", 17: "UDP"}.get(proto, f"Proto-{proto}")
            avg_jitter = (sum(data["jitter_samples"]) / len(data["jitter_samples"])) if data["jitter_samples"] else 0.0
            print(f"  * {src} -> {dst} [{p_name}]: {data['packets']} pkts, {data['bytes']} bytes | Avg Delta: {avg_jitter:.2f} ms")
        print("=" * 80)

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    engine = NetcodeAnalyzer()
    engine.start(duration)
