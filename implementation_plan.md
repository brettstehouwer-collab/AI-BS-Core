# Implementation Plan: Real-Time User Presence, Dynamic Firebase Roster Synchronization & Session Audit Telemetry (v5.295.0)

Dynamic user session presence, dwell time tracking, and session audit telemetry across all authorized Firebase users in the AI-BS ecosystem.

---

## User Review Required

> [!IMPORTANT]
> **Dynamic Authorized Firebase Roster:**
> Removes all hardcoded restrictions in the user session audit ledger. Any user saved and authenticated via Firebase Authentication or Firestore is dynamically registered, displayed in live online operator cards and last-seen cards, and provided in the filter dropdown.

---

## Proposed Architectural Changes

### 1. SQLite Dynamic User Presence & Session Audit Engine
- `backend/modules/user_session_telemetry.py`:
  - `registered_users` table in `data/user_sessions.db` storing `user_email`, `user_name`, `user_avatar`, `user_role`, `user_color`, `is_authorized`, `updated_at`.
  - `sync_authorized_users(users_list)`: Ingests Firebase Firestore user rosters into SQLite.
  - `record_heartbeat()`: Auto-registers and upserts any user emitting a heartbeat.
  - `get_summary()`: Reads all registered users from SQLite and joins with active session metrics.

### 2. REST API Roster Sync Endpoint
- `backend/modules/telemetry_matrix_router.py`:
  - Added `POST /api/telemetry/user-sessions/sync-users` accepting `SyncUsersRequest(users: List[Dict[str, Any]])`.
  - Connected to Port 8080.

### 3. Dynamic Client Telemetry Widget
- `frontend/src/components/UserSessionTelemetryWidget.jsx`:
  - Real-time Firestore snapshot listener on `collection(db, 'users')`.
  - Continuous synchronization with backend `/api/telemetry/user-sessions/sync-users`.
  - Manual `☁️ Sync Firebase Roster` button for on-demand sync.
  - Dynamic `All Operators (N)` select dropdown populated from all discovered operators.
  - Section 1: Live online operator cards with dwell time, active tool, platform, and last ping.
  - Section 2: Last-seen cards and total time spent for every registered user.
  - Section 3: Chronological session audit ledger with search and operator filters.

### 4. Dynamic Authentication Authorization
- `frontend/App.jsx` & `frontend/src/components/accessControl.js`:
  - `onAuthStateChanged` updated so any user authenticated through Firebase Auth is granted authorized access.
  - Saves user profile with role in Firestore `users/{uid}`.
  - Added executive aliases to `ADMIN_EMAILS`.
  - `TeamChatDrawer.jsx` updated to merge all Firestore users dynamically.

### 5. Multi-Mirror Parity & Cloud Deployment
- Verified 100% SHA256 mirror parity across all 430 files in all 4 frontend mirrors (`scripts/sync_mirrors.py`).
- Bumped version authority to `v5.295.0` in `package.json`, `version.txt`, `public/version.json`, `public/sw.js`, and UI badges.
- Production Vite bundle compiled.
- Deployed live to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
