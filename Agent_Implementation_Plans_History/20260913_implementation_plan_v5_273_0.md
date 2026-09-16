# Implementation Plan: Production-Grade Autonomous Developer Workbench (v5.273.0)

Elevation of AI-BS Chat into a production-grade, autonomous developer workbench across orchestrator commands, validation loops, hardware observability, and persistent state management.

---

## User Review Required

> [!IMPORTANT]
> **Dual-Failure Terminal Circuit Breaker:**
> All host terminal and PowerShell commands executed via `mission_control_engine` track exit codes and error signatures. If a command fails twice consecutively with the same error signature, execution immediately halts, outputs the exact stack trace, and requests operator intervention instead of thrashing disk.

> [!NOTE]
> **Multi-Mirror Byte Parity Standard (Rule 1):**
> Enforced by `verify-mirror-parity.ps1` and recursive `sync_mirrors.py`. All 424 files across the 4 mirror paths maintain 100% SHA-256 byte parity before building and deploying.

---

## Proposed Architectural Changes

### 1. Specialized Operational Modes (Slash Commands)
- `C:\AI-BS\skills\SKILL_AUDIT.md`: Pre-flight static analysis, AST validation (`py_compile`), TypeScript linting (`tsc --noEmit`), regex credential scanning, and mirror integrity.
- `C:\AI-BS\skills\SKILL_TEST_FIRST.md`: Autonomous TDD red-green loop enforcing failing baseline test fixture (`NotImplementedError`), minimal functional code, 100% green verification, and `.bak` staging.
- `C:\AI-BS\skills\registry.json`: Registry manifest enabling on-demand dynamic ingestion of skills into LLM working memory.
- `.agents/skills/audit/SKILL.md` & `.agents/skills/test-first/SKILL.md`: Discoverable agent skill definitions.

### 2. Execution Resilience & Guardrails
- `backend/core/mission_control_engine.py`:
  - `execute_terminal_with_circuit_breaker(command, ...)`: Dual-failure circuit breaker.
  - `create_surgical_backup(file_path, task_id)`: Timestamped `.bak` copies in `.aibs_backups/`.
  - `rollback(target)`: Restores backups by ID or filename with pre-rollback snapshot protection.
  - `generate_diff_review()`: Formats visual patch chunks with rollback hashes.
  - `create_snapshot(label)`: Writes atomic Git commit and state dump to `SAVED_CHECKPOINT.md`.

### 3. Native Hardware Observability & Process Conflict Sentinel
- `backend/core/mission_control_engine.py`:
  - `check_hardware_safety()`: Probes NVIDIA GeForce RTX 4090 GPU thermals (<83°C), power draw, and VRAM (<95%) via `nvidia-smi`.
  - `probe_port_conflict(port)`: Probes targeted ports against the 18-port collision matrix and active sockets, providing automated ephemeral fallback ports.

### 4. Backend REST Endpoints & Executive Bus Integration
- `backend/AI_BS_Backend.py`:
  - Mounted `/api/mission/audit`, `/test-first`, `/diff-review`, `/snapshot`, `/rollback`, `/hardware-health`, `/port-probe/{port}`, `/skills`, `/backups` on `mission_router`.
  - Bound command types `audit`, `test_first`, `diff_review`, `snapshot`, `rollback`, `hardware_health`, `port_probe` into `/api/executive/run`.
- `backend/core/hybrid_reasoning_engine.py`:
  - Added intent recognition and streaming response generators for all operational modes.

### 5. Frontend BS-Chat Integration & Mirror Parity
- `frontend/src/components/ChatTab.jsx`:
  - Registered `/audit`, `/test-first`, `/diff-review`, `/snapshot`, `/rollback`, `/hardware`, `/port-probe` in `SLASH_COMMANDS`.
  - Added command interceptors and fetch handlers in `handleSendMessage`.
  - Added 5 quick starter cards in `starterCards`.
  - Restored `OperationsAuditHubTab.jsx` across all 4 mirror trees.
  - Verified 100% SHA-256 byte parity across all 424 files.

### 6. Automated Production Build & Cloud Deployment
- Version incremented to `v5.273.0` across manifests, service workers, and UI badges.
- Production Vite bundle compiled in 27.07s.
- Deployed live to Firebase Hosting: `https://ai-bs-dashboard.web.app`.

---

## Verification Plan

### Automated Verification
- `backend/scratch/test_workbench.py`: Passed all 8 tests:
  1. Hardware Clamping Sentinel (RTX 4090 safe, 47°C, 22.2% VRAM)
  2. Port Collision Sentinel (Port 8080 collision detected, fallback 8180)
  3. Dynamic Skill Ingestion (/audit -> SKILL_AUDIT.md)
  4. Autonomous TDD Loop (Red verified -> Green verified, 133ms)
  5. Pre-Flight AST & Security Audit (Status PASS, 139 files, AST clean, Secret clean, Mirror clean)
  6. Visual Patch Review (Status success, RollbackHash generated)
  7. Terminal Circuit Breaker (Tripped on 2x consecutive failure)
  8. Surgical Backup & Rollback (File restored to exact pre-mutation state)
- `verify-mirror-parity.ps1`: 100% SHA-256 parity confirmed across all 424 files in 4 mirrors.
- `npm run build`: Vite compiled cleanly in 27.07s.
- `firebase deploy`: Successfully deployed to `https://ai-bs-dashboard.web.app`.
