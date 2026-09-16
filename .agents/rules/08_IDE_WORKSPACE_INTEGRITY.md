# IDE Workspace Integrity & Navigation Rule

**Status:** ACTIVE & MANDATORY DIRECTIVE  
**Classification:** IDE Configuration & Multi-Root Management  

## Directives
1. **Ecosystem Exclusivity:** All projects and tasks are exclusively related to the AI-BS ecosystem.
2. **Workspace Navigation:** Do not allow or recommend opening individual folders (like `C:\AI-BS` or subdirectories) directly. Stop clicking the standalone "AI-BS" folder in your recent list.
3. **Required IDE State:** The user must exclusively use **File > Open Workspace from File** and select `C:\AI-BS\AI-BS.code-workspace`.
4. **Multi-Root Subsystems:** Maintain all active subsystem roots in `AI-BS.code-workspace` (`frontend`, `backend`, `go-core`, `trainer_frontend`, `mobile-app`, `game_trainer`, `screenplay_projects`, `docs`, `Stehouwer Publishing Server`, `Prestige Mobile Wash App`).
5. **Exclusion Guardrails:** Maintain aggressive `files.exclude`, `search.exclude`, and `files.watcherExclude` rules on massive binary dumps (`symbol_graph.json`, `py_health_audit.json`, `.ollama`, tensor swap caches) to prevent IDE thrashing and memory exhaustion.
