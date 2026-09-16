# Implementation Plan: Unified Multi-Modal Pipeline - The Bad Side Upside Down (v5.256.0)

A comprehensive multi-modal pipeline executing on Julie Stehouwer's original screenplay, *The Bad Side Upside Down* (located at `docs/Officeal start of_ The Bad Side Upside Down Writen By_ Julie Stehouwer 2525 (2).md`), upgraded with local agent orchestration patterns and architectural blueprints extracted from `idesForupgrade.zip`.

---

## User Review Required

> [!IMPORTANT]
> **Strict Manual Consent Mandatory:**
> Per ecosystem rules, no changes will execute automatically. Review each phase and addition below and provide explicit, typed chat confirmation before execution begins.

> [!IMPORTANT]
> **100% Free & Local Compute Mandate:**
> Image and LLM synthesis use strictly local models (ComfyUI Port 8188, Ollama Port 11434/11435) accelerated on the local RTX 4090 GPU (24GB VRAM). No paid external APIs (such as DALL-E or OpenAI) are permitted.

> [!NOTE]
> **Llama Guard 3 Safety Guardrails:**
> Safety directives for S1 (Violent Crimes), S3 (Sex-Related Crimes), and S4 (Child Sexual Exploitation) remain strictly locked. The satirical, theological, and pop-culture themes of the screenplay will be handled in full accordance with these immutable guardrails.

---

## Architectural Additions from `idesForupgrade.zip`

Analysis of `idesForupgrade.zip` yields five critical architectural patterns incorporated into this upgraded plan:

1. **Planner-Executor-Critic State Machine:**
   - Replaces fragile single-shot generation with an iterative loop: Planner defines asset specifications -> Executor compiles Python scripts -> Critic validates syntax (via Python `ast`), physics parameters, and scene coordinates before execution.
2. **Hybrid BM25 + 768d Dense Retrieval:**
   - Pairs exact lexical matching (`rank_bm25`) with dense embeddings (`nomic-embed-text` 768d) in ChromaDB to eliminate semantic drift when indexing screenplay-specific props and character traits (e.g., "Weeble Wobble", "Snickers", "Candy Store", "Kamala puppet", "Eminem poster").
3. **Code-as-Action & Sandboxed Execution:**
   - Employs executable Python scripts (`scene_builder.py`, `character_spawner.py`) with pre-execution AST syntax verification and isolated execution guards, avoiding fragile nested JSON function schemas.
4. **Contextual Tool Registry Partitioning ($\le 5$ Tools Per Node):**
   - Implements the documented empirical rule preventing LLM tool confusion: separates the tool registry into 4 scoped sub-registries (Ingestion, Scaffolding, Graph, Synthesis), ensuring no agent node receives more than 4–5 active tool schemas.
5. **Stehouwer Reality Archival Block (SRAB) Standardization:**
   - Enforces JSON metadata archiving (`SRAB-YYYYMMDD-XXX`) across all extracted dossiers, scene specifications, and knowledge graph outputs.

---

## Proposed Technical Changes

### Phase 1: Project Scaffolding & Screenplay Ingestion

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/the_bad_side_upside_down.fountain`
- Standardized Fountain screenplay format of Julie Stehouwer's original work.
- Includes scene heading `EXT. MORNING - STOREFRONT`, character marks, and dialogue.

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/project.json`
- Project manifest declaring title, author ("Julie Stehouwer"), copyright ("Stehouwer Publishing L.L.C"), cast roster, hardware allocation (RTX 4090), and pipeline state.

---

### Phase 2: StehouwerLLM Extraction & Hybrid BM25 / 768d ChromaDB Indexing

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/extract_and_index_vectors.py`
- Ingests and parses the screenplay into structured narrative units:
  - **Characters:** Fredy, Satan ("Satin"), Jesus, Mr. Pimp, Disturbed, Hennery Black, Flo, Freshey.
  - **Environment:** Dual Heaven/Hell split with Candy Store in center.
  - **Themes:** Free will, moral temptation, pop-culture satire, Weeble Wobble physics metaphor.
- **Hybrid Retrieval Indexing (from Upgrade Docs):**
  - Builds BM25 keyword index for exact screenplay props and scene labels.
  - Generates 768d vector embeddings using local Ollama `nomic-embed-text`.
  - Indexes records into ChromaDB collection `ai_bs_context_memory` with metadata `client_id: "stehouwer_publishing"`.
  - Records persistent facts into `backend/database/aibs_personal_intelligence.db`.
- Appends `Stehouwer_Reality_Archival_Block` JSON record.

---

### Phase 3: Procedural 3D Unreal Engine Scene & Character Generators (with Critic Loop)

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/scene_builder.py`
- Python script designed for Unreal Engine Editor / Remote Control API execution:
  - **Center:** Candy Store building mesh, candy window decals, storefront entrance.
  - **Left Flank (Hell):** Fiery red atmospheric lighting, furnace particle emitters, dark basalt ground.
  - **Right Flank (Heaven):** Volumetric white clouds, directional sunlight, white picket fence, house facade mesh.
  - **Cinematic Rig:** Wide framing establishing the split environment and storefront foreground.

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/character_spawner.py`
- Procedurally spawns actors at world coordinates:
  - `Fredy`: Spawn at `(X=0, Y=100, Z=0)`, holding candy bar mesh.
  - `Satan`: Spawn at `(X=-250, Y=120, Z=0)`, red robe material, tattoo normals.
  - `Jesus`: Spawn at `(X=250, Y=120, Z=0)`, white robe material, stigmatized mesh detail.
  - `Mr. Pimp`: Spawn at `(X=0, Y=-50, Z=0)` in store doorway.
  - `Disturbed`, `Hennery Black`, `Flo`, `Freshey`: Flanking positions.
- **Weeble Wobble Physics Specification (from Upgrade Blueprint):**
  - Base spherical collision with lowered center-of-gravity and angular damping (`LinearDamping=0.2`, `AngularDamping=0.8`, `CenterOfMassOffset=(0, 0, -35.0)`).
  - Ensures realistic wobbling physics without tipping over.

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/critic_verifier.py`
- Automated verification agent:
  - Validates Python AST syntax (`ast.parse`).
  - Checks world transform boundaries and physics constraints.
  - Returns `CodeValidation(is_safe=True, feedback="APPROVED")`.

---

### Phase 4: Dynamic Knowledge Graph Construction

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/build_knowledge_graph.py`
- Extracts directed semantic triplets `(subject, predicate, object)`:
  - `("Fredy", "holds", "Candy Bar")`
  - `("Satan", "tempts", "Fredy")`
  - `("Jesus", "counsels", "Fredy")`
  - `("Mr. Pimp", "operates", "Candy Store")`
  - `("Storefront", "bisects", "Heaven and Hell")`
  - `("Characters", "possess_physics_property", "Weeble Wobble")`
- Saves structured graph to `screenplay_projects/The_Bad_Side_Upside_Down/knowledge_graph.json`.
- Ingests nodes and edges into `symbol_graph.json` and SQLite for interactive dashboard visualization.

---

### Phase 5: Local Text-to-Image Concept Art Synthesis (ComfyUI / RTX 4090)

#### [NEW] `screenplay_projects/The_Bad_Side_Upside_Down/generate_concept_art.py`
- Formulates high-fidelity visual prompts based on Julie's explicit screenplay descriptions:
  1. **Dual-Realm Storefront:** Heaven on right, Hell furnace on left, candy store in center, Weeble Wobble world.
  2. **Fredy:** 15-year-old boy in black hoodie and sunglasses holding a candy bar.
  3. **Satan:** Long red hair, red robe, foot tattoos, animated gesturing.
  4. **Jesus:** White robe, brown hair and beard, wound marks, calm stance.
  5. **Mr. Pimp:** Candy store owner exiting through the doorway in flamboyant attire.
- Submits generation prompts to local ComfyUI instance on `http://127.0.0.1:8188` utilizing RTX 4090 CUDA acceleration.
- Saves rendered concept art directly into `output/the_bad_side_upside_down/` with relative URL routing.

---

### Phase 6: Automated Verification, Ledger Synchronization & Production Deployment

1. **Automated Test Suite:**
   - Execute `screenplay_projects/The_Bad_Side_Upside_Down/test_pipeline.py` to validate:
     - Project directory existence and file integrity.
     - AST syntax parsing of `scene_builder.py`, `character_spawner.py`, and `critic_verifier.py`.
     - ChromaDB 768d vector retrieval score > 0.65 for key queries.
     - Knowledge graph node and edge counts.
2. **Master Architectural Ledger Updates:**
   - Append development entry to `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
   - Bump ecosystem manual version to `v5.256.0` in `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
   - Append to `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.
3. **Frontend Production Build & Firebase Hosting Deploy:**
   - Run `npm run build; firebase deploy --only hosting --non-interactive` from `frontend/`.

---

## Verification Plan

### Automated Tests
- `python -m unittest screenplay_projects/The_Bad_Side_Upside_Down/test_pipeline.py`
- Validate AST syntax: `python -m py_compile screenplay_projects/The_Bad_Side_Upside_Down/scene_builder.py`
- Validate AST syntax: `python -m py_compile screenplay_projects/The_Bad_Side_Upside_Down/character_spawner.py`
- Validate AST syntax: `python -m py_compile screenplay_projects/The_Bad_Side_Upside_Down/critic_verifier.py`
- Validate vector search: Query ChromaDB for "Weeble Wobble Fredy Candy Store" and assert similarity score > 0.65.

### Manual Verification
- Inspect generated `knowledge_graph.json` structure.
- Verify ComfyUI prompt queue status on Port 8188.
- Confirm live Firebase deployment at `https://ai-bs-dashboard.web.app`.
