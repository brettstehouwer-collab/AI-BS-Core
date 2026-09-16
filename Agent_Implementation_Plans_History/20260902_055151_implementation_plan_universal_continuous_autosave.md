# Implementation Plan: Universal Continuous Auto-Save & Episodic Memory System

Enable **100% continuous, automatic persistence** of everything executed across the AI-BS ecosystem and within BS-Chat into the local SQLite FTS5 Personal Intelligence & Episodic Lore Vault (`database/aibs_personal_intelligence.db`).

---

## Proposed Architectural Flow

```
   ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
   │    BS-Chat Prompts     │   │  Program Builder Runs  │   │  OSINT / Matrix Doctor │
   │   & Assistant Streams  │   │     & Script Builds    │   │  Diagnostics & Trades  │
   └───────────┬────────────┘   └───────────┬────────────┘   └───────────┬────────────┘
               │                            │                            │
               └────────────────────┬───────┴────────────────────────────┘
                                    │
                                    ▼
         ┌────────────────────────────────────────────────────────┐
         │     Asynchronous Auto-Save & Event Collector Hook      │
         │  (backend/core/personal_intelligence_memory.py)        │
         └───────────────┬────────────────────────┬───────────────┘
                         │                        │
         Background Fact │                        │ Chronological
         Extraction / NLP│                        │ Event Logging
                         ▼                        ▼
         ┌────────────────────────┐     ┌────────────────────────┐
         │     memory_facts       │     │     episodic_logs      │
         │ (Rules, Habits, Specs) │     │ (Full History Timeline)│
         └────────────────────────┘     └────────────────────────┘
```

---

## User Review Required

> [!IMPORTANT]
> - **Zero Manual Clicking Required:** Every message typed, tool executed, program compiled, lead scanned, or preference declared is saved automatically to local NVMe disk immediately in the background without blocking the UI.
> - **Never Forgets Across Restarts:** When you refresh the browser, reopen the desktop app, or start a new conversation next month, your entire chat history, custom rules, and activity lore remain stored and ready for instant search.

---

## Proposed Changes

### 1. Core Engine Extensions (`backend/core/personal_intelligence_memory.py`)
- `log_interaction_and_auto_extract(user_prompt, assistant_response, client_id, user_id)`:
  - Logs full interaction to `episodic_logs` with timestamps and tokens.
  - Automatically runs heuristic NLP regex + entity extractors to detect new user habits, project decisions, preferred technologies, and business rules, inserting them into `memory_facts`.
- `record_ecosystem_event(event_type, summary, metadata, client_id, user_id)`:
  - Records events from any AI-BS module (e.g., `program_built`, `osint_recon_completed`, `health_audit_run`, `crypto_take_profit`, `audio_rendered`).
- `get_activity_timeline(client_id, limit=50)`:
  - Fetches the unified chronological activity feed of all actions taken across the ecosystem.

---

### 2. Backend Subsystem Event Hooks
- **`backend/core/sovereign_reasoning/dispatcher.py` & `AI_BS_Backend.py`:**
  - Fire `log_interaction_and_auto_extract` after every completed stream response.
- **`backend/core/program_builder_engine.py`:**
  - Fire `record_ecosystem_event("program_built", f"Scaffolded and tested {project_name}", ...)` upon successful generation.
- **`backend/core/real_system_tools.py`:**
  - Fire `record_ecosystem_event("system_diagnostic", ...)` and `record_ecosystem_event("osint_recon", ...)` on execution.

---

### 3. API Router (`backend/routers/personal_intelligence_router.py`)
- `POST /api/memory/personal/log_event`: Allows frontend components or external daemons to log custom events.
- `GET /api/memory/personal/activity`: Returns the unified chronological activity log.

---

### 4. Frontend BS-Chat & Artifacts Hub Integration
- **`ChatTab.jsx`:**
  - Ensure local state auto-saves all messages to `localStorage` keyed by thread ID so page reloads never wipe conversation history.
  - Add a **"🟢 Memory Auto-Save: Active"** status badge in the input bar.
- **`ArtifactsAndToolsModal.jsx`:**
  - Add an **"📜 Live Activity Timeline & Episodic Lore"** sub-tab showing the real-time record of all actions, prompts, and auto-learned memories.

---

## Verification Plan

### Automated Tests
1. Python test script invoking `log_interaction_and_auto_extract` and verifying `episodic_logs` and `memory_facts` rows in SQLite.
2. Test `record_ecosystem_event` across program building, OSINT scanning, and Matrix Doctor runs.
3. Test API endpoint `GET /api/memory/personal/activity`.

### Manual Verification
1. Send a prompt in BS-Chat: *"Remember that I prefer all Python scripts to include type annotations and docstrings."*
2. Check the **"🧠 Personal Intelligence"** modal to verify that the rule was automatically extracted and saved.
3. Refresh the page to confirm that the chat history and memory bank remain intact.
4. Run `npm run build` and `firebase deploy --only hosting --non-interactive` to confirm live production parity.
