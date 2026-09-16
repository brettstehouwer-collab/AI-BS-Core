# AI-BS DAW Browser Junction Streaming Patch Tasks (v5.105.0)

## Backend Junction Reload
- [x] Restart FastAPI backend on Port 8080 applying `ALLOWED_ROOTS` for physical NVMe `E:\` folders.
- [x] Verify HTTP 200 responses on `/api/drive/files` for `/4 media/Cymatics_Sound_Banks` (31 folders) and `/4 media/Muse_Hub_Instruments` (10 folders).

## Frontend Browser Resilience
- [x] Add multi-endpoint fallback in `Browser.jsx` (`http://127.0.0.1:8080`, `http://localhost:8080`, `http://127.0.0.1:8000`, relative).
- [x] Skip drive fetching when on `__suno_stems__` virtual drawer tab.
- [x] Connect audio auditioning to dynamic `previewUrl` with active backend host.
- [x] Rebuild and deploy frontend to Firebase Hosting (`ai-bs-dashboard.web.app`).
