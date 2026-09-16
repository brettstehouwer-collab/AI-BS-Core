# Implementation Plan: AI-BS Sovereign Personal Intelligence & Long-Term Memory Bank

Design and deploy a dedicated, 100% local, persistent **Personal Intelligence & Long-Term Memory Bank System** tailored specifically for Brett Stehouwer, Sean, Julie, and the AI-BS ecosystem—mirroring Gemini's cross-session personalization and memory recall, but operating entirely on local NVMe SQLite FTS5, ChromaDB, and sovereign reasoning models.

---

## Proposed Architectural Design

```
                     ┌────────────────────────────────────────────────────────┐
                     │            User Prompt (BS-Chat / Terminal)            │
                     └───────────────────────────┬────────────────────────────┘
                                                 │
                                                 ▼
                     ┌────────────────────────────────────────────────────────┐
                     │     AI-BS Personal Intelligence Memory Engine          │
                     │  (backend/core/personal_intelligence_memory.py)        │
                     └───────────────┬───────────────────────┬────────────────┘
                                     │                       │
               Semantic Memory Query │                       │ Async Fact Extractor
           (Sub-ms BM25 + ChromaDB)  │                       │ (Background Pattern Log)
                                     ▼                       ▼
            ┌───────────────────────────────────┐ ┌───────────────────────────────────┐
            │  database/aibs_personal_          │ │  database/aibs_personal_          │
            │  intelligence.db (FTS5 WAL Table) │ │  intelligence.db (Memory Facts)   │
            └────────────────┬──────────────────┘ └───────────────────────────────────┘
                             │
                             ▼ Top-5 Relevant Personal Facts
            ┌───────────────────────────────────────────────────┐
            │ Injected into [SOVEREIGN PERSONAL MEMORY CONTEXT] │
            │      (backend/core/sovereign_reasoning/...)       │
            └────────────────────────┬──────────────────────────┘
                                     │
                                     ▼
            ┌───────────────────────────────────────────────────┐
            │           Stehouwer LLM / Local Model Core        │
            │    (Personalized, Context-Aware Response Output)   │
            └───────────────────────────────────────────────────┘
```

---

## User Review Required

> [!IMPORTANT]
> - **100% Free & Local:** All embeddings, vector storage, and SQLite tables run entirely on your local PC (NVIDIA RTX 4090 / NVMe SSD) with zero paid cloud API calls or subscriptions.
> - **Full User Control & Transparency:** A dedicated **"🧠 Personal Memory Vault"** UI tab will allow you to inspect, edit, add, or delete any memory fact stored about you or your businesses at any time.

---

## Proposed Changes

### 1. Database Schema (`database/aibs_personal_intelligence.db`)
- **`user_profiles`**: User metadata (`user_id`, `client_id`, `display_name`, `role`, `bio`, `theme_preferences`).
- **`memory_facts`**: Declarative facts and guidelines with metadata:
  - `id`, `client_id`, `user_id`, `category` (`preferences`, `hardware`, `businesses`, `coding_patterns`, `directives`), `fact_text`, `importance_score` (1-10), `is_pinned` (0/1), `source`, `created_at`, `updated_at`.
- **`memory_facts_fts`**: SQLite FTS5 virtual table indexing `fact_text` and `category` for sub-0.5ms BM25 ranking.
- **`episodic_logs`**: Chronological event milestones, key past session decisions, and resume keywords.

---

### 2. Core Engine (`backend/core/personal_intelligence_memory.py`)
- `PersonalIntelligenceEngine`:
  - `get_relevant_memories(prompt, client_id, limit=5)`: Semantic hybrid retrieval combining FTS5 keyword relevance with memory importance weights.
  - `add_memory_fact(...)`, `update_memory_fact(...)`, `delete_memory_fact(...)`.
  - `extract_facts_from_conversation(user_prompt, assistant_response)`: Asynchronous rule-based + local LLM parser extracting new user preferences and persisting them.
  - `format_system_prompt_block(client_id, user_prompt)`: Returns a clean markdown grounding block for injection into `dispatcher.py`.

---

### 3. API Router (`backend/routers/personal_intelligence_router.py`)
- `GET /api/memory/personal`: Returns all stored personal memories grouped by category with stats.
- `POST /api/memory/personal/add`: Adds a new explicit personal memory rule or fact.
- `PUT /api/memory/personal/update/{fact_id}`: Edits an existing memory.
- `DELETE /api/memory/personal/delete/{fact_id}`: Deletes/forgets a specific memory.
- `POST /api/memory/personal/query`: Live semantic search tester.
- `POST /api/memory/personal/extract`: Triggers on-demand memory extraction.

---

### 4. Sovereign Reasoning Dispatcher Integration (`backend/core/sovereign_reasoning/dispatcher.py`)
- Automatically retrieve matching personal memories for the active user prompt and append `[PERSONAL INTELLIGENCE & USER KNOWLEDGE BANK]` directly into `stehouwer_system_prompt`.

---

### 5. Frontend UI Management Vault (`ArtifactsAndToolsModal.jsx` & `ChatTab.jsx`)
- Add **"🧠 Personal Intelligence"** tab in `ArtifactsAndToolsModal.jsx` allowing Brett, Sean, and Julie to:
  - Search and filter memories by category (Preferences, Hardware, Businesses, Directives).
  - Add custom personal rules (e.g., "Always use dark neon theme", "Always prioritize Cronos reinvestment").
  - Delete or pin memories.
  - View total memory facts count and live sync timestamp.

---

## Verification Plan

### Automated Tests
1. Python unit tests verifying SQLite database creation, FTS5 virtual table indexing, and WAL mode.
2. Verification of memory insertion, category filtering, and semantic BM25 ranking.
3. Test API endpoints (`GET /api/memory/personal`, `POST /api/memory/personal/add`, `DELETE /api/memory/personal/delete/{id}`).
4. Test dynamic prompt injection in `stream_sovereign_response`.

### Manual Verification
1. Open BS-Chat in the browser, open the **"📦 Artifacts & Tools"** hub, switch to **"🧠 Personal Intelligence"**, and add a custom memory rule.
2. Ask BS-Chat a question that relies on personal preferences to confirm memory recall in the response.
3. Run `npm run build` and `firebase deploy --only hosting --non-interactive` to verify live production deployment.
