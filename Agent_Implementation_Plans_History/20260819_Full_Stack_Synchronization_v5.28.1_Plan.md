# Implementation Plan: Full-Stack Communication & Endpoint Synchronization

Plan to patch backend route definitions, mount prefixes, alias endpoints, and fix frontend relative component imports identified in the **AI-BS Deep Scan Audit**.

```mermaid
flowchart TD
    subgraph Backend Routing Patches (AI_BS_Backend.py)
        A[data_feed_router] -->|Mount with prefix='/api'| B[/api/feeds/latest/{topic}]
        C[Endpoint Aliases] --> D[/api/terminal/run]
        C --> E[/api/chia-stop]
        C --> F[/api/trainer/status]
        C --> G[/api/git/status & /api/git/system/pull]
        C --> H[/api/crypto/liquidate_all]
    end

    subgraph Frontend Import Alignment
        I[ChatTab.jsx] -->|Fix relative import| J[../TerminalPanel]
        K[SystemEconomicsDashboard.jsx] -->|Remove missing ./ui/card| L[Inline Clean Card UI]
        M[TerminalPanelWrapper.jsx] -->|Fix relative imports| N[../components/AdvertisingTab]
    end

    B & D & E & F & G & H & J & L & N --> O[⚡ 100% Full-Stack Synchronization & Clean Vite Build]
```

## User Review Required

> [!IMPORTANT]
> **Backend Route Aliasing**:
> - We will update `AI_BS_Backend.py` to include `data_feed_router` under `app.include_router(data_feed_router, prefix="/api")` so all 71 industry hubs can fetch real-time topic feeds without 404s.
> - We will add alias endpoints:
>   - `@app.post("/api/terminal/run")` ➔ maps to `polyglot_execute`
>   - `@app.post("/api/chia-stop")` ➔ stops active Chia plotting/farming daemon
>   - `@app.get("/api/trainer/status")` ➔ returns model trainer status
>   - `@app.get("/api/git/status")` & `@app.post("/api/git/system/pull")` ➔ returns local git status and pulls latest
>   - `@app.post("/api/crypto/liquidate_all")` ➔ triggers emergency TWAP liquidation engine

> [!TIP]
> **Frontend Import Patches**:
> - `c:\AI-BS\frontend\src\components\ChatTab.jsx`: Update `./TerminalPanel` to `../TerminalPanel`.
> - `c:\AI-BS\frontend\components\SystemEconomicsDashboard.jsx`: Replace missing `./ui/card` with lightweight container styles.
> - `c:\AI-BS\frontend\src\TerminalPanelWrapper.jsx`: Update `./AdvertisingTab` and `./VisualScriptingTab` to `../components/AdvertisingTab` and `../components/VisualScriptingTab`.

## Open Questions

> [!NOTE]
> None. All route mappings match existing backend daemon handlers.

## Proposed Changes

---

### Component 1: Backend Router Inclusions & Alias Endpoints
[MODIFY] [AI_BS_Backend.py](file:///c:/AI-BS/backend/AI_BS_Backend.py)
- Mount `data_feed_router` with `prefix="/api"`.
- Add alias routes for `/api/terminal/run`, `/api/chia-stop`, `/api/trainer/status`, `/api/git/status`, `/api/git/system/pull`, and `/api/crypto/liquidate_all`.

---

### Component 2: Frontend Import Path Fixes
[MODIFY] [ChatTab.jsx](file:///c:/AI-BS/frontend/src/components/ChatTab.jsx)
- Fix relative import of `TerminalPanel`.

[MODIFY] [SystemEconomicsDashboard.jsx](file:///c:/AI-BS/frontend/components/SystemEconomicsDashboard.jsx)
- Replace missing `./ui/card` import with clean inline Card layout components.

[MODIFY] [TerminalPanelWrapper.jsx](file:///c:/AI-BS/frontend/src/TerminalPanelWrapper.jsx)
- Fix relative imports for `AdvertisingTab` and `VisualScriptingTab`.

## Verification Plan

### Automated Build Verification
- Execute `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` in `c:\AI-BS\frontend` to confirm clean compilation and live deployment.

### Manual & Functional Verification
1. Verify `/api/feeds/latest/technology` returns valid feed JSON.
2. Verify terminal command execution via `/api/terminal/run`.
3. Verify live deployment at `https://ai-bs-dashboard.web.app`.
