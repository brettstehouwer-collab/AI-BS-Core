# Implementation Plan: Unified Web Analytics, Wire Packet Hashes & Over-The-Air Wave Sensor Suite

Unify all telemetry, packet capture, and wave sensor data streams into the **Web Traffic Tab** (`BetaAnalyticsTab.jsx`) under the **Stehouwer Publishing** module in AI-BS. This organizes all data captures into one centralized, categorized operational dashboard:
1. **Category 1: 🌐 Stehouwer Web Traffic & User Telemetry:** Real-time dwell times, scroll depths, Geo-IP distribution, client hardware specs, Web Vitals, form drop-offs & GPU telemetry.
2. **Category 2: 🔒 Wire Packet Hashes & Gateway Telemetry:** Pure ASGI middleware capturing HTTP/WebSocket request-response lifecycles, byte accumulators, execution latency, credential scrubbing, and streaming SHA-256 payload digests (`packet_hash_in`, `packet_hash_out`), filtered for `stehouwer-publishing.com`.
3. **Category 3: 📡 Over-The-Air Wave Hardware Sensors:** Ambient electromagnetic radio waves (2.4 GHz, 5 GHz, 6 GHz Wi-Fi beacons and Bluetooth BLE advertisements) detected via host PC hardware sensors, generating and persisting cryptographic SHA-256 beacon hashes to SQLite for review, environment fingerprinting, and learning.
4. **Category 4: ⚡ Commercial API & Security Telemetry:** Live commercial API calls, IP security events, and ban ledgers.

---

## User Review Required

> [!IMPORTANT]
> **Unified Single-Pane Architecture in Stehouwer Publishing Module:** All capture layers will be blended directly into `BetaAnalyticsTab.jsx` (accessible under the Web Analytics & Stehouwer Publishing suite in AI-BS), segmented into 4 clean category sub-tabs with real-time sync, tabular inspection, and filtering.

> [!IMPORTANT]
> **Hardware Sensor Reality & RF Wave Detection:** Host PC sensors natively detect electromagnetic radio waves across 802.11 Wi-Fi (2.4 GHz, 5 GHz, 6 GHz) and Bluetooth (2.4 GHz ISM). Telemetry records capture SSID, BSSID (MAC), RSSI signal quality, channel frequencies, and physical wave metadata (`frequency_band`, `medium: RF_ELECTROMAGNETIC`, `sensor_hardware`). Each over-the-air beacon is cryptographically hashed with SHA-256 and persisted in SQLite (`saved_data/air_sensor_telemetry.db`).

> [!NOTE]
> **Production Deployment:** All frontend modifications in `frontend/` will be built and deployed directly to `ai-bs-dashboard.web.app` via `firebase deploy --only hosting --non-interactive`.

---

## Technical Specifications

### 1. Frontend UI Architecture (`BetaAnalyticsTab.jsx`)
Upgrade `BetaAnalyticsTab.jsx` with a categorized sub-navigation bar:
- **`[ 🌐 Stehouwer Web Traffic ]`**:
  - Dwell time distributions, scroll depth gauges, Geo-IP origin map/table, client GPU specs, Core Web Vitals (LCP, CLS, TTFB), and lead drop-off recovery.
- **`[ 🔒 Wire Packet Hashes & Gateway ]`**:
  - Inbound & outbound throughput meters (KB/MB).
  - Status code distribution (`2xx`, `3xx`, `4xx`, `5xx`).
  - Active transaction table with live SHA-256 payload digests (`packet_hash_in`, `packet_hash_out`), execution latencies, and sanitized headers.
  - Filter toggle: `Stehouwer-Publishing.com Traffic Only` vs `All Gateway Traffic`.
- **`[ 📡 Over-The-Air Wave Sensors ]`**:
  - "Scan Air Waves" on-demand trigger button.
  - Spectrum band distribution badges (`2.4GHz ISM`, `5GHz UNII`, `6GHz Wi-Fi 6E`, `Bluetooth BLE`).
  - Active over-the-air beacon ledger: BSSID, SSID, Channel, Signal Quality %, Wave Medium, and 64-char SHA-256 beacon fingerprint.
  - Historical query panel backed by SQLite persistence.
- **`[ ⚡ API & Security Telemetry ]`**:
  - API call streams, ban management, and security audit events.

### 2. Backend ASGI Network Telemetry Middleware (`NetworkTelemetryMiddleware`)
- Intercepts ASGI `http` and `websocket` scopes in `backend/modules/network_telemetry.py`.
- Calculates high-precision execution latency via `time.perf_counter()`.
- Computes SHA-256 hex digests on streaming body chunks incrementally without buffering full payloads into memory.
- Strictly redacts authentication headers (`Authorization`, `Cookie`, `X-Api-Key`, etc.).
- Tags origin domain and flags `is_stehouwer_publishing`.

### 3. Over-The-Air Wave Sensor Engine (`AirWaveSensorEngine`)
- In `backend/modules/ambient_sensor_telemetry.py`:
  - Wi-Fi RF Scanner: Runs unprivileged native Windows WLAN queries (`netsh wlan show networks mode=bssid`) to extract active 802.11 beacon frames in the surrounding air.
  - Bluetooth Scanner: Queries local Bluetooth/BLE peripheral advertisements.
  - Hasher: Generates deterministic SHA-256 hashes:
    $$\text{beacon\_hash} = \text{SHA-256}(\text{BSSID} \parallel \text{SSID} \parallel \text{Channel} \parallel \text{RadioType} \parallel \text{Encryption})$$
  - Persistence: Writes every detected beacon to SQLite database `saved_data/air_sensor_telemetry.db` table `air_beacon_records`.

### 4. API Router Endpoints (`/api/network-telemetry`)
| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/network-telemetry/summary` | `GET` | None | Aggregated gateway metrics (throughput, status codes, latencies) and `stehouwer_publishing` stats. |
| `/api/network-telemetry/traffic` | `GET` | `limit`, `offset`, `domain`, `is_stehouwer`, `has_hash` | Filterable list of captured HTTP/WS transactions with SHA-256 packet digests. |
| `/api/network-telemetry/air/scan` | `GET` | None | Triggers live on-demand over-the-air RF wave sweep across PC sensors. |
| `/api/network-telemetry/air/records` | `GET` | `sensor_type`, `band`, `limit`, `offset` | Queries historically persisted over-the-air packet and beacon hashes from SQLite. |
| `/api/network-telemetry/air/summary` | `GET` | None | Summary metrics of ambient wave landscape (unique beacon hashes, band distribution, signal averages). |
| `/api/network-telemetry/stream` | `GET` | `domain`, `include_air` | Server-Sent Events (SSE) live broadcast of gateway packets and air wave events. |
| `/api/network-telemetry/clear` | `POST` | None | Flushes the in-memory gateway ring buffer. |

---

## Proposed Changes

### Backend Infrastructure
#### [NEW] [ambient_sensor_telemetry.py](file:///C:/AI-BS/backend/modules/ambient_sensor_telemetry.py)
- Defines `AirWaveSensorEngine` with Wi-Fi RF beacon scanning, Bluetooth device discovery, SHA-256 beacon hashing, and SQLite persistence.

#### [NEW] [network_telemetry.py](file:///C:/AI-BS/backend/modules/network_telemetry.py)
- Defines pure ASGI `NetworkTelemetryMiddleware` and in-memory ring buffer `NetworkTelemetryEngine`.
- Computes SHA-256 payload digests on incoming/outgoing wire chunks.
- Sanitizes credentials and indexes `stehouwer-publishing.com` transactions.

#### [NEW] [network_telemetry_router.py](file:///C:/AI-BS/backend/routers/network_telemetry_router.py)
- Mounts `/api/network-telemetry` endpoints with multi-tenancy dependency `Depends(get_tenant)`.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Registers `NetworkTelemetryMiddleware`.
- Includes `network_telemetry_router`.

### Frontend UI
#### [MODIFY] [BetaAnalyticsTab.jsx](file:///C:/AI-BS/frontend/src/components/BetaAnalyticsTab.jsx)
- Integrate 4 categorized sub-tabs: Web Traffic, Wire Packet Hashes, Over-The-Air Wave Sensors, and API Security.
- Add live tables, filters, and charts for packet hashes and air beacon telemetry.

#### [MODIFY] [StehouwerCMSTab.jsx](file:///C:/AI-BS/frontend/src/components/components/StehouwerCMSTab.jsx)
- Update Stehouwer Publishing telemetry summary cards to display live wire packet counts and over-the-air wave beacon counts.

---

## Verification Plan

### Automated Tests
- Create [test_network_telemetry.py](file:///C:/AI-BS/backend/test_network_telemetry.py):
  1. **Gateway Inbound/Outbound Hashing:** Send request with known payload, verify byte count and SHA-256 digest match `hashlib.sha256(payload).hexdigest()`.
  2. **`stehouwer-publishing.com` Classification:** Send request with `Host: stehouwer-publishing.com`, verify `is_stehouwer_publishing == True` and packet appears in `stehouwer_publishing` sub-ledger.
  3. **Credential Scrubbing:** Send request with `Authorization: Bearer test_key` and `Cookie: token=xyz`, verify `[REDACTED]`.
  4. **Over-The-Air Sensor Scanning & Hashing:** Execute `AirWaveSensorEngine.scan_air()`; verify discovered Wi-Fi/RF records produce deterministic 64-character SHA-256 hex hashes.
  5. **Air Telemetry Database Persistence:** Verify beacon records and hashes are written to `saved_data/air_sensor_telemetry.db` and queryable via `/api/network-telemetry/air/records`.
- Run automated test suite:
  ```powershell
  python C:\AI-BS\backend\test_network_telemetry.py
  ```

### Frontend Build & Deployment
- Build and deploy to Firebase Hosting:
  ```powershell
  powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"
  ```
- Verify live deployment at `https://ai-bs-dashboard.web.app`.

### Manual Verification
- Open Web Traffic Tab in AI-BS, toggle between all 4 categories, and trigger an Over-The-Air Wave sweep to confirm live telemetry rendering.
