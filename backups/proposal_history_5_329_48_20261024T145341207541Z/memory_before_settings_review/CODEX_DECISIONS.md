# AI-BS — Codex Architectural Decisions & Rationale (`CODEX_DECISIONS.md`)

This document records durable architectural, security, runtime, and persistence decisions for the AI-BS repository (`C:\AI-BS`). Do not overwrite historical entries; append new decisions as development progresses.

---

## ADR-001: Three-Layer Persistent Engineering Memory & Lifecycle Hook Architecture
- **Date:** 2026-10-24
- **Status:** Active / Verified on Codex `v0.164.0-alpha.11.1` (`windows-x86_64`)
- **Context:** Long-running autonomous development across Phases 1–6 experiences context compaction and session restarts. Relying on conversation history alone risks losing checkpoint paths, hash invariants, runtime PID/flag baselines, and deferred scope boundaries.
- **Decision:**
  1. Maintain durable repository truth across:
     - `AGENTS.md` (and `C:\Users\footb\.codex\AGENTS.md`) — Permanent operational instructions and safety invariants.
     - `docs/CODEX_HANDOFF.md` — Authoritative current engineering state and versioned checkpoint records.
     - `docs/CODEX_JOURNAL.md` — Append-only chronological history of checkpoints, lifecycle hook triggers (`SessionStart`, `PreCompact`, `PostCompact`, `Stop`), test results, and diagnostic halts.
     - `docs/CODEX_DECISIONS.md` — Architectural decisions and rationale.
     - `docs/CODEX_TASKS.md` — Outstanding tasks, dependencies, and acceptance criteria.
  2. Configure native Codex `v0.164.0-alpha.11.1` lifecycle hooks in `C:\Users\footb\.codex\hooks.json` (UTF-8 without BOM) with trusted content hashes in `C:\Users\footb\.codex\config.toml` (`[hooks.state.'...']`) invoking `C:\Users\footb\.codex\scripts\codex_lifecycle_hook.py`.
  3. **Non-Interference Invariant:** Hook scripts read `docs/CODEX_HANDOFF.md`, `docs/AI_BS_Autonomy_Implementation_Plan.md`, `docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md`, and `docs/engineering_ledger/cloud_index.json` strictly in **read-only** mode so they never invalidate an in-flight `before_manifest.json` SHA-256 guard during active checkpoint finalization. Hook checkpoints write atomically to `docs/CODEX_JOURNAL.md`, `docs/CODEX_TASKS.md`, and `C:\AI-BS\backups\codex_hook_checkpoints\`.

---

## ADR-002: Preservation of Originals, Private Stores, Models, and Dirty Working Tree
- **Date:** 2026-10-24
- **Status:** Mandatory Invariant
- **Decision:**
  - Never run `git reset`, `git checkout --`, `git clean`, or destructive deletions on `C:\AI-BS`.
  - Preserve all 866 screenplays + 22 selected creative/project documents (888 total) and their retained backup copies byte-for-byte.
  - Preserve SQLite databases (`data/aibs_vault.db`, `aibs_master.db`, `backend/data/personal_ai_profile.db`), model blobs (`C:\AI-BS\models\ollama`), and `Modelfile*` definitions.
  - Export only sanitized engineering ledger summaries to the private Google Drive ledger file after exact byte-readback verification; never export raw source, candidate proposals, personal rows, credentials, or local directory listings.

---

## ADR-003: Loopback-Only Services & Six Disabled Autonomous/External Flags
- **Date:** 2026-10-24
- **Status:** Mandatory Runtime Gate
- **Decision:**
  - Local services (`127.0.0.1:8080` FastAPI backend, `127.0.0.1:8000` Go gateway, `127.0.0.1:11434` Ollama, `127.0.0.1:5173` Vite frontend) must bind strictly to `127.0.0.1`.
  - Keep all six autonomous/outbound flags explicitly `false` (`AIBS_AUTONOMOUS_SWARM`, `AIBS_BACKGROUND_DAEMONS`, `AIBS_OUTBOUND_PUBLISH`, `AIBS_AUTO_APPLY`, `AIBS_CLOUD_SYNC_DAEMON`, `AIBS_UNATTENDED_EXECUTION`).
  - All candidate code proposals remain `Tests not run / Not applied` (`execution_authorized=false`, `apply_authorized=false`) until isolated execution and review/apply gates are explicitly completed.

---

## ADR-004: Explicit Deferral of Windows VM Isolation Steps & Two-Strike Diagnostic Halt
- **Date:** 2026-10-24
- **Status:** Active User Directive
- **Decision:**
  - Per explicit user instruction, Windows VM / Hyper-V / Sandbox isolation setup and VM retry workarounds are deferred while bounded VM-independent tasks in BS-Chat preparation/planning/proposal workflows proceed.
  - Apply a strict two-strike diagnostic halt after two failed corrective attempts on any unexpected runtime or verification failure, recording the exact failure artifact before changing approach.
