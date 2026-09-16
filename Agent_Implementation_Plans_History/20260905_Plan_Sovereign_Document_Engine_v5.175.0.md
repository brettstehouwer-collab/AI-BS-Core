# Fix BS-Chat Large Markdown Ingestion & Sovereign Stream Connection

## Overview
When attempting to attach and read large Markdown files (such as `Matthew.md` at 132.9 KB, ~35,000 tokens) in BS-Chat, the streaming response failed with `Error in sovereign stream connection: All connection attempts failed`. This was caused by a combination of:
1. **Ollama Instance Inactive on Port 11434:** `Launch_AI_BS.bat` launched port 11435 for E-Drive models, but port 11434 (where `stehouwer_llm` is hosted in `C:\AI-BS\.ollama\models`) was not running or failed silently.
2. **Memory Vault & Lexicon Explosion on Massive Documents:** When `prompt` contained 132.9 KB (23,000+ words), `SovereignMemoryVault.get_unified_context` passed the entire text into `LexiconService.bulk_expand`, initiating 3,000+ sequential SQLite queries that blocked the event loop and caused httpx connection drops.
3. **Context Window Overflow:** `stehouwer_llm` has an 8,192 token context window. Passing 35,000 raw tokens without `num_ctx` configuration (which defaults to 2,048 in Ollama) caused Ollama to choke or drop connections.
4. **Lack of Dynamic Ollama Failover and Self-Healing:** The backend dispatcher lacked automatic port failover (11434 -> 11435) and auto-recovery daemon triggers.

---

## User Review Required
> [!IMPORTANT]
> - All changes use 100% free local models (`stehouwer_llm` on port 11434, fallback to 11435).
> - Large documents (>20 KB) will be processed with our new **Smart Document Engine**: building a chapter/section index and extracting targeted content (or structured executive breakdown) so that Stehouwer LLM can analyze any size Markdown document without overflowing the 8,192 token limit.
> - Frontend will be rebuilt and automatically deployed to `https://ai-bs-dashboard.web.app` in compliance with our strict deployment rules.

---

## Proposed Changes

### 1. Ollama Launch Configuration & Auto-Recovery
#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
- Fix line 33 to explicitly set `$env:OLLAMA_HOST='0.0.0.0:11434'` and `$env:OLLAMA_MODELS='C:\AI-BS\.ollama\models'` so both primary (port 11434) and secondary (port 11435) Ollama instances always boot reliably.

### 2. Backend Sovereign Reasoning Dispatcher & Self-Healing
#### [MODIFY] [dispatcher.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py)
- Add multi-port resilience: checks `127.0.0.1:11434`, fails over to `127.0.0.1:11435`, and auto-starts Ollama if neither is listening.
- Extract clean user intent from `prompt` (stripping attached file payloads before running telemetry/system tool checks, historical search, and memory vault).
- Integrate `options: {"num_ctx": 8192}` for maximum context utilization.
- Integrate `SovereignDocumentEngine` to handle large document attachments seamlessly.

### 3. Smart Document Context Engine
#### [NEW] [document_engine.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/document_engine.py)
- Inspects attached documents: detects chapters, headers, verse patterns, line counts, and file structure.
- If document is within 20KB (< 5,000 tokens), passes complete text directly to the model.
- If document exceeds 20KB (like `Matthew.md` at 133KB):
  - Parses chapter/section index.
  - If user prompt requests specific chapters or keywords (e.g. "Chapter 1", "Genealogy", "Beatitudes"), extracts matching chapters in full detail.
  - If user prompt asks for general analysis or summary, supplies an executive structural map with first chapters, key milestones, final chapters, and a complete chapter directory so the model answers authoritatively.

### 4. Memory Vault & Lexicon Optimization
#### [MODIFY] [memory_vault.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/memory_vault.py)
- Ensure only the user's actual question/prompt is passed to historical and lexicon search.
#### [MODIFY] [lexicon_service.py](file:///C:/AI-BS/backend/core/lexicon_service.py)
- Optimize `bulk_expand`: reuse a single SQLite connection and cap lookup to top 15 significant keywords.
#### [MODIFY] [stehouwer_history_retriever.py](file:///C:/AI-BS/backend/core/stehouwer_history_retriever.py)
- Cap FTS query terms to avoid query parser explosion.

### 5. Frontend Streaming & Large Attachment Feedback
#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx)
- Display smart document indexing indicator when files > 50KB are attached.
- Improve error messages and auto-recovery in case of stream disconnects.

### 6. Ledgers & Deployment
#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Build frontend (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Sync master ledgers and version history.

---

## Verification Plan
### Automated Tests
1. Test Ollama dual port check (`curl.exe -s http://127.0.0.1:11434/api/tags` and `11435`).
2. Run python script `test_matthew_stream.py` to verify streaming response with `Matthew.md` (132.9 KB) succeeds without connection error and returns a complete analysis of Chapter 1 of Matthew.
3. Test targeted chapter query ("What happens in Matthew Chapter 28?") with `Matthew.md` attached.
4. Verify Lexicon and History retrieval executes in < 5ms without blocking.
5. Verify `npm run build` passes cleanly and Firebase deployment succeeds.
