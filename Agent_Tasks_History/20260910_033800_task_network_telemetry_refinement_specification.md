# Task: Network Telemetry Architectural Remediation (Transaction vs Frame Separation, Bandwidth Accounting & Dashboard Parity)

- [x] Phase 1: Planning & Operator Review <!-- id: 400 -->
  - [x] Generate comprehensive implementation plan artifact addressing all 16 audit findings <!-- id: 401 -->
  - [x] Halt and await explicit operator approval before mutating any codebase files <!-- id: 402 -->
- [x] Phase 2: Core Data Modeling & Engine Separation (`backend/modules/network_telemetry.py`) <!-- id: 403 -->
  - [x] Formalize distinct `Transaction` (L7 HTTP/WS) and `Frame` (L2/3 Npcap) data structures <!-- id: 404 -->
  - [x] Fix Npcap status code bug (remove `status_code = 200 if TCP`; set `status_code = None` and record `tcp_flags`) <!-- id: 405 -->
  - [x] Fix Npcap bandwidth accounting (`frame_bytes = len(bytes(packet))` vs `payload_bytes = len(Raw.load)`) <!-- id: 406 -->
  - [x] Disambiguate `method` and `path` for Npcap frames (rename to `endpoint` and `transport`) <!-- id: 407 -->
  - [x] Isolate ASGI application execution duration from network latency (rename to `asgi_duration_ms`) <!-- id: 408 -->
  - [x] Eliminate HYBRID mode double-counting by tracking separate counters for transactions, frames, and flows <!-- id: 409 -->
  - [x] Implement active frame-level and lifecycle WebSocket telemetry <!-- id: 410 -->
  - [x] Upgrade Stehouwer domain classification with auditable `classification_reason` and `trusted_domain_match` <!-- id: 411 -->
  - [x] Implement collision-free UUIDv7-style transaction and frame IDs <!-- id: 412 -->
- [x] Phase 3: REST API & Telemetry Router Upgrades (`backend/routers/network_telemetry_router.py`) <!-- id: 413 -->
  - [x] Upgrade `GET /api/network-telemetry/summary` with decoupled transaction, wire frame, and flow statistics <!-- id: 414 -->
  - [x] Upgrade `GET /api/network-telemetry/traffic` with `record_type` filter (`ALL`, `TRANSACTION`, `FRAME`) <!-- id: 415 -->
  - [x] Stream real-time typed events over SSE `/stream` <!-- id: 416 -->
- [x] Phase 4: Frontend UI Analytics Dashboard Refactor (`BetaAnalyticsTab.jsx`) <!-- id: 417 -->
  - [x] Update Category 1 (Stehouwer Web Traffic): "ASGI Transactions", "Observed HTTP Body Bytes In/Out", "Avg ASGI App Duration" <!-- id: 418 -->
  - [x] Update Category 2 (Wire Packets & L2/3 Dissection): "Captured Wire Frames", "Wire Bytes (Frames vs Payload)", "Active Flows", "TCP Flags" <!-- id: 419 -->
  - [x] Update Wire Stream Table: distinct badges for L7 Transactions vs L2/3 Frames, Endpoint vs Path, and Payload SHA-256 digests <!-- id: 420 -->
  - [x] Sync across mirror paths (`frontend/src/components/`, `frontend/components/`, `frontend/src/components/components/`) <!-- id: 421 -->
- [x] Phase 5: Verification, Production Build & Deployment <!-- id: 422 -->
  - [x] Author unit test suite `backend/test_telemetry_remediation.py` validating data model separation and metrics <!-- id: 423 -->
  - [x] Sweep UI version parity to `v5.242.0` <!-- id: 424 -->
  - [x] Compile production bundle (`npm run build`) and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 425 -->
  - [x] Mirror dist to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist` <!-- id: 426 -->
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, and master chronologies <!-- id: 427 -->
- [x] Phase 6: Telemetry Audit Refinements & Second Review Implementation <!-- id: 428 -->
  - [x] Eliminate "actual wire frame length" terminology in favor of explicit 4-tier semantic hierarchy (`captured_frame_bytes`, `ip_bytes`, `transport_payload_bytes`, `captured_overhead_bytes`) <!-- id: 429 -->
  - [x] Formalize canonical `flow_id` (`{protocol}|{min_endpoint}|{max_endpoint}`) with `Optional[str]` nullability <!-- id: 430 -->
  - [x] Implement deterministic flow lifecycle with `FLOW_IDLE_TIMEOUT_SECONDS = 60` and TCP FIN/RST teardown <!-- id: 431 -->
  - [x] Standardize highly collision-resistant timestamp-prefixed UUID4 identifiers (`tx_{ms}_{12_hex}`, `frm_{ms}_{12_hex}`) <!-- id: 432 -->
  - [x] Expose dedicated `"flows"` namespace in `GET /api/network-telemetry/summary` with active, observed, and protocol counts <!-- id: 433 -->
  - [x] Author comprehensive 6-test verification suite and verify 100% pass rate <!-- id: 434 -->


