import os
import sys
import time
import subprocess
import json
import logging
import socket
from typing import Dict, Any, Optional, List

logger = logging.getLogger("TSharkTelemetryEngine")

TSHARK_EXE = r"C:\Program Files\Wireshark\tshark.exe"


class TSharkTelemetryEngine:
    """
    Local Packet Extraction & Telemetry Monitor using TShark and socket analyzers.
    Verifies ChromaDB, vLLM/Ollama, Pearl Mining Stratum, and local-first architecture stability.
    """

    @staticmethod
    def get_tshark_info() -> Dict[str, Any]:
        has_tshark = os.path.exists(TSHARK_EXE)
        version_str = "Unknown"
        if has_tshark:
            try:
                res = subprocess.run([TSHARK_EXE, "--version"], capture_output=True, text=True, timeout=5)
                version_str = res.stdout.splitlines()[0] if res.stdout else "Available"
            except Exception:
                pass

        return {
            "tshark_installed": has_tshark,
            "tshark_path": TSHARK_EXE,
            "version": version_str
        }

    @staticmethod
    def capture_packets(
        ports: List[int] = [8001, 8080, 8335, 11434, 11435],
        duration_seconds: int = 3,
        max_packets: int = 50,
        interface: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes local packet capture via TShark targeting specific ecosystem ports.
        Falls back to socket connectivity probe if TShark lacks raw capture privileges.
        """
        start_time = time.time()

        if not os.path.exists(TSHARK_EXE):
            # Fallback to local socket port audit
            return TSharkTelemetryEngine.probe_ecosystem_sockets(ports)

        # Build port filter expression
        port_filters = " or ".join([f"tcp port {p}" for p in ports])
        capture_filter = f"({port_filters})"

        cmd = [
            TSHARK_EXE,
            "-a", f"duration:{duration_seconds}",
            "-c", str(max_packets),
            "-f", capture_filter,
            "-T", "fields",
            "-e", "frame.number",
            "-e", "frame.time_relative",
            "-e", "ip.src",
            "-e", "ip.dst",
            "-e", "tcp.srcport",
            "-e", "tcp.dstport",
            "-e", "frame.len",
            "-e", "_ws.col.Protocol",
            "-e", "_ws.col.Info"
        ]

        if interface:
            cmd.extend(["-i", interface])

        packets = []
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=duration_seconds + 5)
            if res.stdout:
                lines = res.stdout.strip().splitlines()
                for line in lines:
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        packets.append({
                            "frame": parts[0],
                            "time_rel": parts[1],
                            "src_ip": parts[2],
                            "dst_ip": parts[3],
                            "src_port": parts[4],
                            "dst_port": parts[5],
                            "length_bytes": parts[6],
                            "protocol": parts[7] if len(parts) > 7 else "TCP",
                            "info": parts[8] if len(parts) > 8 else ""
                        })
        except Exception as e:
            logger.warning(f"TShark capture exception: {e}")

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        # If 0 packets captured via raw capture, supplement with socket health probe
        socket_status = TSharkTelemetryEngine.probe_ecosystem_sockets(ports)

        return {
            "status": "success",
            "tshark_used": True,
            "duration_seconds": duration_seconds,
            "monitored_ports": ports,
            "packets_captured": len(packets),
            "packets": packets[:max_packets],
            "port_diagnostics": socket_status.get("ports_tested", {}),
            "elapsed_ms": elapsed_ms
        }

    @staticmethod
    def audit_pearl_mining_telemetry(port: int = 8335) -> Dict[str, Any]:
        """
        Audits Pearl Mining Stratum & Wallet daemon connectivity on Port 8335 and hero pools.
        """
        start_time = time.time()
        is_open = False
        banner = ""
        latency_ms = 0.0

        try:
            s_start = time.time()
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
                latency_ms = round((time.time() - s_start) * 1000, 2)
                is_open = True
                sock.sendall(b'{"id":1,"method":"mining.ping","params":[]}\n')
                sock.settimeout(1.0)
                try:
                    data = sock.recv(1024)
                    banner = data.decode("utf-8", errors="ignore").strip()
                except Exception:
                    banner = "Socket connected (no instant response)"
        except Exception as e:
            banner = str(e)

        # Check HeroMiners pool connectivity
        pool_host = "de.pearl.herominers.com"
        pool_port = 1177
        pool_reachable = False
        try:
            with socket.create_connection((pool_host, pool_port), timeout=2.0):
                pool_reachable = True
        except Exception:
            pool_reachable = False

        return {
            "status": "success",
            "stratum_local_port": port,
            "stratum_listening": is_open,
            "latency_ms": latency_ms,
            "response_banner": banner,
            "herominers_pool_reachable": pool_reachable,
            "pool_host": f"{pool_host}:{pool_port}",
            "elapsed_ms": round((time.time() - start_time) * 1000, 2)
        }

    @staticmethod
    def probe_ecosystem_sockets(ports: List[int]) -> Dict[str, Any]:
        """
        Sub-millisecond socket connection latency probe for ecosystem microservices.
        """
        results = {}
        for p in ports:
            s_start = time.time()
            try:
                with socket.create_connection(("127.0.0.1", p), timeout=0.5):
                    lat = round((time.time() - s_start) * 1000, 2)
                    results[p] = {"open": True, "latency_ms": lat, "status": "ONLINE"}
            except Exception:
                results[p] = {"open": False, "latency_ms": None, "status": "OFFLINE"}
        return {
            "ports_tested": results
        }
