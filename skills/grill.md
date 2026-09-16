# AI-BS SKILL: Architectural Grill (/grill)

## Objective
Stress-test incoming mission proposals before updating task.md or modifying code. Identify missing specifications, edge cases, and architectural friction between Stage 1 (Intent Parsing) and Stage 2 (Planning & Artifact Generation).

```
┌──────────────────────────────────────────────┐
│           OPERATOR MISSION PROMPT            │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ 1. INTENT PARSING & SKILL ACTIVATION         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ [OPTIONAL] /grill SESSION (Stress-Test Loop) │  <-- Front-loads discovery
│  • Inspect workspace & DB schemas first      │
│  • Interrogate architectural edge cases      │
│  • Propose default decisions (1-click ack)   │
│  • Output locked requirements into spec.md   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│ 2. PLANNING (task.md / implementation_plan)   │
└──────────────────────────────────────────────┘
```

## Execution Rules
1. **Workspace Priority**: Inspect existing files, schemas, and git history before asking questions. If a question can be answered from local context, resolve it silently.
2. **Sequential Branches**: Do not overwhelm the operator. Ask 1 to 2 targeted questions at a time, moving sequentially through:
   - Data structures & state mutation
   - Concurrency & hardware resource limits (VRAM, locks, processes)
   - Failure recovery & rollback strategies
   - Security, network policies & API limits
3. **Recommended Answer Mandate**: For EVERY question, formulate a concrete, opinionated recommendation based on AI-BS standards. The operator must be able to reply "yes" to accept.
4. **Exit Condition**: Terminate the grilling session only when all structural ambiguities are resolved, or when the operator issues `/build` or `proceed`.
5. **Final Deliverable**: Write the agreed decisions into `mission_spec.md` and transition directly into Stage 2 (Planning & Artifact Generation).
