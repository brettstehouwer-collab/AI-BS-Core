# Stehouwer LLM: Core NLP Expansion Matrix

We are expanding the Stehouwer LLM's natural language processing capabilities by shifting from purely probabilistic text generation to a rigid, multi-perspective algorithmic framework. This implementation incorporates the decisions established during our architectural review.

## User Review Required
> [!IMPORTANT]
> Please review the proposed multi-model synthesis logic in Phase 3. The integration requires installing `spacy` in the backend environment and adjusting `aibs_reasoning_engine.py`.

## Proposed Changes

---

### Phase 1 & 2: Foundational Parsing & Flattening (Hybrid Approach)
We will integrate `spaCy` into the backend environment to handle Tokenization, POS Tagging, NER, and Semantic Role Labeling (SRL). 

#### [MODIFY] [aibs_reasoning_engine.py](file:///C:/AI-BS/backend/aibs_reasoning_engine.py)
- **New Class**: `AIBSHybridNLPParser`
  - Loads a `spaCy` transformer pipeline (e.g., `en_core_web_trf`).
  - Flattens user input, extracting root dependency nodes (verbs) and mapping exact "who did what to whom" semantic relationships.
  - Strips emotional bias from the physical syntax structure before vectorization.

### Phase 2 & 5: Persistence & Vector Routing
The output of the NLP parser will be routed simultaneously to a temporal knowledge graph and long-term vector storage.

#### [MODIFY] [chroma_storage.py](file:///C:/AI-BS/backend/chroma_storage.py)
- **Enhancement**: When embedding a prompt, `chroma_storage.py` will now attach the `spaCy` Dependency Parse and Named Entities as highly structured metadata in ChromaDB.
- **Why**: This mathematically anchors abstract nouns (like trauma or anhedonia) based on their parsed syntax, allowing retrieval based on structural semantic similarity rather than just text match.

#### [MODIFY] [aibs_reasoning_engine.py](file:///C:/AI-BS/backend/aibs_reasoning_engine.py)
- **Update**: `AIBSGraphReasoningEngine` will directly consume the output from `AIBSHybridNLPParser` to construct the Directed Knowledge Graph for immediate inference context.

### Phase 3 & 4: Multi-Perspective Generation Synthesis
Rather than shifting generation parameters linearly, the engine will force the prompt through a multi-model "Gauntlet" representing different psychological and clinical standpoints.

#### [MODIFY] [aibs_reasoning_engine.py](file:///C:/AI-BS/backend/aibs_reasoning_engine.py)
- **Update**: `AIBSSelfProblemSolver.solve_and_refine()` will be heavily expanded to execute the `24/7 Workflow` paradigm:
  - **Clinical Model**: (e.g., `stehouwer_qwen:latest`) forces objective, empirical detachment.
  - **Subjective Model**: (e.g., `stehouwer_dolphin:latest`) generates raw, unfiltered cognitive frameworks.
  - **Synthesis Engine**: (`stehouwer_llm:latest`) takes the output of all perspectives, cross-references it against the Knowledge Graph, and outputs a unified, unbiased multidimensional response.

## Verification Plan
### Automated Tests
- `python -m spacy download en_core_web_trf` (Backend Virtual Environment)
- Run a custom test script `test_nlp_expansion.py` to pass an emotionally chaotic sentence into the `AIBSHybridNLPParser` and verify the output graph is strictly flattened into Root/Predicate JSON.

### Manual Verification
- We will submit a highly abstract, narrative-driven prompt into the frontend.
- You will verify that the response synthesized by the `stehouwer_llm` distinctly highlights the clinical, objective, and subjective breakdowns of the concept, proving the multi-model Gauntlet was triggered.
