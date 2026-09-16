# Implementation Plan: Npcap-Backed L2/L3 Promiscuous Packet Capture & Hybrid Telemetry Engine (v5.240.0)

Integrate a low-level Npcap/Scapy Layer 2 (Ethernet MAC) and Layer 3 (IP/Transport) packet capture engine directly into `backend/modules/network_telemetry.py` operating alongside the pure ASGI middleware via a unified ring-buffer and telemetry manager. Provide dynamic engine mode toggling (`ASGI`, `NPCAP`, `HYBRID`) via FastAPI endpoints and the frontend dashboard.

## User Review Required

> [!IMPORTANT]
> - **Host Driver Requirement:** Npcap (NDIS 6 Filter Driver) must be installed on the Windows host to enable raw wire frame capture. If Npcap or Scapy is absent, the system operates with a graceful, non-blocking fallback to `"ASGI"` mode.
> - **Driver Configuration Flags (When Installing Npcap on Host):**
>   1. *Install Npcap in WinPcap API-compatible Mode:* Required for Python bindings to locate `wpcap.dll` and `Packet.dll`.
>   2. *Support raw 802.11 traffic (and monitor mode):* Optional for Wi-Fi frame capture.
>   3. *Restrict Npcap driver access to Administrators only:* Uncheck if running telemetry services un-elevated.
> - **Zero Disruption to Existing Services:** The existing ASGI middleware and SSE streaming endpoints will remain fully functional regardless of Npcap availability.

## Open Questions

- None. The architecture follows the provided selectable capture specification with non-blocking fallback.

---

## Proposed Changes

### Backend Telemetry Engine Layer

#### [MODIFY] [`backend/modules/network_telemetry.py`](file:///C:/AI-BS/backend/modules/network_telemetry.py)
- Import Scapy modules (`IP`, `TCP`, `UDP`, `Ether`, `Raw`, `conf`, `AsyncSniffer`) wrapped in a non-blocking `try...except` block, setting `NPCAP_AVAILABLE = True` or `False`.
- Refactor the telemetry core into a unified `UnifiedTelemetryManager` (aliased to `network_telemetry_engine` for backward compatibility):
  - Support three capture modes:
    - `"ASGI"`: Pure application-level HTTP/WebSocket lifecycle interception with zero driver dependency.
    - `"NPCAP"`: Low-level promiscuous packet sniffing via Scapy `AsyncSniffer` with kernel-level BPF filtering.
    - `"HYBRID"`: Simultaneous dual-tier telemetry where ASGI captures application route/latency/status metrics while Npcap captures L2 Ethernet MAC and L3/L4 transport frames.
  - Implement `_start_npcap_sniffer()` and `_stop_npcap_sniffer()` with thread-safe controls.
  - Implement `set_mode(mode, interface, bpf_filter)`.
  - Implement `get_network_interfaces()` using `get_windows_if_list()` / Scapy interface discovery.
  - Ingest both ASGI transactions and Npcap L2/L3 frames into a shared ring buffer and dispatch to active SSE subscribers.
  - Retain `stehouwer-publishing.com` classifier, sub-ledger, and credential masking.
- Update `NetworkTelemetryMiddleware` to check `telemetry_manager.capture_mode == "NPCAP"` and bypass duplicate ASGI record creation when locked strictly to pure Npcap mode.

---

### Backend API Router Layer

#### [MODIFY] [`backend/routers/network_telemetry_router.py`](file:///C:/AI-BS/backend/routers/network_telemetry_router.py)
- Expose `POST /api/network-telemetry/capture-mode`:
  - Accepts query parameters `mode` (`ASGI`, `NPCAP`, `HYBRID`), `interface` (optional), and `bpf` (default: `"tcp or udp"`).
  - Switches active capture mode dynamically without restarting the server.
- Expose `GET /api/network-telemetry/interfaces`:
  - Returns list of host network adapters with name, description, MAC, and IP.
- Update `GET /api/network-telemetry/summary` to return `capture_engine` block (`mode`, `npcap_available`, `npcap_active`, `active_interface`, `bpf_filter`).

---

### Frontend Dashboard Layer

#### [MODIFY] [`frontend/src/components/BetaAnalyticsTab.jsx`](file:///C:/AI-BS/frontend/src/components/BetaAnalyticsTab.jsx) (and mirrors)
- In **Category 2: 🔒 Wire Packet Hashes & Gateway Telemetry**:
  - Add Capture Engine selector controls (`ASGI`, `NPCAP`, `HYBRID`) and display active driver status (`Npcap Available / Active / Offline`).
  - Add interface selector dropdown and BPF filter configuration input.
  - Update packet table to display Layer 2 MAC addresses (`src_mac` &rarr; `dst_mac`) when available from Npcap frames.
- Sweep UI version parity badges to `v5.240.0`.

---

### System Ledgers & Maintenance

#### [MODIFY] [`docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md) & [`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Document the Npcap L2/L3 promiscuous capture architecture, NDIS 6 filter driver requirements, BPF kernel offload, and hybrid dual-tier telemetry.
- Bump manual version to `5.240.0`, persist artifact to `saved_data/artifacts/20260910_AI_BS_Master_Ecosystem_Manual.md`, log in `NotebookLM_Records/artifact_history.md`, and update chronologies.

---

## Verification Plan

### Automated Tests
1. Install `scapy` via `uv pip install scapy` (or project python tooling) and verify import.
2. Run standalone test script `backend/test_network_telemetry_npcap.py`:
   - Verify `NPCAP_AVAILABLE` detection and graceful fallback when driver is not bound.
   - Verify mode switching (`set_mode("ASGI")`, `set_mode("HYBRID")`, `set_mode("NPCAP")`).
   - Verify ASGI packet tracking continues seamlessly with SHA-256 payload hashing.
   - Verify interface enumeration returns host adapters.
   - Verify router endpoints (`/api/network-telemetry/capture-mode`, `/interfaces`, `/summary`) return HTTP 200.

### Manual & Build Verification
1. Build frontend via `npm run build` from `C:\AI-BS\frontend`.
2. Deploy to Firebase Hosting via `firebase deploy --only hosting --non-interactive`.
3. Mirror `dist` to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
4. Inspect `Launch_AI_BS.bat` to verify system boot launcher integrity.
