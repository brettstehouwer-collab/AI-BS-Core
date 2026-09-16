# Implementation Plan: Business Email Client (v5.192.0) - Compliance API, Dynamic Counts & Telemetry Fixes

Implement the 5 issues identified during browser automation and component inspection of `http://localhost:5173/?tab=email_client`:

1. **Compliance Analyzer API (High)**:
   - Root cause: `ContentGovernanceRiskModal.jsx` fetched relative path `/api/v1/content-governance/analyze`, hitting static server port 5173 which returned HTTP 501 Unsupported method ('POST').
   - Fix: Import `getApiBase()` from `../config/api` and target `${getApiBase()}/api/v1/content-governance/analyze` (Go engine Port 8000 / FastAPI Port 8080).
2. **Filtered Counts (Medium)**:
   - Root cause: Sidebar badge (`70,208`) and header pagination (`1-100 of 80,532`) were hardcoded numbers.
   - Fix: Compute `inboxUnreadCount` and total filtered items dynamically based on `selectedAccount` and `filteredEmails.length`.
3. **Sender/Subject Collision (Low)**:
   - Root cause: `styles.emailRow` lacked a `gap` property, causing 180px sender names to touch the subject line with zero buffer.
   - Fix: Add `gap: '12px'` to `emailRow`, add `flexShrink: 0`, `minWidth: '180px'`, and `paddingRight: '8px'` to `senderCell`, and `minWidth: 0` to `subjectCell`.
4. **Dropdown Truncation (Low)**:
   - Root cause: Sidebar width was 240px with select input padding clipping the closing parenthesis in `📬 All Accounts (Unified Inbox)`.
   - Fix: Widen `folderSidebar` to `260px` and set `width: '100%'` with clean padding.
5. **Telemetry Math (Cosmetic)**:
   - Root cause: `CampaignAutomationTab.jsx` displayed hardcoded string literals `Opens (75%)`, `Clicks (40%)`, and `Bounces (0%)`.
   - Fix: Implement dynamic percentage calculations: `Math.round((count / sent_count) * 100)`.
6. **Ecosystem Synchronization & Deployment**:
   - Bump version to `v5.192.0`.
   - Compile production frontend bundle (`npm run build`).
   - Deploy live to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
   - Synchronize master ledgers and manuals.
