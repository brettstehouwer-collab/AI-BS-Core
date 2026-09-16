# Tasks: Fix BS-Chat Large Markdown Ingestion & Sovereign Stream Connection

- [x] Fix Ollama Launch Configuration & Failover <!-- id: 0 -->
  - [x] Update `Launch_AI_BS.bat` line 33 to guarantee port 11434 starts with explicit `$env:OLLAMA_HOST` and `$env:OLLAMA_MODELS` <!-- id: 1 -->
  - [x] Add dual-port failover (11434 -> 11435) and auto-recovery in `dispatcher.py` <!-- id: 2 -->
- [x] Optimize Memory Vault & Lexicon Services <!-- id: 3 -->
  - [x] In `core/lexicon_service.py`, cap `bulk_expand` to 15 keywords and reuse single SQLite connection <!-- id: 4 -->
  - [x] In `core/stehouwer_history_retriever.py`, cap query terms to 15 <!-- id: 5 -->
  - [x] In `core/sovereign_reasoning/dispatcher.py`, isolate clean user query from attached file payload before searching memory/tools <!-- id: 6 -->
- [x] Build Sovereign Document Engine for Large Attachments <!-- id: 7 -->
  - [x] Create `core/sovereign_reasoning/document_engine.py` to index chapters, detect targeted queries, and slice large documents (>20KB) within the 8,192 token window <!-- id: 8 -->
  - [x] Integrate `document_engine.py` and `options: {"num_ctx": 8192}` into `dispatcher.py` <!-- id: 9 -->
- [x] Enhance Frontend Streaming & Attachment UX <!-- id: 10 -->
  - [x] Update `ChatTab.jsx` to show smart document indexing badge and improve stream error handling <!-- id: 11 -->
- [x] Verification & End-to-End Testing <!-- id: 12 -->
  - [x] Run automated python streaming test with `Matthew.md` (132.9 KB) <!-- id: 13 -->
  - [x] Verify chapter-targeted queries work cleanly <!-- id: 14 -->
  - [x] Build and deploy frontend to Firebase Hosting <!-- id: 15 -->
  - [x] Update Master Architectural Ledger and Ecosystem Manual <!-- id: 16 -->
