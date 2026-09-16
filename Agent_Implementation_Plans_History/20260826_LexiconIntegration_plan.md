# Integrate Lexicographical Vault into AI-BS Ecosystem

This plan outlines the integration of the newly created `lexicon_vault.db` across the four critical phases of the AI-BS ecosystem. The goal is to provide the LLM with an enhanced offline vocabulary, expose it to satellites, augment semantic search, and enrich the Stehouwer Persona Engine.

## User Review Required

> [!WARNING]
> Please review the open questions below to clarify exact design decisions for the 4 phases before I begin implementation. We want to make sure the "hybrid" approach matches your vision perfectly.

## Open Questions

**Phase 1 (LLM Inference Pipeline)**:
1. **Pre-Processing Scope**: For the prompt pre-processor, should it scan *all* words in the user's prompt or only specific entities/keywords extracted via NLP (e.g. using `aibs_nlp_analysis.py`)?
2. **Post-Processing Aggressiveness**: For the post-processor, how aggressively should it replace words? Should it only replace simple adjectives/verbs, or do you want a specific heuristic threshold for substitution?

**Phase 2 (FastAPI Satellites)**:
3. **Endpoint Needs**: Does `BroadcastStudioApp` need a simple `/api/lexicon/synonyms?word=...` endpoint, or should we include advanced filtering (like grouping by parts of speech from Wordset)?

**Phase 3 (ChromaDB Integration)**:
4. **Embedding Strategy**: Should we inject synonyms into the text *before* it gets embedded by ChromaDB, or should we expand the user's query at search time (i.e. query expansion)?

**Phase 4 (Persona Engine)**:
5. **Heuristic Integration**: Should we add a new heuristic to `stehouwer_vault.db` that strictly forces the Persona Engine to prioritize Lexicon Vault terminology when generating dialogue?

## Proposed Changes

### Core / Lexicon API
#### [NEW] backend/core/lexicon_service.py
- Will contain the unified wrapper for `lexicon_vault.db`.
- Functions: `get_synonyms(word)`, `bulk_expand(text)`, `hybrid_tool_lookup(word)`.

### Phase 1: LLM Inference Pipeline
#### [MODIFY] backend/aibs_reasoning_engine.py
- **Pre-processor**: Inject contextual synonyms into the context block before sending the prompt to Ollama/Gemini.
- **Tool Callable**: Add a new tool for the LLM to call `get_synonyms()` mid-generation.
- **Post-processor**: Regex-based token replacement for output augmentation.

### Phase 2: FastAPI Exposure
#### [MODIFY] backend/main.py
- Create new endpoints: `GET /lexicon/synonyms` and `POST /lexicon/enrich`.

### Phase 3: ChromaDB Vector Memory
#### [MODIFY] backend/chroma_vault_service.py
- Intercept search queries, pass them through `lexicon_service.bulk_expand(text)`, and execute a multi-query search against ChromaDB.

### Phase 4: Stehouwer Persona Engine
#### [MODIFY] backend/aibs_nlp_analysis.py & backend/bullshit_heuristics_daemon.py
- Hook the lexicon engine into the heuristics generator. Adjust the Stehouwer LLM prompts to favor these newly injected vocabulary tokens.

## Verification Plan

### Automated Tests
- Create and run `test_lexicon_integration.py` to ensure the API, preprocessing, and DB retrieval work securely.

### Manual Verification
- Test LLM generation using the hybrid approach to ensure vocabulary is noticeably elevated without hallucinations.
- Test the new `/lexicon/synonyms` endpoint via curl.
- Verify ChromaDB returns broader semantic matches.
