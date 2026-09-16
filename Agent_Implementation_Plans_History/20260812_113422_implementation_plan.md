# Scaffold 25-Stage Engine Matrix (Phases I-VI)

The goal of this architectural upgrade is to replace the current flat LLM orchestration model in `bullshit_orchestrator.py` with a rigorous, 6-phase algorithmic routing matrix. This will dynamically decouple prompt complexity, intelligently routing tasks across local APIs, the Code_Debugger swarm, and Polyglot pipelines while preventing system lock-ups.

## User Review Required

> [!IMPORTANT]  
> Please review the 6-Phase architecture below. Confirm if you want Phase II (Context Injection) to strictly query the local `ChromaDB` instances, or if it should also fetch heuristics from the `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.

## Open Questions

1. **Routing Thresholds:** What determines if a prompt bypasses the 25-Stage Matrix and goes straight to a monolithic Swarm Agent? (e.g., character count, specific keywords, or a separate classifier LLM call?)
2. **Phase IV Execution Mode:** Should Phase IV parallelize independent nodes dynamically (using `asyncio.gather`), or execute the topological sort strictly sequentially to guarantee filesystem state consistency?

## Proposed Changes

### Backend Orchestrator

#### [MODIFY] [bullshit_orchestrator.py](file:///C:/AI-BS/backend/bullshit_orchestrator.py)
Refactor the `StageEngine` class to explicitly implement and log the following strict algorithmic phases:

* **Phase I: Intent & Complexity Analysis:** Determine execution scope (Monolithic vs. Matrix).
* **Phase II: Context & Heuristic Injection:** Extract related ambient memories and previous Code_Debugger heuristics from `ChromaDB`.
* **Phase III: 25-Stage Decomposition:** Generate the DAG structural nodes (up to 25 stages).
* **Phase IV: Polyglot Execution Routing:** Route nodes via `execute_polyglot_command` using strict dependency resolution. Map failures dynamically to `Code_Debugger`.
* **Phase V: Synthesis & Assembly:** Aggregate outputs and commit final state vectors.
* **Phase VI: Telemetry & Commitment:** Broadcast to the Aero-Agri frontend telemetry endpoints and commit the successful sequence as a new heuristic in `ChromaDB`.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
* Map the `/stage-engine/orchestrate` endpoint to hook directly into the Phase I initiation protocol, streaming real-time status updates back to the client UI.

## Verification Plan

### Automated Tests
- Trigger a mock complex prompt via `/stage-engine/orchestrate`.
- Validate that the execution logs correctly flag `[PHASE I]`, `[PHASE II]`, etc., sequentially.

### Manual Verification
- Deploy the backend and trigger a complex request from the UI Command Center. Verify that the telemetry accurately reflects active background threads and successful heuristic injection.
