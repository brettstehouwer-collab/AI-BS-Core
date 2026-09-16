# Dictionary Ingestion Plan for Lexicographical Augmentation

The goal of this task is to ingest both the `wordset-dictionary-master` dataset (~177,000 definitions) and the **Moby Thesaurus** (the largest thesaurus in the English language) into the AI-BS ecosystem. This will directly fulfill the **Lexicographical Augmentation** directive by giving the LLM deep access to precise, monosemic definitions, etymological data, and extensive synonym linkages.

## User Review Required

> [!WARNING]  
> Vectorizing 177k entries into ChromaDB using standard embedding models can be computationally heavy and might take a long time to run (up to an hour depending on the embedding function used). 
> 
> **Are you okay with running this ingestion script in the background while we proceed with other tasks, or would you prefer a fast, lightweight ingestion that relies on exact-match SQLite rather than full semantic Vector embeddings?**

## Proposed Changes

### Backend Core

#### [NEW] `dictionary_ingestor.py`
We will create a new Python script in `C:\AI-BS\backend\core\dictionary_ingestor.py` that will:
1. Traverse the `C:\AI-BS\docs\wordset-dictionary-master\data\` directory for dictionary definitions.
2. Download or interface with the `moby` thesaurus package to map massive synonym trees.
3. Merge the Moby synonym linkages with the Wordset definitions for unified context.
4. Connect to the ChromaDB Vector Store on `localhost:8001` (or `8002` if E-Drive is active).
5. Upsert the enhanced definitions in batches of 1,000 into a new collection named `wordset_lexicon`.

#### [MODIFY] `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`
Log the addition of the `wordset_lexicon` ChromaDB collection to the architecture.

## Verification Plan

### Automated Tests
- Run `python C:\AI-BS\backend\core\dictionary_ingestor.py --dry-run` to verify JSON parsing and batch chunking logic without hitting ChromaDB.
- After ingestion, execute a test script to query the `wordset_lexicon` collection for a sample word (e.g. "lindy") and ensure the vector search successfully returns the definition.

### Manual Verification
- We will query the Vector Database to confirm the total document count matches the expected 177,000 entries.
