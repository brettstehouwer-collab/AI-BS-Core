# Prestige Mobile Wash: Phase 3 (Backend Integration & Release)

The goal of Phase 3 is to deploy the Python FastAPI backend to a live cloud environment so the standalone `.exe` can hit it remotely from the field. 

Through my ecosystem research, I discovered a massive shortcut: **We do not need to pay for a VPS or set up Google Cloud Run.** Your `Launch_AI_BS.bat` is *already* running a secure **Cloudflare Tunnel** mapping `https://api.brettstehouwer.live` to the local AI-BS Go Gateway/Python Backend!

The only reason it wasn't working earlier is that your core Python backend process (`AI_BS_Backend.py`) has been running for 24+ hours and hadn't loaded the brand new `power_washing_router.py` we wrote today. 

## Proposed Architecture

1. **Soft Restart FastAPI:** We will surgically kill the stale `python` process listening on port `8080` and restart it via `Launch_AI_BS.bat` commands so it ingests the new power washing endpoints.
2. **Cloudflare Tunnel Test:** Verify that `https://api.brettstehouwer.live/api/powerwash/telemetry` returns active GIS/telemetry data rather than an "unhandled" error.
3. **Environment Configuration:** Inject `VITE_BACKEND_URL=https://api.brettstehouwer.live` into `C:\AI-BS\PrestigeMobileWash\.env` so the standalone executable routes all traffic securely to your home base server.

## Proposed Changes

### Backend Infrastructure

#### [MODIFY] Local Machine (Memory / Processes)
- Kill PID handling port `8080` (stale Python backend).
- Run: `powershell Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\python.exe' -ArgumentList 'AI_BS_Backend.py' -WorkingDirectory '%BASE_DIR%backend' -WindowStyle Hidden`

### Client Configuration

#### [NEW] [PrestigeMobileWash/.env](file:///C:/AI-BS/PrestigeMobileWash/.env)
- Hardcode `VITE_BACKEND_URL=https://api.brettstehouwer.live`

#### [MODIFY] [PrestigeMobileWash/src/App.jsx](file:///C:/AI-BS/PrestigeMobileWash/src/App.jsx)
- Ensure the standalone app prioritizes the `.env` variable for production routing.

## Verification Plan

### Automated Verification
- I will execute a direct `curl.exe` against the live Cloudflare endpoint to verify the backend is securely exposed to the public internet.
- I will execute `npm run build` in `PrestigeMobileWash` to bake the environment variable into the production build.

### Manual Verification
- You will launch the freshly packaged `PrestigeMobileWash` standalone `.exe`.
- Ensure data correctly loads into the Telemetry tab, GIS tab, and CRM from the live remote server.

> [!IMPORTANT]  
> If this plan looks good, hit **Proceed**. Once approved, I will immediately execute the backend restart and package the final standalone release.
