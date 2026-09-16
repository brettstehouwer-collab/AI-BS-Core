"""
AI-BS Decoupled Network Telemetry & Kernel Npcap Wire Dissection Subsystem
Architecturally separates:
  1. L7 Application Transactions (HTTP & WebSocket lifecycles via ASGI middleware).
  2. L2/L3 Physical Wire Frames (promiscuous Scapy/Npcap packet capture with BPF filtering).
  3. L4 5-Tuple Conversational Flows (TCP/UDP sessions) with bi-directional correlation.

Features:
  - Explicit capture length qualifications: captured_frame_bytes, ip_bytes, transport_payload_bytes.
  - Distinct hash semantics: payload_sha256_in/out (full HTTP stream) vs frame_payload_sha256 (packet payload fragment).
  - Formal flow correlation: TRANSACTION <-> flow_id <-> FRAMES.
  - Granular TCP flag bitmask extraction (SYN, ACK, PSH, FIN, RST).
  - Active message-level WebSocket telemetry.
  - Auditable Stehouwer domain classification.
"""

import time
import uuid
import json
import asyncio
import hashlib
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger("ai_bs.network_telemetry")

# Optional Scapy/Npcap bindings with non-blocking fallback
try:
    from scapy.all import IP, TCP, UDP, AsyncSniffer, Ether, Raw, conf
    conf.use_pcap = True
    NPCAP_AVAILABLE = bool(getattr(conf, "use_pcap", False))
except (ImportError, Exception):
    NPCAP_AVAILABLE = False


def is_npcap_available() -> bool:
    global NPCAP_AVAILABLE
    if NPCAP_AVAILABLE:
        return True
    try:
        from scapy.all import conf
        conf.use_pcap = True
        NPCAP_AVAILABLE = bool(getattr(conf, "use_pcap", False))
        return NPCAP_AVAILABLE
    except Exception:
        return False


FLOW_IDLE_TIMEOUT_SECONDS: int = 60


def compute_canonical_flow_id(
    proto: Optional[str],
    src_ip: Optional[str],
    sport: Optional[int],
    dst_ip: Optional[str],
    dport: Optional[int]
) -> Optional[str]:
    """
    Computes a canonical, deterministic bidirectional 5-tuple identifier:
    {protocol}|{min_endpoint}|{max_endpoint}
    Returns None if endpoints are incomplete, unresolvable, or loopback 0.0.0.0.
    """
    if not proto or not src_ip or not dst_ip:
        return None
    if src_ip in ("0.0.0.0", "") or dst_ip in ("0.0.0.0", ""):
        return None
    ep_a = f"{src_ip}:{sport or 0}"
    ep_b = f"{dst_ip}:{dport or 0}"
    proto_clean = proto.upper().split("/")[0]
    endpoints = sorted([ep_a, ep_b])
    return f"{proto_clean}|{endpoints[0]}|{endpoints[1]}"


def get_tcp_flags(packet: Any) -> List[str]:
    """
    Extracts readable TCP flag names from Scapy packet.
    """
    if not packet.haslayer(TCP):
        return []
    flags = []
    f_val = packet[TCP].flags
    flag_map = {
        'F': 'FIN',
        'S': 'SYN',
        'R': 'RST',
        'P': 'PSH',
        'A': 'ACK',
        'U': 'URG',
        'E': 'ECE',
        'C': 'CWR'
    }
    for char, name in flag_map.items():
        if char in str(f_val):
            flags.append(name)
    return flags if flags else [str(f_val)]


SENSITIVE_HEADERS: Set[str] = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "password",
    "token",
    "secret"
}

TRUSTED_DOMAINS: Set[str] = {
    "stehouwer-publishing.com",
    "api.stehouwer-publishing.com",
    "stehouwer.live",
    "api.brettstehouwer.live"
}


class NetworkTelemetryEngine:
    def __init__(
        self,
        max_tx_buffer: int = 2000,
        max_frame_buffer: int = 4000,
        max_buffer_len: Optional[int] = None
    ):
        if max_buffer_len is not None:
            max_tx_buffer = max_buffer_len
            max_frame_buffer = max_buffer_len * 2

        self.max_tx_buffer = max_tx_buffer
        self.max_frame_buffer = max_frame_buffer
        self.lock = threading.Lock()

        # Decoupled In-Memory Ring Buffers
        self.transaction_buffer: deque = deque(maxlen=max_tx_buffer)
        self.frame_buffer: deque = deque(maxlen=max_frame_buffer)
        self.subscribers: List[asyncio.Queue] = []

        # L7 Application Metrics (ASGI HTTP & WS)
        self.total_transactions = 0
        self.http_body_bytes_in = 0
        self.http_body_bytes_out = 0
        self.status_codes: Dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
        self.route_counts: Dict[str, int] = {}
        self.asgi_latencies: deque = deque(maxlen=1000)  # Pure application duration
        self.active_websockets = 0
        self.websocket_messages = 0

        # L2/L3 Physical Wire Metrics (Npcap)
        self.total_frames = 0
        self.captured_frame_bytes = 0       # Total captured frame octets
        self.transport_payload_bytes = 0    # Transport Raw payload octets
        self.tcp_flags_counts: Dict[str, int] = {
            "SYN": 0, "ACK": 0, "PSH": 0, "FIN": 0, "RST": 0, "other": 0
        }
        self.endpoint_counts: Dict[str, int] = {}

        # Formal L4 Conversational Flow Correlation Tracker (5-tuple)
        self.flows: Dict[str, Dict[str, Any]] = {}

        # Stehouwer Publishing Domain Metrics (Auditable)
        self.stehouwer_trusted_transactions = 0
        self.stehouwer_heuristic_transactions = 0
        self.stehouwer_body_bytes_in = 0
        self.stehouwer_body_bytes_out = 0
        self.stehouwer_recent_digests: deque = deque(maxlen=50)

        # Capture Engine Configuration: "ASGI" | "NPCAP" | "HYBRID"
        self.capture_mode = "ASGI"
        self.sniffer: Optional[Any] = None
        self._sniffer_running = False
        self.active_interface: Optional[str] = None
        self.active_bpf: str = "tcp or udp"

    # Backward compatibility property aliases
    @property
    def buffer(self) -> deque:
        with self.lock:
            combined = list(self.transaction_buffer) + list(self.frame_buffer)
            combined.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return deque(combined[:self.max_tx_buffer])

    @property
    def total_requests(self) -> int:
        return self.total_transactions

    @property
    def total_bytes_in(self) -> int:
        return self.http_body_bytes_in

    @property
    def total_bytes_out(self) -> int:
        return self.http_body_bytes_out

    @property
    def wire_frame_bytes(self) -> int:
        return self.captured_frame_bytes

    @property
    def wire_payload_bytes(self) -> int:
        return self.transport_payload_bytes

    @property
    def stehouwer_packets_count(self) -> int:
        return self.stehouwer_trusted_transactions + self.stehouwer_heuristic_transactions

    @property
    def stehouwer_bytes_in(self) -> int:
        return self.stehouwer_body_bytes_in

    @property
    def stehouwer_bytes_out(self) -> int:
        return self.stehouwer_body_bytes_out

    @property
    def stehouwer_recent_hashes(self) -> deque:
        return self.stehouwer_recent_digests

    @property
    def latencies(self) -> deque:
        return self.asgi_latencies

    def set_mode(self, mode: str, interface: Optional[str] = None, bpf_filter: str = "tcp or udp") -> Dict[str, Any]:
        """
        Switches active capture engine between pure ASGI, Npcap raw wire promiscuous capture, or parallel Hybrid mode.
        """
        mode = mode.upper()
        if mode not in ["ASGI", "NPCAP", "HYBRID"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'ASGI', 'NPCAP', or 'HYBRID'.")

        if mode in ["NPCAP", "HYBRID"] and not is_npcap_available():
            raise RuntimeError("Npcap NDIS 6 driver not detected on host system. Operating in ASGI mode.")

        with self.lock:
            self.capture_mode = mode
            self.active_interface = interface
            self.active_bpf = bpf_filter
            if mode in ["NPCAP", "HYBRID"]:
                self._start_npcap_sniffer(interface=interface, bpf_filter=bpf_filter)
            else:
                self._stop_npcap_sniffer()

        return {
            "status": "success",
            "active_mode": self.capture_mode,
            "npcap_available": is_npcap_available(),
            "npcap_running": self._sniffer_running,
            "active_interface": self.active_interface,
            "bpf_filter": self.active_bpf
        }

    def _start_npcap_sniffer(self, interface: Optional[str], bpf_filter: str) -> None:
        if self._sniffer_running:
            self._stop_npcap_sniffer()

        def _packet_handler(packet: Any) -> None:
            now_iso = datetime.now(timezone.utc).isoformat()
            now_time = time.time()
            l2_meta = {}
            src_mac, dst_mac = "00:00:00:00:00:00", "00:00:00:00:00:00"

            if packet.haslayer(Ether):
                src_mac = packet[Ether].src
                dst_mac = packet[Ether].dst
                l2_meta = {"src_mac": src_mac, "dst_mac": dst_mac}

            proto = "RAW"
            src_ip, dst_ip = "0.0.0.0", "0.0.0.0"
            sport, dport = 0, 0
            ip_bytes = 0

            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                proto = f"IP/{packet[IP].proto}"
                ip_bytes = getattr(packet[IP], "len", len(packet[IP]))

            tcp_flags = []
            if packet.haslayer(TCP):
                proto = "TCP"
                sport = packet[TCP].sport
                dport = packet[TCP].dport
                tcp_flags = get_tcp_flags(packet)
            elif packet.haslayer(UDP):
                proto = "UDP"
                sport = packet[UDP].sport
                dport = packet[UDP].dport

            # Qualified Captured Frame Length (wirelen if provided by Npcap/Scapy, else serialized len)
            captured_frame_bytes = getattr(packet, "wirelen", None)
            if captured_frame_bytes is None:
                try:
                    captured_frame_bytes = len(bytes(packet))
                except Exception:
                    captured_frame_bytes = len(packet)

            # Transport Payload Bytes & Explicit Frame Payload SHA-256
            transport_payload_bytes = 0
            frame_payload_sha256 = None
            if packet.haslayer(Raw):
                payload = packet[Raw].load
                transport_payload_bytes = len(payload)
                if transport_payload_bytes > 0:
                    frame_payload_sha256 = hashlib.sha256(payload).hexdigest()

            captured_overhead_bytes = max(0, captured_frame_bytes - transport_payload_bytes)
            dst_endpoint = f"{dst_ip}:{dport}"
            src_endpoint = f"{src_ip}:{sport}"
            flow_id = compute_canonical_flow_id(proto, src_ip, sport, dst_ip, dport)

            is_stehouwer = (
                sport in [8080, 5173, 5174, 8000]
                or dport in [8080, 5173, 5174, 8000]
            )

            frame_id = f"frm_{int(now_time * 1000)}_{uuid.uuid4().hex[:12]}"

            rec = {
                "id": frame_id,
                "type": "FRAME",
                "timestamp": now_iso,
                "engine": "NPCAP_L2_L3",
                "protocol": proto,
                "transport": proto,
                "tcp_flags": tcp_flags,
                "endpoint": dst_endpoint,
                "src_endpoint": src_endpoint,
                "status_code": None,  # Strictly None: TCP frames are not HTTP responses
                "client_ip": src_ip,
                "client_id": "stehouwer_publishing" if is_stehouwer else "wire_capture",
                "origin_domain": src_endpoint,
                "is_stehouwer_publishing": is_stehouwer,
                "duration_ms": 0.0,
                "captured_frame_bytes": captured_frame_bytes,
                "ip_bytes": ip_bytes,
                "transport_payload_bytes": transport_payload_bytes,
                "captured_overhead_bytes": captured_overhead_bytes,
                "header_bytes": captured_overhead_bytes,
                "frame_payload_sha256": frame_payload_sha256,
                "flow_id": flow_id,
                "l2_meta": l2_meta,
                "sport": sport,
                "dport": dport,
                # Backward-compatibility aliases
                "frame_bytes": captured_frame_bytes,
                "payload_bytes": transport_payload_bytes,
                "payload_sha256": frame_payload_sha256,
                "method": proto,
                "path": dst_endpoint,
                "bytes_in": captured_frame_bytes if dport in [8080, 5173, 5174, 8000] else 0,
                "bytes_out": captured_frame_bytes if sport in [8080, 5173, 5174, 8000] else 0,
                "packet_hash_in": frame_payload_sha256 if dport in [8080, 5173, 5174, 8000] else None,
                "packet_hash_out": frame_payload_sha256 if sport in [8080, 5173, 5174, 8000] else None,
                "headers": None
            }
            self.record_frame(rec)

        try:
            self.sniffer = AsyncSniffer(
                iface=interface,
                prn=_packet_handler,
                filter=bpf_filter,
                store=False,
                promisc=True
            )
            self.sniffer.start()
            self._sniffer_running = True
            logger.info(f"Npcap L2/L3 Promiscuous Sniffer active on iface={interface or 'default'} bpf='{bpf_filter}'")
        except Exception as e:
            logger.error(f"Failed to start Npcap sniffer: {e}")
            self._sniffer_running = False

    def _stop_npcap_sniffer(self) -> None:
        if self.sniffer and self._sniffer_running:
            try:
                self.sniffer.stop()
            except Exception as e:
                logger.warning(f"Error stopping sniffer: {e}")
            self._sniffer_running = False
            self.sniffer = None

    def get_interfaces(self) -> List[Dict[str, Any]]:
        """
        Enumerates network interfaces on host via Scapy/Windows arch bindings.
        """
        interfaces = []
        try:
            from scapy.arch.windows import get_windows_if_list
            raw_ifs = get_windows_if_list()
            for iface in raw_ifs:
                interfaces.append({
                    "name": iface.get("name", ""),
                    "description": iface.get("description", ""),
                    "mac": iface.get("mac", ""),
                    "ips": iface.get("ips", []),
                    "guid": iface.get("guid", "")
                })
        except Exception as e:
            logger.warning(f"Failed to enumerate Windows interfaces: {e}")
        return interfaces

    def record_transaction(self, record: Dict[str, Any]):
        """
        Appends an L7 HTTP or WebSocket transaction to the transaction buffer,
        updates application metrics, and establishes formal flow correlation.
        """
        with self.lock:
            self.transaction_buffer.appendleft(record)
            self.total_transactions += 1
            body_in = record.get("body_bytes_in", record.get("bytes_in", 0))
            body_out = record.get("body_bytes_out", record.get("bytes_out", 0))
            self.http_body_bytes_in += body_in
            self.http_body_bytes_out += body_out

            # Status classification (strictly L7)
            code = record.get("status_code")
            if code is not None:
                if 200 <= code < 300:
                    self.status_codes["2xx"] += 1
                elif 300 <= code < 400:
                    self.status_codes["3xx"] += 1
                elif 400 <= code < 500:
                    self.status_codes["4xx"] += 1
                elif 500 <= code < 600:
                    self.status_codes["5xx"] += 1
                else:
                    self.status_codes["other"] += 1

            # Route frequency
            path = record.get("path", "/")
            self.route_counts[path] = self.route_counts.get(path, 0) + 1

            # Latency tracking: purely ASGI application duration
            dur = record.get("asgi_duration_ms", record.get("duration_ms", 0.0))
            if dur > 0:
                self.asgi_latencies.append(dur)

            # Flow Correlation Registration
            flow_id = record.get("flow_id")
            if flow_id:
                now_t = time.time()
                if flow_id not in self.flows:
                    self.flows[flow_id] = {
                        "flow_id": flow_id,
                        "protocol": "TCP",
                        "first_seen": now_t,
                        "last_seen": now_t,
                        "transaction_ids": [record["id"]],
                        "frame_ids": [],
                        "packets_count": 1,
                        "captured_frame_bytes": 0,
                        "transport_payload_bytes": 0,
                        "http_body_bytes_in": body_in,
                        "http_body_bytes_out": body_out
                    }
                else:
                    fl = self.flows[flow_id]
                    fl["last_seen"] = now_t
                    if record["id"] not in fl["transaction_ids"]:
                        fl["transaction_ids"].append(record["id"])
                    fl["http_body_bytes_in"] += body_in
                    fl["http_body_bytes_out"] += body_out

            # Stehouwer Publishing classification
            is_trusted = record.get("trusted_domain_match", False)
            is_heuristic = record.get("is_stehouwer_publishing", False) and not is_trusted

            if is_trusted:
                self.stehouwer_trusted_transactions += 1
                self.stehouwer_body_bytes_in += body_in
                self.stehouwer_body_bytes_out += body_out
            elif is_heuristic:
                self.stehouwer_heuristic_transactions += 1

            if is_trusted or is_heuristic:
                hash_in = record.get("payload_sha256_in", record.get("packet_hash_in"))
                hash_out = record.get("payload_sha256_out", record.get("packet_hash_out"))
                if hash_in or hash_out:
                    self.stehouwer_recent_digests.appendleft({
                        "timestamp": record.get("timestamp"),
                        "method": record.get("method"),
                        "path": record.get("path"),
                        "status_code": record.get("status_code"),
                        "hash_in": hash_in,
                        "hash_out": hash_out,
                        "bytes_in": body_in,
                        "bytes_out": body_out,
                        "engine": "ASGI",
                        "trusted": is_trusted,
                        "classification_reason": record.get("classification_reason", "unknown")
                    })

            self._dispatch_to_subscribers(record)

    def record_frame(self, record: Dict[str, Any]):
        """
        Appends an L2/L3 physical wire frame to the frame buffer,
        updates wire metrics, and establishes formal flow correlation.
        """
        with self.lock:
            self.frame_buffer.appendleft(record)
            self.total_frames += 1
            f_bytes = record.get("captured_frame_bytes", record.get("frame_bytes", 0))
            p_bytes = record.get("transport_payload_bytes", record.get("payload_bytes", 0))
            self.captured_frame_bytes += f_bytes
            self.transport_payload_bytes += p_bytes

            # TCP Flags distribution
            flags = record.get("tcp_flags", [])
            for flg in flags:
                if flg in self.tcp_flags_counts:
                    self.tcp_flags_counts[flg] += 1
                else:
                    self.tcp_flags_counts["other"] += 1

            # Endpoint distribution
            ep = record.get("endpoint", "unknown")
            self.endpoint_counts[ep] = self.endpoint_counts.get(ep, 0) + 1

            # Flow Correlation Registration with Lifecycle Tracking
            f_key = record.get("flow_id")
            if f_key:
                now_t = time.time()
                is_fin_or_rst = any(f in flags for f in ("FIN", "RST"))
                if f_key not in self.flows:
                    self.flows[f_key] = {
                        "flow_id": f_key,
                        "protocol": record.get("protocol"),
                        "src_endpoint": record.get("src_endpoint"),
                        "dst_endpoint": record.get("endpoint"),
                        "first_seen": now_t,
                        "last_seen": now_t,
                        "transaction_ids": [],
                        "frame_ids": [record["id"]],
                        "packets_count": 1,
                        "captured_frame_bytes": f_bytes,
                        "transport_payload_bytes": p_bytes,
                        "http_body_bytes_in": 0,
                        "http_body_bytes_out": 0,
                        "closed": is_fin_or_rst,
                        "closure_reason": ("FIN" if "FIN" in flags else "RST") if is_fin_or_rst else None
                    }
                else:
                    fl = self.flows[f_key]
                    fl["last_seen"] = now_t
                    fl["packets_count"] += 1
                    fl["frame_ids"].append(record["id"])
                    if len(fl["frame_ids"]) > 300:
                        fl["frame_ids"] = fl["frame_ids"][-300:]
                    fl["captured_frame_bytes"] = fl.get("captured_frame_bytes", 0) + f_bytes
                    fl["transport_payload_bytes"] = fl.get("transport_payload_bytes", 0) + p_bytes
                    if is_fin_or_rst:
                        fl["closed"] = True
                        fl["closure_reason"] = "FIN" if "FIN" in flags else "RST"

            # Stehouwer wire traffic
            if record.get("is_stehouwer_publishing"):
                p_hash = record.get("frame_payload_sha256", record.get("payload_sha256"))
                if p_hash:
                    self.stehouwer_recent_digests.appendleft({
                        "timestamp": record.get("timestamp"),
                        "method": record.get("transport"),
                        "path": record.get("endpoint"),
                        "status_code": None,
                        "hash_in": p_hash if record.get("bytes_in", 0) > 0 else None,
                        "hash_out": p_hash if record.get("bytes_out", 0) > 0 else None,
                        "bytes_in": record.get("bytes_in", 0),
                        "bytes_out": record.get("bytes_out", 0),
                        "engine": "NPCAP_L2_L3",
                        "trusted": False,
                        "classification_reason": "port_binding"
                    })

            self._dispatch_to_subscribers(record)

    def get_flow_correlation(self, flow_id: Optional[str] = None, transaction_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Resolves formal correlation between an HTTP transaction and all physical wire frames that carried it.
        """
        with self.lock:
            target_flow_id = flow_id
            target_tx = None

            if transaction_id and not target_flow_id:
                for tx in self.transaction_buffer:
                    if tx.get("id") == transaction_id:
                        target_flow_id = tx.get("flow_id")
                        target_tx = tx
                        break

            if not target_flow_id or target_flow_id not in self.flows:
                return None

            fl = dict(self.flows[target_flow_id])
            tx_ids = set(fl.get("transaction_ids", []))
            frame_ids = set(fl.get("frame_ids", []))

            tx_records = [tx for tx in self.transaction_buffer if tx.get("id") in tx_ids]
            frame_records = [frm for frm in self.frame_buffer if frm.get("id") in frame_ids]

            return {
                "flow_id": target_flow_id,
                "metadata": fl,
                "target_transaction": target_tx,
                "correlated_transactions": tx_records,
                "correlated_frames": frame_records,
                "total_transactions": len(tx_records),
                "total_wire_frames": len(frame_records)
            }

    def _dispatch_to_subscribers(self, record: Dict[str, Any]):
        dead = []
        for q in self.subscribers:
            try:
                q.put_nowait(record)
            except Exception:
                dead.append(q)
        for d in dead:
            if d in self.subscribers:
                self.subscribers.remove(d)

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns decoupled, technically defensible telemetry summaries for L7 Transactions,
        L2/L3 Wire Frames, L4 Flows, and Stehouwer Publishing.
        """
        with self.lock:
            # Latencies: strictly pure ASGI application execution duration
            l_list = list(self.asgi_latencies)
            avg_lat = round(sum(l_list) / len(l_list), 2) if l_list else 0.0
            min_lat = round(min(l_list), 2) if l_list else 0.0
            max_lat = round(max(l_list), 2) if l_list else 0.0

            p95_lat = 0.0
            if l_list:
                sorted_l = sorted(l_list)
                idx = int(len(sorted_l) * 0.95)
                p95_lat = round(sorted_l[min(idx, len(sorted_l) - 1)], 2)

            sorted_routes = sorted(self.route_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            sorted_endpoints = sorted(self.endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Active Flow Lifecycle Evaluation:
            # TCP active until FIN/RST or FLOW_IDLE_TIMEOUT_SECONDS (60s) expires.
            # UDP active until FLOW_IDLE_TIMEOUT_SECONDS (60s) expires.
            now_t = time.time()
            active_flows_dict = {}
            tcp_active = 0
            udp_active = 0
            total_observed = len(self.flows)

            for fid, fl in self.flows.items():
                idle_sec = now_t - fl.get("last_seen", now_t)
                is_closed = fl.get("closed", False)
                proto = str(fl.get("protocol", "TCP")).upper()
                if not is_closed and idle_sec < FLOW_IDLE_TIMEOUT_SECONDS:
                    active_flows_dict[fid] = fl
                    if "TCP" in proto:
                        tcp_active += 1
                    elif "UDP" in proto:
                        udp_active += 1

            active_flows_list = list(active_flows_dict.values())
            captured_overhead = max(0, self.captured_frame_bytes - self.transport_payload_bytes)

            return {
                # Decoupled L7 Application Metrics
                "transactions": {
                    "total_count": self.total_transactions,
                    "http_body_in_bytes": self.http_body_bytes_in,
                    "http_body_out_bytes": self.http_body_bytes_out,
                    "bandwidth_in_kb": round(self.http_body_bytes_in / 1024, 2),
                    "bandwidth_out_kb": round(self.http_body_bytes_out / 1024, 2),
                    "status_codes": self.status_codes,
                    "active_websockets": self.active_websockets,
                    "websocket_messages": self.websocket_messages,
                    "asgi_duration": {
                        "avg_ms": avg_lat,
                        "min_ms": min_lat,
                        "max_ms": max_lat,
                        "p95_ms": p95_lat
                    },
                    "top_routes": [{"path": r[0], "hits": r[1]} for r in sorted_routes]
                },
                # Decoupled L2/L3 Physical Wire Metrics
                "wire_frames": {
                    "total_count": self.total_frames,
                    "captured_frame_bytes": self.captured_frame_bytes,
                    "transport_payload_bytes": self.transport_payload_bytes,
                    "captured_overhead_bytes": captured_overhead,
                    "wire_frame_bytes": self.captured_frame_bytes,
                    "wire_payload_bytes": self.transport_payload_bytes,
                    "wire_bandwidth_kb": round(self.captured_frame_bytes / 1024, 2),
                    "payload_bandwidth_kb": round(self.transport_payload_bytes / 1024, 2),
                    "tcp_flags_distribution": self.tcp_flags_counts,
                    "active_flows_count": len(active_flows_list),
                    "top_endpoints": [{"endpoint": e[0], "frames": e[1]} for e in sorted_endpoints]
                },
                # Decoupled L4 Conversational Flows with Lifecycle States
                "flows": {
                    "active_count": len(active_flows_list),
                    "total_observed": total_observed,
                    "tcp_active": tcp_active,
                    "udp_active": udp_active,
                    "idle_timeout_seconds": FLOW_IDLE_TIMEOUT_SECONDS,
                    "recent_flows": sorted(active_flows_list, key=lambda x: x.get("last_seen", 0), reverse=True)[:10]
                },
                # Auditable Stehouwer Publishing Sub-Ledger
                "stehouwer_publishing": {
                    "trusted_transactions": self.stehouwer_trusted_transactions,
                    "heuristic_transactions": self.stehouwer_heuristic_transactions,
                    "total_packets": self.stehouwer_trusted_transactions + self.stehouwer_heuristic_transactions,
                    "bytes_in": self.stehouwer_body_bytes_in,
                    "bytes_out": self.stehouwer_body_bytes_out,
                    "bandwidth_in_kb": round(self.stehouwer_body_bytes_in / 1024, 2),
                    "bandwidth_out_kb": round(self.stehouwer_body_bytes_out / 1024, 2),
                    "recent_packet_hashes": list(self.stehouwer_recent_digests)[:20]
                },
                # Capture Engine Controls
                "capture_engine": {
                    "mode": self.capture_mode,
                    "npcap_available": is_npcap_available(),
                    "npcap_active": self._sniffer_running,
                    "active_interface": self.active_interface,
                    "bpf_filter": self.active_bpf
                },
                # Backward Compatibility Root Attributes
                "total_requests": self.total_transactions,
                "total_bytes_in": self.http_body_bytes_in,
                "total_bytes_out": self.http_body_bytes_out,
                "bandwidth_in_kb": round(self.http_body_bytes_in / 1024, 2),
                "bandwidth_out_kb": round(self.http_body_bytes_out / 1024, 2),
                "status_codes": self.status_codes,
                "active_websockets": self.active_websockets,
                "latency": {
                    "avg_ms": avg_lat,
                    "min_ms": min_lat,
                    "max_ms": max_lat,
                    "p95_ms": p95_lat
                },
                "top_routes": [{"path": r[0], "hits": r[1]} for r in sorted_routes]
            }

    def get_traffic(
        self,
        record_type: str = "ALL",
        limit: int = 50,
        offset: int = 0,
        domain: Optional[str] = None,
        is_stehouwer: Optional[bool] = None,
        has_hash: Optional[bool] = None,
        method: Optional[str] = None,
        status: Optional[int] = None,
        engine: Optional[str] = None,
        trusted_only: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves filterable list of captured network transactions and/or physical wire frames.
        """
        with self.lock:
            tx_snapshot = list(self.transaction_buffer)
            frm_snapshot = list(self.frame_buffer)

        rec_type = record_type.upper()
        candidates = []
        if rec_type in ["TRANSACTION", "TX", "L7"]:
            candidates = tx_snapshot
        elif rec_type in ["FRAME", "FRM", "L2", "L3"]:
            candidates = frm_snapshot
        else:  # "ALL"
            candidates = tx_snapshot + frm_snapshot
            candidates.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        results = []
        for r in candidates:
            if trusted_only and not r.get("trusted_domain_match"):
                continue
            if domain:
                d_lower = domain.lower()
                orig = r.get("origin_domain", "").lower()
                path_or_ep = r.get("path", "") or r.get("endpoint", "")
                if d_lower not in orig and d_lower not in path_or_ep.lower():
                    continue
            if is_stehouwer is not None and r.get("is_stehouwer_publishing") != is_stehouwer:
                continue
            if has_hash:
                h_in = r.get("payload_sha256_in") or r.get("packet_hash_in")
                h_out = r.get("payload_sha256_out") or r.get("packet_hash_out") or r.get("frame_payload_sha256") or r.get("payload_sha256")
                if not (h_in or h_out):
                    continue
            if method:
                r_m = r.get("method") or r.get("transport") or ""
                if r_m.upper() != method.upper():
                    continue
            if status is not None:
                if r.get("status_code") != status:
                    continue
            if engine:
                if r.get("engine", "").upper() != engine.upper():
                    continue
            results.append(r)

        return results[offset : offset + limit]

    def clear(self):
        """
        Clears both in-memory buffers and resets cumulative metrics.
        """
        with self.lock:
            self.transaction_buffer.clear()
            self.frame_buffer.clear()
            self.total_transactions = 0
            self.http_body_bytes_in = 0
            self.http_body_bytes_out = 0
            self.status_codes = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
            self.route_counts.clear()
            self.asgi_latencies.clear()
            self.total_frames = 0
            self.captured_frame_bytes = 0
            self.transport_payload_bytes = 0
            self.tcp_flags_counts = {"SYN": 0, "ACK": 0, "PSH": 0, "FIN": 0, "RST": 0, "other": 0}
            self.endpoint_counts.clear()
            self.flows.clear()
            self.stehouwer_trusted_transactions = 0
            self.stehouwer_heuristic_transactions = 0
            self.stehouwer_body_bytes_in = 0
            self.stehouwer_body_bytes_out = 0
            self.stehouwer_recent_digests.clear()


# Global Singleton Instance
network_telemetry_engine = NetworkTelemetryEngine()
telemetry_manager = network_telemetry_engine  # Architectural Alias


class NetworkTelemetryMiddleware:
    """
    Pure ASGI Middleware intercepting HTTP and WebSocket lifecycles without buffering
    streaming payloads or requiring raw-socket promiscuous captures.
    """
    def __init__(self, app, engine: Optional[NetworkTelemetryEngine] = None):
        self.app = app
        self.engine = engine or network_telemetry_engine

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        # Skip ASGI accumulation if system is locked exclusively to pure Npcap capture
        if self.engine.capture_mode == "NPCAP":
            return await self.app(scope, receive, send)

        start_time = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()
        now_time = time.time()
        protocol = scope["type"]
        path = scope.get("path", "/")
        method = scope.get("method", "WS" if protocol == "websocket" else "GET")

        # Extract & sanitize headers
        raw_headers = scope.get("headers", [])
        headers: Dict[str, str] = {}
        for k, v in raw_headers:
            header_name = k.decode("latin1").lower()
            if header_name in SENSITIVE_HEADERS:
                headers[header_name] = "[REDACTED]"
            else:
                headers[header_name] = v.decode("latin1", errors="replace")

        # Multi-tenant ID extraction
        client_id = headers.get("x-client-id", "stehouwer_publishing")

        # Domain classification with auditable reasoning
        host_header = headers.get("host", "")
        origin_header = headers.get("origin", "")
        referer_header = headers.get("referer", "")
        fwd_host = headers.get("x-forwarded-host", "")

        origin_domain = host_header or origin_header or fwd_host or "localhost"
        combined_domains = f"{host_header} {origin_header} {referer_header} {fwd_host}".lower()

        trusted_domain_match = any(td in combined_domains for td in TRUSTED_DOMAINS)
        classification_reason = "untrusted_external"

        if trusted_domain_match:
            classification_reason = "host_exact_match"
        elif "stehouwer" in client_id.lower():
            classification_reason = "tenant_header"
        elif path.startswith(("/api/cms", "/api/analytics", "/api/network-telemetry")):
            classification_reason = "internal_api_route"

        is_stehouwer = trusted_domain_match or (classification_reason in ["tenant_header", "internal_api_route"])

        # Endpoints & 5-Tuple Flow Calculation
        client_ip = "127.0.0.1"
        client_port = 0
        if scope.get("client"):
            client_ip = scope["client"][0]
            client_port = scope["client"][1] if len(scope["client"]) > 1 else 0

        server_ip = "127.0.0.1"
        server_port = 8080
        if scope.get("server"):
            server_ip = scope["server"][0]
            server_port = scope["server"][1] if len(scope["server"]) > 1 else 8080

        flow_id = compute_canonical_flow_id("TCP", client_ip, client_port, server_ip, server_port)

        # Payload accumulators & incremental SHA-256 hashers
        bytes_in = 0
        bytes_out = 0
        status_code = 200
        hasher_in = hashlib.sha256()
        hasher_out = hashlib.sha256()

        if protocol == "websocket":
            self.engine.active_websockets += 1
            ws_session_id = f"ws_{int(now_time * 1000)}_{uuid.uuid4().hex[:6]}"

            # Emit WebSocket Connection Event
            self.engine.record_transaction({
                "id": f"tx_{int(now_time * 1000)}_{uuid.uuid4().hex[:12]}",
                "type": "TRANSACTION",
                "engine": "ASGI",
                "protocol": "websocket",
                "method": "WS_CONNECT",
                "path": path,
                "status_code": 101,  # Switching Protocols
                "client_ip": client_ip,
                "client_id": client_id,
                "host_domain": host_header,
                "origin_domain": origin_domain,
                "trusted_domain_match": trusted_domain_match,
                "classification_reason": classification_reason,
                "is_stehouwer_publishing": is_stehouwer,
                "asgi_duration_ms": 0.0,
                "duration_ms": 0.0,
                "body_bytes_in": 0,
                "body_bytes_out": 0,
                "bytes_in": 0,
                "bytes_out": 0,
                "payload_sha256_in": None,
                "payload_sha256_out": None,
                "packet_hash_in": None,
                "packet_hash_out": None,
                "headers": headers,
                "l2_meta": None,
                "transport": "WS",
                "sport": client_port,
                "dport": server_port,
                "flow_id": flow_id,
                "ws_session_id": ws_session_id
            })

            async def wrapped_receive():
                nonlocal bytes_in
                msg = await receive()
                if msg["type"] == "websocket.receive":
                    data = msg.get("bytes") or (msg.get("text", "").encode("utf-8"))
                    if data:
                        d_len = len(data)
                        bytes_in += d_len
                        hasher_in.update(data)
                        self.engine.websocket_messages += 1
                        # Real-time frame message telemetry
                        self.engine.record_transaction({
                            "id": f"tx_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}",
                            "type": "TRANSACTION",
                            "engine": "ASGI",
                            "protocol": "websocket",
                            "method": "WS_RECEIVE",
                            "path": path,
                            "status_code": 200,
                            "client_ip": client_ip,
                            "client_id": client_id,
                            "host_domain": host_header,
                            "origin_domain": origin_domain,
                            "trusted_domain_match": trusted_domain_match,
                            "classification_reason": classification_reason,
                            "is_stehouwer_publishing": is_stehouwer,
                            "asgi_duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
                            "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
                            "body_bytes_in": d_len,
                            "body_bytes_out": 0,
                            "bytes_in": d_len,
                            "bytes_out": 0,
                            "payload_sha256_in": hashlib.sha256(data).hexdigest(),
                            "payload_sha256_out": None,
                            "packet_hash_in": hashlib.sha256(data).hexdigest(),
                            "packet_hash_out": None,
                            "headers": None,
                            "l2_meta": None,
                            "transport": "WS",
                            "sport": client_port,
                            "dport": server_port,
                            "flow_id": flow_id,
                            "ws_session_id": ws_session_id
                        })
                return msg

            async def wrapped_send(msg):
                nonlocal bytes_out, status_code
                if msg["type"] == "websocket.send":
                    data = msg.get("bytes") or (msg.get("text", "").encode("utf-8"))
                    if data:
                        d_len = len(data)
                        bytes_out += d_len
                        hasher_out.update(data)
                        self.engine.websocket_messages += 1
                        # Real-time frame message telemetry
                        self.engine.record_transaction({
                            "id": f"tx_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}",
                            "type": "TRANSACTION",
                            "engine": "ASGI",
                            "protocol": "websocket",
                            "method": "WS_SEND",
                            "path": path,
                            "status_code": 200,
                            "client_ip": client_ip,
                            "client_id": client_id,
                            "host_domain": host_header,
                            "origin_domain": origin_domain,
                            "trusted_domain_match": trusted_domain_match,
                            "classification_reason": classification_reason,
                            "is_stehouwer_publishing": is_stehouwer,
                            "asgi_duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
                            "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
                            "body_bytes_in": 0,
                            "body_bytes_out": d_len,
                            "bytes_in": 0,
                            "bytes_out": d_len,
                            "payload_sha256_in": None,
                            "payload_sha256_out": hashlib.sha256(data).hexdigest(),
                            "packet_hash_in": None,
                            "packet_hash_out": hashlib.sha256(data).hexdigest(),
                            "headers": None,
                            "l2_meta": None,
                            "transport": "WS",
                            "sport": client_port,
                            "dport": server_port,
                            "flow_id": flow_id,
                            "ws_session_id": ws_session_id
                        })
                elif msg["type"] == "websocket.close":
                    status_code = msg.get("code", 1000)
                await send(msg)

            try:
                await self.app(scope, wrapped_receive, wrapped_send)
            finally:
                self.engine.active_websockets = max(0, self.engine.active_websockets - 1)
                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                tx_id = f"tx_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}"

                # Final Session Disconnect Record
                self.engine.record_transaction({
                    "id": tx_id,
                    "type": "TRANSACTION",
                    "engine": "ASGI",
                    "protocol": "websocket",
                    "method": "WS_DISCONNECT",
                    "path": path,
                    "status_code": status_code,
                    "client_ip": client_ip,
                    "client_id": client_id,
                    "host_domain": host_header,
                    "origin_domain": origin_domain,
                    "trusted_domain_match": trusted_domain_match,
                    "classification_reason": classification_reason,
                    "is_stehouwer_publishing": is_stehouwer,
                    "asgi_duration_ms": dur_ms,
                    "duration_ms": dur_ms,
                    "body_bytes_in": bytes_in,
                    "body_bytes_out": bytes_out,
                    "bytes_in": bytes_in,
                    "bytes_out": bytes_out,
                    "payload_sha256_in": hasher_in.hexdigest() if bytes_in > 0 else None,
                    "payload_sha256_out": hasher_out.hexdigest() if bytes_out > 0 else None,
                    "packet_hash_in": hasher_in.hexdigest() if bytes_in > 0 else None,
                    "packet_hash_out": hasher_out.hexdigest() if bytes_out > 0 else None,
                    "headers": headers,
                    "l2_meta": None,
                    "transport": "WS",
                    "sport": client_port,
                    "dport": server_port,
                    "flow_id": flow_id,
                    "ws_session_id": ws_session_id
                })

        else:  # protocol == "http"
            async def wrapped_receive():
                nonlocal bytes_in
                msg = await receive()
                if msg["type"] == "http.request":
                    body = msg.get("body", b"")
                    if body:
                        bytes_in += len(body)
                        hasher_in.update(body)
                return msg

            async def wrapped_send(msg):
                nonlocal bytes_out, status_code
                if msg["type"] == "http.response.start":
                    status_code = msg.get("status", 200)
                elif msg["type"] == "http.response.body":
                    body = msg.get("body", b"")
                    if body:
                        bytes_out += len(body)
                        hasher_out.update(body)
                await send(msg)

            try:
                await self.app(scope, wrapped_receive, wrapped_send)
            finally:
                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                tx_id = f"tx_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}"

                self.engine.record_transaction({
                    "id": tx_id,
                    "type": "TRANSACTION",
                    "engine": "ASGI",
                    "protocol": "http",
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "client_ip": client_ip,
                    "client_id": client_id,
                    "host_domain": host_header,
                    "origin_domain": origin_domain,
                    "trusted_domain_match": trusted_domain_match,
                    "classification_reason": classification_reason,
                    "is_stehouwer_publishing": is_stehouwer,
                    "asgi_duration_ms": dur_ms,
                    "duration_ms": dur_ms,
                    "body_bytes_in": bytes_in,
                    "body_bytes_out": bytes_out,
                    "bytes_in": bytes_in,
                    "bytes_out": bytes_out,
                    "payload_sha256_in": hasher_in.hexdigest() if bytes_in > 0 else None,
                    "payload_sha256_out": hasher_out.hexdigest() if bytes_out > 0 else None,
                    "packet_hash_in": hasher_in.hexdigest() if bytes_in > 0 else None,
                    "packet_hash_out": hasher_out.hexdigest() if bytes_out > 0 else None,
                    "headers": headers,
                    "l2_meta": None,
                    "transport": "HTTP",
                    "sport": client_port,
                    "dport": server_port,
                    "flow_id": flow_id
                })
