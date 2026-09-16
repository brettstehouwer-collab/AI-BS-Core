# Implementation Plan: Network Telemetry Architectural Remediation & Metric Parity (Final Specification)

A rigorous architectural overhaul of the AI-BS telemetry subsystem addressing all 16 audit findings: separating application-layer HTTP/WS transactions from raw physical wire frames and transport flows, establishing a formal flow-correlation layer (`TRANSACTION ⮀ flow_id ⮀ FRAMES`), qualifying capture lengths (`captured_frame_bytes`, `ip_bytes`, `transport_payload_bytes`, `captured_overhead_bytes`), eliminating the phrase "actual wire frame length", renaming frame hashes to `frame_payload_sha256`, enforcing flow lifecycle expiration (60s idle timeout, TCP FIN/RST closure), generating highly collision-resistant 12-hex identifiers, and aligning dashboard presentations with exact measurement semantics.

---

## Refinement Matrix from User Audits

| # | Audit Defect | Specification Requirement | Implemented Architecture |
| :-: | :--- | :--- | :--- |
| **A** | **Capture-Length Semantics** | Do not call `len(bytes(packet))` "wire frame length" without qualification. Eliminate "actual wire frame length". | Semantic hierarchy: `captured_frame_bytes` (capture record), `ip_bytes` (IP packet length), `transport_payload_bytes` (captured transport payload), and `captured_overhead_bytes = captured_frame_bytes - transport_payload_bytes`. |
| **B** | **Payload Hash Distinction** | Rename Npcap SHA-256 to prevent conflation with full HTTP body streams. | Renamed to `frame_payload_sha256` for frames; `payload_sha256_in`/`out` reserved strictly for complete L7 HTTP body streams. |
| **C** | **Canonical Flow Identification** | Define exact canonicalization and nullability for `flow_id`. | `flow_id = canonical(protocol, endpoint_A, endpoint_B)` sorted deterministically (e.g. `TCP|192.168.1.20:54321|192.168.1.50:8080`). Type is `Optional[str]` (returns `None` if unresolvable, loopback, or NAT/proxied). |
| **D** | **Active Flow Lifecycle** | Define when a flow becomes inactive; otherwise count is cumulative. | `FLOW_IDLE_TIMEOUT_SECONDS = 60`. TCP flows close upon `FIN` or `RST` or 60s idle timeout. UDP flows close upon 60s idle timeout. `active_flows = flows_seen - flows_expired - flows_closed`. |
| **E** | **Identifier Terminology & Sizing** | Timestamp + UUID4 is not UUIDv7; avoid claiming "collision-free". | Defined as **"highly collision-resistant timestamp-prefixed UUID4 identifiers"**: `tx_{timestamp_ms}_{uuid4().hex[:12]}` and `frm_{timestamp_ms}_{uuid4().hex[:12]}`. |
| **F** | **Summary API Formal Namespace** | `FLOW` is a formal entity; provide top-level namespace. | Added `"flows": {"active_count": 0, "total_observed": 0, "tcp_active": 0, "udp_active": 0, "idle_timeout_seconds": 60}` to `/api/network-telemetry/summary`. |

---

## Architectural Data Models

### 1. `ASGITransaction` (Layer 7 Application Telemetry)
```python
{
    "id": f"tx_{int(now_time * 1000)}_{uuid.uuid4().hex[:12]}",
    "type": "TRANSACTION",
    "protocol": "http" | "websocket",
    "method": "GET" | "POST" | "WS_CONNECT" | "WS_RECEIVE" | "WS_SEND" | "WS_DISCONNECT",
    "path": "/api/...",
    "status_code": 200,
    "asgi_duration_ms": 14.2,  # Isolated application execution duration, NOT network wire RTT
    "body_bytes_in": 0,
    "body_bytes_out": 3070,
    "payload_sha256_in": "...",  # Complete HTTP request body stream digest
    "payload_sha256_out": "...", # Complete HTTP response body stream digest
    "client_ip": "127.0.0.1",
    "client_id": "stehouwer_publishing",
    "host_domain": "127.0.0.1:8080",
    "origin_domain": "http://localhost:5173",
    "trusted_domain_match": True,
    "classification_reason": "host_exact_match" | "tenant_header" | "internal_api_route",
    "flow_id": "TCP|127.0.0.1:54321|127.0.0.1:8080" # Optional[str]
}
```

### 2. `NpcapFrame` (Layer 2/3 Physical Wire Dissection)
```python
{
    "id": f"frm_{int(now_time * 1000)}_{uuid.uuid4().hex[:12]}",
    "type": "FRAME",
    "engine": "NPCAP_L2_L3",
    "timestamp": "2026-09-10T07:25:00.123456Z",
    "transport": "TCP" | "UDP" | "RAW",
    "endpoint": "192.168.1.50:8080",
    "src_endpoint": "192.168.1.20:54321",
    "tcp_flags": ["PSH", "ACK"],
    "status_code": None,  # Strictly None: raw TCP/UDP frames are not HTTP responses
    "captured_frame_bytes": 1514,    # Bytes represented by the capture record (wirelen or len(bytes))
    "ip_bytes": 1500,                # IP packet length header field
    "transport_payload_bytes": 1460, # Transport Raw payload actually captured
    "captured_overhead_bytes": 54,   # captured_frame_bytes - transport_payload_bytes
    "frame_payload_sha256": "...",   # Digest of the captured payload fragment only
    "l2_meta": {"src_mac": "e8:9c:...", "dst_mac": "00:1a:..."},
    "flow_id": "TCP|192.168.1.20:54321|192.168.1.50:8080" # Optional[str]
}
```

### 3. `ConversationFlow` (Layer 4 5-Tuple Conversational State)
```python
{
    "flow_id": "TCP|192.168.1.20:54321|192.168.1.50:8080",
    "protocol": "TCP",
    "src_endpoint": "192.168.1.20:54321",
    "dst_endpoint": "192.168.1.50:8080",
    "first_seen": 1789025000.0,
    "last_seen": 1789025010.5,
    "closed": False,
    "closure_reason": None | "FIN" | "RST",
    "transaction_ids": ["tx_..."],
    "frame_ids": ["frm_..."],
    "packets_count": 14,
    "captured_frame_bytes": 15420,
    "transport_payload_bytes": 12800,
    "http_body_bytes_in": 0,
    "http_body_bytes_out": 12500
}
```

---

## Verification Plan

### Automated Unit Tests (`backend/test_telemetry_remediation.py`)
1. **Bandwidth Hierarchy & Overhead**:
   ```python
   assert frame["captured_frame_bytes"] == expected_captured_length
   assert frame["ip_bytes"] == expected_ip_length
   assert frame["transport_payload_bytes"] == expected_payload_length
   assert frame["captured_overhead_bytes"] == expected_overhead_length
   assert frame["frame_payload_sha256"] == hashlib.sha256(raw_payload).hexdigest()
   ```
2. **Canonical Flow ID**:
   ```python
   fid_a = compute_canonical_flow_id("TCP", "192.168.1.50", 8080, "192.168.1.20", 54321)
   fid_b = compute_canonical_flow_id("TCP", "192.168.1.20", 54321, "192.168.1.50", 8080)
   assert fid_a == fid_b == "TCP|192.168.1.20:54321|192.168.1.50:8080"
   assert compute_canonical_flow_id("TCP", "0.0.0.0", 0, "127.0.0.1", 8080) is None
   ```
3. **Flow Lifecycle & Timeout Rules**:
   - Verify TCP FIN/RST immediately marks `closed = True`.
   - Verify 60s idle timeout moves flow from `active_count` to expired.
   - Verify `tcp_active` and `udp_active` counts.
4. **Formal Flow Correlation**:
   - Verify `get_flow_correlation(transaction_id)` resolves all correlated frames without abstraction bleed.
5. **Latency Isolation**:
   - Verify ASGI latency deque contains only L7 durations and Npcap 0.0ms does not dilute statistics.
6. **WebSocket L7 Classification**:
   - Verify WebSocket messages are recorded strictly as `TRANSACTION` records.
