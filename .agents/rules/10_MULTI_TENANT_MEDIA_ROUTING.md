# Multi-Tenant & Frontend Media Routing Standard

**Status:** ACTIVE & MANDATORY DIRECTIVE  
**Classification:** API Architecture & Web Frontend Standards  

## Directives
1. **Dynamic Frontend Media Routing:** All image `src` and media references rendered inside React components or markdown (`ChatTab.jsx`, `NotosEnterpriseOSTab.jsx`, etc.) MUST dynamically append `BACKEND_URL` if relative:
   ```javascript
   src={imgUrl.startsWith('http') ? imgUrl : `${BACKEND_URL}${imgUrl}`}
   ```
2. **Multi-Tenant Header & Schema Isolation:**
   - All FastAPI endpoints MUST extract `X-Client-ID` using `Depends(get_tenant)` with a fallback to `'stehouwer_publishing'`.
   - All SQLite database tables MUST enforce `client_id TEXT DEFAULT 'stehouwer_publishing'`.
   - ChromaDB vector metadata MUST include `"client_id": "stehouwer_publishing"`.
3. **System Boot Launcher Verification:** Whenever any backend, frontend, daemon, or environment configuration is modified, inspect `C:\AI-BS\Launch_AI_BS.bat` to verify that all relative directory paths, startup timeouts, and port allocations match the updated architecture.
