# Implementation Plan: Network Telemetry Architectural Remediation & Metric Parity (Refined)

A systematic architectural overhaul of the AI-BS telemetry subsystem addressing all audit findings: separating application-layer HTTP/WS transactions from raw physical wire frames and transport flows, adding a formal flow-correlation layer (`TRANSACTION ⮀ flow_id ⮀ FRAMES`), qualifying capture lengths (`captured_frame_bytes`, `ip_bytes`, `transport_payload_bytes`), renaming frame hashes to `frame_payload_sha256`, eliminating false HTTP status codes in Npcap, preventing HYBRID mode double-counting, instrumenting WebSocket telemetry, and aligning dashboard presentations with exact measurement semantics.

---

## Refinement Matrix from User Audit

| # | Audit Finding | User Directive | Refined Implementation |
| :-: | :--- | :--- | :--- |
| **A** | **Capture Length Qualification** | Do not call `len(bytes(packet))` "wire frame length" without qualification. | Store `captured_frame_bytes = getattr(packet, 'wirelen', len(bytes(packet)))`, `ip_bytes` (from IP header len), and `transport_payload_bytes` (from `Raw.load`). |
| **B** | **Hash Distinction** | Rename Npcap SHA-256 to prevent conflation with full HTTP body streams. | Rename to `frame_payload_sha256` for frames, keeping `payload_sha256_in`/`out` strictly for complete HTTP body streams. |
| **C** | **Formal Flow Correlation** | Link transactions to wire frames via `flow_id`. | Both `TRANSACTION` and `FRAME` compute bidirectional 5-tuple `flow_id` (`min(src, dst)<->max(src, dst)_TCP`), allowing correlation of all wire frames belonging to an HTTP transaction. |

---

## Audit Findings & Remediation Matrix

| # | Audited Defect | Severity | Root Cause in Current Code | Architectural Remediation |
| :-: | :--- | :---: | :--- | :--- |
| **1** | **Monolithic Packet Model** | **High** | L7 HTTP transactions and L2/L3 wire packets are stored in the same dictionary format and appended to the same ring buffer. | Separate into distinct entities: `TRANSACTION` (L7 HTTP/WS), `FRAME` (L2/L3 Npcap), and `FLOW` (L4 5-tuple). |
| **2** | **Npcap HTTP Status 200 Bug** | **High** | Line 168: `"status_code": 200 if packet.haslayer(TCP) else None`. Raw TCP SYN/ACK/FIN are misreported as successful HTTP requests. | Set `status_code = None` on all Npcap frames. Capture and expose `tcp_flags` (`SYN`, `ACK`, `PSH`, `FIN`, `RST`) instead. |
| **3** | **Npcap Bandwidth Under-Counting** | **High** | Line 148-150: Only measures `len(packet[Raw].load)`, ignoring Ethernet, IP, and TCP headers. | Measure `frame_bytes = len(bytes(packet))` (wire bandwidth) and `payload_bytes = len(packet[Raw].load)` as separate metrics. |
| **4** | **Npcap Mislabeled Method & Path** | **High** | Line 166-167: `"method": proto` (produces `method = "TCP"`) and `"path": f"{dst_ip}:{dport}"`. | Rename fields to `transport = "TCP"`, `endpoint = f"{dst_ip}:{dport}"`. Reserve `method` and `path` strictly for L7 HTTP/WS. |
| **5** | **Latency Semantics Discrepancy** | **High** | `duration_ms` measures Python ASGI application execution duration (`time.perf_counter()`), not wire round-trip network latency. | Re-label metrics to `asgi_duration_ms` / `Avg ASGI Duration` / `P95 ASGI Duration`. Add clear UI explanation distinguishing app execution from network wire transit. |
| **6** | **Npcap Zero Latency Distortion** | **High** | Npcap emits `duration_ms = 0.0`. Combining ASGI and Npcap into the same latency deque dilutes average/P95 stats. | Maintain dedicated `asgi_latencies` deque populated strictly by completed L7 transactions. Exclude Npcap frames from latency averaging. |
| **7** | **HYBRID Double-Counting** | **High** | In HYBRID mode, both ASGI middleware and Npcap sniffer call `record_transaction`, artificially inflating "Total Packets". | Maintain separate counters: `total_transactions`, `total_frames`, and `active_flows`. Never sum them into a monolithic "Total Packets". |
| **8** | **Payload SHA-256 vs Packet Digest** | **Medium** | `packet_hash_in/out` hashes HTTP request/response bodies in ASGI, but only hashes single TCP `Raw` payload fragments in Npcap. | Rename fields to `payload_sha256_in` / `payload_sha256_out` (L7 body digest) and `payload_sha256` (L2/3 frame payload digest). |
| **9** | **WebSocket Telemetry Gaps** | **High** | WebSocket accounting only emits a transaction upon socket disconnection (`finally` block); zero real-time visibility during active sessions. | Instrument frame-level WebSocket telemetry on every `websocket.receive` and `websocket.send` message, plus session connection/disconnection lifecycle events. |
| **10** | **Stehouwer Classification Over-Broad** | **Medium** | Classifies any request as `is_stehouwer_publishing` if URL begins with `/api/cms` or `/api/analytics` even if `Host` is external. | Replace boolean with auditable fields: `trusted_domain_match` (strict host/origin match), `client_id`, and `classification_reason` (`"host_exact_match"`, `"origin_match"`, `"internal_route"`). |
| **11** | **ID Generation Collision Risk** | **Medium** | Uses millisecond timestamp + 5-character MAC slice or 6-character MD5. | Use collision-free monotonic UUIDv7-style IDs: `tx_{timestamp_ms}_{uuid_hex[:8]}` and `frm_{timestamp_ms}_{uuid_hex[:8]}`. |
| **12** | **Dashboard Metric Labels** | **High** | "Total Packets: 1,145" and "Avg Latency: 394 ms" are technically inaccurate for HTTP transactions. | Refactor dashboard cards and tables to display technically defensible titles: `ASGI Transactions`, `Observed HTTP Body Bytes`, `Captured Wire Frames`, and `Avg ASGI Duration`. |

---

## User Review Required

> [!IMPORTANT]
> **Key Architectural Design Decisions:**
> 1. **Data Model Decoupling:** We will maintain two dedicated ring buffers in `NetworkTelemetryEngine`:
>    - `transaction_buffer` (max 1,000 L7 HTTP & WebSocket records).
>    - `frame_buffer` (max 2,000 L2/L3 physical wire frame records).
>    - This completely eliminates data collision, metric dilution, and field mislabeling between layers.
> 2. **Unified Query Option:** The REST API `GET /api/network-telemetry/traffic` will support `type=TRANSACTION`, `type=FRAME`, or `type=ALL` (chronologically interleaved by timestamp) so that both the dedicated L7 panel and L2/3 wire sniffer table receive exact data without compromises.
> 3. **Dashboard Clarity:** Category 1 will be titled **Category 1: 🌐 Stehouwer Web Traffic (L7 Application Telemetry)**, and Category 2 will be titled **Category 2: 📡 Wire Packets & L2/L3 Dissection (Kernel Npcap Driver)**.

---

## Proposed Changes

### Component 1: Core Telemetry Engine (`backend/modules/network_telemetry.py`)

#### [MODIFY] [`backend/modules/network_telemetry.py`](file:///C:/AI-BS/backend/modules/network_telemetry.py)

1. **Formalize Data Structures:**
   - **`ASGITransaction`**:
     ```python
     {
         "id": f"tx_{int(now_time * 1000)}_{uuid.uuid4().hex[:8]}",
         "type": "TRANSACTION",
         "protocol": "http" | "websocket",
         "method": "GET" | "POST" | ...,
         "path": "/api/...",
         "status_code": 200,
         "asgi_duration_ms": 14.2,
         "body_bytes_in": 0,
         "body_bytes_out": 3070,
         "payload_sha256_in": "...",
         "payload_sha256_out": "...",
         "client_ip": "127.0.0.1",
         "client_id": "stehouwer_publishing",
         "host_domain": "127.0.0.1:8080",
         "origin_domain": "http://localhost:5173",
         "trusted_domain_match": True,
         "classification_reason": "host_exact_match"
     }
     ```
   - **`NpcapFrame`**:
     ```python
     {
         "id": f"frm_{int(now_time * 1000)}_{uuid.uuid4().hex[:8]}",
         "type": "FRAME",
         "engine": "NPCAP_L2_L3",
         "timestamp": "2026-09-10T07:25:00.123456Z",
         "transport": "TCP" | "UDP" | "RAW",
         "endpoint": "192.168.1.50:8080",
         "src_endpoint": "192.168.1.20:54321",
         "tcp_flags": ["PSH", "ACK"],
         "status_code": None,  # NEVER 200
         "frame_bytes": 1514,  # Actual wire frame length
         "payload_bytes": 1460, # Raw transport payload
         "header_bytes": 54,    # L2+L3+L4 overhead
         "payload_sha256": "...",
         "l2_meta": {"src_mac": "e8:9c:...", "dst_mac": "00:1a:..."},
         "flow_key": "192.168.1.20:54321<->192.168.1.50:8080_TCP"
     }
     ```

2. **Decouple In-Memory Ring Buffers & Counters:**
   - `self.transaction_buffer = deque(maxlen=1500)`
   - `self.frame_buffer = deque(maxlen=3000)`
   - `self.asgi_latencies = deque(maxlen=500)` (tracks `asgi_duration_ms` only; zero 0.0ms pollution from Npcap)
   - Independent counters for `total_transactions`, `total_frames`, `http_body_in_bytes`, `http_body_out_bytes`, `wire_frame_bytes`, `wire_payload_bytes`.

3. **Active WebSocket Telemetry:**
   - Instrument `wrapped_receive` and `wrapped_send` to emit live `WS_MESSAGE` transactions for every message transferred over open WebSockets, and log `WS_CONNECT` / `WS_DISCONNECT` with cumulative lifetime session metrics.

4. **TCP Flags Dissection:**
   - Extract TCP flags from Scapy packet (`packet[TCP].flags`) into readable tags (`SYN`, `ACK`, `PSH`, `FIN`, `RST`, `URG`).

---

### Component 2: REST API Router (`backend/routers/network_telemetry_router.py`)

#### [MODIFY] [`backend/routers/network_telemetry_router.py`](file:///C:/AI-BS/backend/routers/network_telemetry_router.py)

1. **`GET /api/network-telemetry/summary`:**
   - Returns decoupled metric structures:
     - `transactions`: `total_count`, `http_body_in_bytes`, `http_body_out_bytes`, `avg_asgi_duration_ms`, `p95_asgi_duration_ms`, `status_codes`, `top_routes`.
     - `wire_frames`: `total_count`, `wire_frame_bytes`, `wire_payload_bytes`, `tcp_flags_distribution`, `active_flows_count`.
     - `stehouwer_publishing`: `trusted_transactions`, `heuristic_transactions`, `trusted_body_bytes`, `recent_payload_digests`.
     - `capture_engine`: `mode`, `npcap_available`, `npcap_active`, `active_interface`, `bpf_filter`.

2. **`GET /api/network-telemetry/traffic`:**
   - Add query parameter `type`: `ALL` (interleaved), `TRANSACTION`, or `FRAME`.
   - Add query parameter `trusted_only`: filter by strict domain verification.

---

### Component 3: Frontend Dashboard Refactoring (`BetaAnalyticsTab.jsx`)

#### [MODIFY] [`frontend/src/components/BetaAnalyticsTab.jsx`](file:///C:/AI-BS/frontend/src/components/BetaAnalyticsTab.jsx) *(and mirror paths)*

1. **Category 1: 🌐 Stehouwer Web Traffic (L7 Application Telemetry)**
   - Card 1: `ASGI Transactions: {summary?.transactions?.total_count || 0}`
   - Card 2: `Observed Request Body In: {formatBytes(summary?.transactions?.http_body_in_bytes)}`
   - Card 3: `Observed Response Body Out: {formatBytes(summary?.transactions?.http_body_out_bytes)}`
   - Card 4: `Avg ASGI App Duration: {summary?.transactions?.avg_asgi_duration_ms} ms` (P95: `{summary?.transactions?.p95_asgi_duration_ms} ms`) with informative badge: *"App Execution Latency"*
   - Table: Displays HTTP Method, Path, Status Code, Body In/Out, and **Request/Response Payload SHA-256**.

2. **Category 2: 📡 Wire Packets & L2/L3 Dissection (Kernel Npcap Driver)**
   - Card 1: `Captured Wire Frames: {summary?.wire_frames?.total_count || 0}`
   - Card 2: `Total Wire Bandwidth: {formatBytes(summary?.wire_frames?.wire_frame_bytes)}` (with payload breakdown)
   - Card 3: `Active TCP/UDP Flows: {summary?.wire_frames?.active_flows_count || 0}`
   - Card 4: `TCP Flags: SYN ({...}) | ACK ({...}) | PSH ({...})`
   - Table: Displays Transport Protocol, TCP Flags badge (e.g. `[PSH, ACK]`), Destination Endpoint (`IP:Port`), L2 MACs (`src_mac` &rarr; `dst_mac`), Wire Frame Bytes, and **Raw Payload SHA-256**.

3. **Synchronize Across Mirror Paths:**
   - `frontend/src/components/BetaAnalyticsTab.jsx`
   - `frontend/components/BetaAnalyticsTab.jsx`
   - `frontend/src/components/components/BetaAnalyticsTab.jsx`

---

### Component 4: Verification, Version Sweeps & Live Deployment

1. **Automated Unit Test Suite:**
   - Author [`backend/test_telemetry_remediation.py`](file:///C:/AI-BS/backend/test_telemetry_remediation.py) verifying:
     - Distinct `TRANSACTION` vs `FRAME` data models.
     - Npcap frame status code is strictly `None` with valid TCP flags extracted.
     - Npcap bandwidth counts `len(bytes(packet))` vs `len(Raw.load)`.
     - `asgi_duration_ms` tracked independently from Npcap frames.
     - HYBRID mode keeps separate transaction and frame counters.
     - WebSocket message-level telemetry works.
2. **UI Version Parity:**
   - Sweep version to `v5.242.0` across 17 frontend files and manifests.
3. **Build & Live Deployment:**
   - Run `npm run build` in `frontend/`.
   - Deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`).
   - Mirror dist to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
4. **Ledgers:**
   - Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (v5.242.0), and master chronologies.

---

## Verification Plan

### Automated Tests
- `python backend/test_telemetry_remediation.py`: 100% pass across all 8 assertions.
- `python backend/test_network_telemetry_npcap.py`: Existing tests updated to verify new decoupled schemas.
- `python backend/test_network_telemetry.py`: Verify regression-free ASGI middleware execution.

### Manual Verification
- Launch browser at `https://ai-bs-dashboard.web.app`.
- Verify Category 1 displays "ASGI Transactions" and "Avg ASGI App Duration".
- Verify Category 2 displays "Captured Wire Frames", TCP flags, and destination endpoints.
- Confirm zero instances of TCP packets showing HTTP 200.
