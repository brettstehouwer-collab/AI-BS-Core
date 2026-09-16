# Stehouwer LLM NLP Expansion Tasks

- `[x]` **1. Environment Setup**
  - Install `spacy` in the backend Python virtual environment.
  - Download the transformer-based English language model (`en_core_web_trf`).
- `[x]` **2. Core Reasoning Engine Expansion (`aibs_reasoning_engine.py`)**
  - Implement `AIBSHybridNLPParser` class using spaCy for rigid tokenization and dependency parsing.
  - Update `AIBSGraphReasoningEngine` to construct graphs natively from the new spaCy parsed objects.
  - Upgrade `AIBSSelfProblemSolver.solve_and_refine()` to execute the 24/7 multi-perspective gauntlet (clinical, subjective, objective synthesis).
- `[x]` **3. Vector Persistence (`chroma_storage.py`)**
  - Update embedding logic to attach the spaCy Dependency Parse and Named Entities as strictly structured ChromaDB metadata.
- `[x]` **4. Verification**
  - Create and run `test_nlp_expansion.py` to validate the flattened syntactic output and the multi-perspective generation.
