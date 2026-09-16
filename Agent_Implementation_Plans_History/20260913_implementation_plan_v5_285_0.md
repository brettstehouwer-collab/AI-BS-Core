# Implementation Plan: Sovereign Multi-Tenant Hosting & AI Vector Analytics for The Simple Chef

Deploy a sovereign, multi-tenant hosting configuration for Chef John Barr's website (*The Simple Chef*) on your host infrastructure, featuring an isolated Nginx virtual host with DDoS/rate-limiting, automated daily log rotation, a dedicated ChromaDB vector partition (`thesimplechef_analytics_bin`), GDPR/CCPA-compliant IP anonymization, and an interactive AI analytics dashboard in the AI-BS Client Hub.

---

## User Review Required

> [!IMPORTANT]
> **Zero Disruption to Stehouwer Publishing & Active Workloads:**
> The new Nginx configuration and ChromaDB collection are strictly isolated in a partitioned client sandbox. Your existing Stehouwer Publishing sites (`*.brettstehouwer.live`), RTX 4090 Pearl miner (~275 TH/s), and crypto swarm bots remain completely untouched and protected by rate-limiting and memory caps.

> [!NOTE]
> **Hybrid Edge + Local Core Architecture:**
> The frontend storefront remains globally cached and live on Firebase Hosting (`https://thesimplechef.web.app`) for 100% uptime with zero bandwidth cost, while your local machine serves as the sovereign AI backend, order engine, and vector analytics brain via Nginx and Cloudflare Tunnel.

---

## Proposed Changes

```mermaid
graph TD
    A[Visitor Traffic on thesimplechef.com / Web App] -->|Edge Delivery| B[Firebase CDN & Nginx Gateway Port 80]
    B -->|Strict User Isolation: client_web_user| C[/var/log/nginx/thesimplechef_access.log]
    C -->|Automated Daily Rotation| D[/etc/logrotate.d/thesimplechef]
    C -->|Real-Time Tail / Ingestion Loop| E[thesimplechef_analytics_daemon.py]
    E -->|1. IP Hash Anonymizer: 192.168.1.xxx| F[Privacy Compliance Filter]
    F -->|2. Semantic Intent Embedding| G[ChromaDB Port 8002: thesimplechef_analytics_bin]
    G -->|Volumetric Pruning: MAX 50,000 vectors| H[HNSW RAM Guard]
    G -->|Analytical Synthesis API| I[FastAPI: /api/v1/chef/analytics]
    I -->|Interactive Visualization| J[AI-BS Client Hub: JohnBarr.jsx]
```

---

### Phase 1: Linux / WSL2 Isolated Nginx Virtual Host & Logrotate Setup

#### [NEW] [/etc/nginx/sites-available/thesimplechef](file:///etc/nginx/sites-available/thesimplechef)
* Deploy dedicated Nginx server block targeting `thesimplechef.com`, `www.thesimplechef.com`, and local port gateway.
* Strict logging isolation:
  * Access log: `/var/log/nginx/thesimplechef_access.log`
  * Error log: `/var/log/nginx/thesimplechef_error.log`
* Rate limiting & DDoS protection:
  * `limit_req_zone $binary_remote_addr zone=chef_limit:10m rate=15r/s;`
  * `limit_conn_zone $binary_remote_addr zone=chef_conn:10m;`
* Chrooted/isolated webroot:
  * Root directed to `/var/www/thesimplechef/public` with restricted non-login user (`client_web_user:www-data`, `chmod 750`).
* Security directives: Deny access to hidden files (`.git`, `.env`, `.bak`).

#### [NEW] [/etc/logrotate.d/thesimplechef](file:///etc/logrotate.d/thesimplechef)
* Automates daily log rotation with 7-day retention, gzip compression, and non-disruptive Nginx USR1 signal:
  ```text
  /var/log/nginx/thesimplechef_access.log /var/log/nginx/thesimplechef_error.log {
      daily
      missingok
      rotate 7
      compress
      delaycompress
      notifempty
      create 0640 client_web_user www-data
      sharedscripts
      postrotate
          [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat /var/run/nginx.pid`
      endscript
  }
  ```

---

### Phase 2: Dedicated ChromaDB Vector Analytics Pipeline

#### [NEW] [thesimplechef_analytics_daemon.py](file:///C:/AI-BS/backend/core/thesimplechef_analytics_daemon.py)
* Background daemon monitoring `/var/log/nginx/thesimplechef_access.log` or ingest queue:
  1. **IP Anonymization Engine:** Masks visitor IPs (e.g. `72.134.52.19` -> `72.134.52.xxx` or SHA256 salt) to comply with privacy frameworks before vectorization.
  2. **ChromaDB Client Integration:** Connects to local persistent ChromaDB (Port 8002) and initializes dedicated partition `thesimplechef_analytics_bin`.
  3. **Semantic Intent & Behavior Tagging:** Classifies requests (e.g., `Viewing BBQ Rubs`, `Tuesday Meal Customization`, `Cart Abandonment`, `Checkout Attempt`, `Bot Probing`).
  4. **Volumetric Memory Guard:** Dynamically tracks vector count (`MAX_VECTOR_COUNT = 50,000`, `PRUNE_BATCH_SIZE = 5,000`) ensuring the HNSW index never exceeds memory boundaries or threatens host RAM.

---

### Phase 3: Backend API Integration

#### [NEW] [chef_analytics_router.py](file:///C:/AI-BS/backend/routers/chef_analytics_router.py)
* Mounted on Port 8080 under `/api/v1/chef/analytics`:
  * `GET /api/v1/chef/analytics/overview`: Returns total hits, unique anonymized visitors, top dishes viewed, conversion funnel rate, and bot blocks.
  * `GET /api/v1/chef/analytics/semantic-insights`: Queries ChromaDB collection for recent customer browsing clusters (e.g., most engaged recipes, bounce reasons).
  * `POST /api/v1/chef/analytics/ingest-event`: Allows frontend telemetry (add-to-cart, modal opens) to be logged directly into the vector store.
  * `GET /api/v1/chef/analytics/export-pdf-summary`: Compiles a clean monthly traffic & revenue performance summary ready to email to John Barr to justify the monthly retainer.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
* Mount `chef_analytics_router` on Port 8080.
* Register `thesimplechef_analytics_daemon` into `daemon_supervisor` for autonomous background supervision.

---

### Phase 4: AI-BS Client Hub Frontend Upgrade (Rule 1: 4 Mirrors)

#### [MODIFY] [JohnBarr.jsx](file:///C:/AI-BS/frontend/src/components/clients/JohnBarr.jsx)
* Add a 5th interactive tab: **📊 Sovereign AI Analytics & Hosting Retainer**:
  * **Retainer Billing & Infrastructure Card:** Active tier ($75–$150/mo), renewal status, isolated vhost indicator, and 99.99% uptime badge.
  * **Semantic Traffic Flow:** ChromaDB vector cluster visualization showing user journeys (e.g., *Homepage -> Steak Frites -> Rub That Hiney -> Checkout*).
  * **Real-Time Privacy-First Metrics:** Total visits, page requests, top viewed meals, bot probes neutralized.
  * **Generate Monthly Client PDF Report:** 1-click button to download/email John his monthly executive traffic summary.
* Synchronize across all 4 mirror trees (`frontend/src/components/clients/`, `frontend/components/clients/`, `frontend/src/components/components/clients/`, `frontend/components/components/clients/`, `frontend/src/clients/`) with 100% SHA256 byte parity.

---

## Verification Plan

### Automated Tests
1. **Nginx Syntax & Virtual Host Verification:**
   - Run `wsl.exe -d Ubuntu -e sudo nginx -t` to confirm zero syntax errors.
   - Test reload with `wsl.exe -d Ubuntu -e sudo systemctl reload nginx`.
2. **Logrotate Simulation:**
   - Run `wsl.exe -d Ubuntu -e sudo logrotate -d /etc/logrotate.d/thesimplechef` to dry-run rotation rules.
3. **ChromaDB Vector Partition & Memory Test:**
   - Execute unit test `backend/scratch/test_chef_analytics_pipeline.py`:
     - Test collection instantiation `thesimplechef_analytics_bin`.
     - Test IP masking & embedding insertion.
     - Test volumetric pruning trigger when vector threshold is reached.
4. **FastAPI Endpoints Health Check:**
   - Verify `GET /api/v1/chef/analytics/overview` and `GET /api/v1/chef/analytics/semantic-insights`.

### Manual & UI Verification
1. Open the updated **JohnBarr.jsx** in AI-BS Dashboard (`http://localhost:5173` / `https://ai-bs-dashboard.web.app`).
2. Verify live metrics render cleanly in the new **📊 Sovereign AI Analytics** tab.
3. Confirm 100% SHA256 byte parity across all 4 frontend mirror paths.
4. Execute `npm run build` and `firebase deploy --only hosting` to update the production dashboard.
