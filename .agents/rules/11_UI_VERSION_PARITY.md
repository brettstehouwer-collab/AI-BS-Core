# UI Version Parity & Build Synchronization Rule

**Status:** ACTIVE & MANDATORY DIRECTIVE  
**Classification:** Version Control & Frontend Consistency  

## Directives
1. **Universal Version Sweeps:** Whenever you increment the system version number in the master architectural ledgers, you MUST also sweep the frontend UI codebase and manually update the hardcoded version badges to perfectly match the new ledger version.
2. **Synchronized Target Files:**
   - `version.txt`
   - `frontend/package.json`
   - `frontend/public/version.json`
   - `frontend/public/updates/version.json`
   - `frontend/public/sw.js`
   - `frontend/App.jsx`
   - `frontend/src/components/TopNavbar.jsx`
   - `frontend/src/components/Sidebar.jsx`
   - `frontend/src/components/ChatTab.jsx`
   - All component mirrors (`frontend/components/`, `frontend/src/components/components/`, `frontend/components/components/`)
3. **Zero Discrepancy Standard:** Version badges rendered in headers, sidebars, and chat headers must never show stale version numbers or mismatch the production release tag.
