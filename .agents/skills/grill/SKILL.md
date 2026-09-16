---
name: grill
description: Architectural Grill (/grill) - Stress-tests incoming mission proposals before updating task.md or modifying code. Front-loads codebase exploration, interrogates edge cases across 4 architectural branches, and pairs every question with an opinionated recommended decision.
---

# AI-BS SKILL: Architectural Grill (/grill)

## Objective
Stress-test incoming mission proposals before updating `task.md` or modifying code. Identify missing specifications, edge cases, and architectural friction between Stage 1 (Intent Parsing) and Stage 2 (Planning & Artifact Generation).

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

### 1. Workspace Exploration First (Silent Self-Answering)
Before generating or asking any question, inspect the local repository (`C:\AI-BS`), SQLite schemas, active configurations, and environment variables. If a technical answer already exists in active code or database tables, resolve it silently and cite the verified context rather than querying the operator.

### 2. Sequential Decision-Tree Traversal
Walk sequentially down each architectural branch (never overwhelm the operator; ask 1 to 2 high-impact targeted questions at a time):
1. **Branch 1: Data Schemas & State Persistence**
   - Table schema definitions, primary keys, indexing on query paths.
   - Write frequencies, journal modes (`PRAGMA journal_mode=WAL;`), batch flushes.
   - Storage limits, bloat prevention, and rolling retention/prune policies.
2. **Branch 2: Concurrency, Locking & Resource Limits**
   - Thread contention, SQLite busy timeouts, asynchronous event loops.
   - GPU VRAM consumption (RTX 4090 24GB allocation, JIT unload vs persistent).
   - CPU thread pools, background daemon auto-recovery, and process supervision.
3. **Branch 3: Error Handling, Rollbacks & Boundary Recovery**
   - Pre-mutation automated backups (`.bak` files).
   - Circuit breakers (halt on 2 consecutive failures).
   - Crash restart policies, orphan cleanup, and transaction rollbacks.
4. **Branch 4: Security, Network Policies & API Limits**
   - 18-Port collision matrix compliance (never rebind static sockets).
   - Strict Zero-Cost Mandate (100% local/free; no paid external API billing).
   - Zero-Mock Real Money Rule (no simulated dollar amounts or fake trades).
   - Stehouwer safety guardrails (S1, S3, S4 locked).

### 3. Opinionated Recommended Answer Mandate
For **EVERY** question asked, formulate a concrete, authoritative, opinionated recommendation tailored to the AI-BS ecosystem. The operator must always be able to accept with a single keystroke (`"yes"`, `"agree"`, `"proceed"`) or override only where they wish to customize.

### 4. Exit Conditions
The grill session terminates when:
- All decision branches are resolved, OR
- The operator replies `"yes"`, `"agree"`, `"proceed"`, OR
- The operator issues `/build` or clicks `[🚀 Build Spec]`.

### 5. Final Deliverable: `mission_spec.md`
Upon session conclusion, write the locked specifications and architectural decisions into `mission_spec.md` (or `spec.md`) and transition directly into Stage 2 (Planning & Artifact Generation: `task.md` / `implementation_plan.md`) and Stage 3 (Autonomous Tool Execution Loop).

## Example Interaction in AI-BS

**Operator:**
`/grill Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry.`

**AI-BS Agent:**
```markdown
🔥 **Architectural Grill Session Initiated**
**Mission Proposal:** *Add a persistent SQLite event-logging daemon for Pearl mining stratum telemetry.*

📦 **Codebase Context Verified:**
- Checked `aibs_media_processor.py` and local mining watcher configs in `miners/`.
- Discovered existing SQLite telemetry tables with unindexed timestamps.
- Target DB: `C:\AI-BS\backend\aibs_master.db` (WAL mode enabled).

---

### ❓ Question 1 (Write Frequency & Lock Contention)
If stratum telemetry logs every 250ms, direct synchronous disk writes will lock SQLite during peak hash bursts.
👉 **Recommended Decision:** Implement an in-memory queue (`queue.Queue` or `asyncio.Queue`) flushing batches every 5 seconds or 50 entries using WAL mode (`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`).

### ❓ Question 2 (Retention Policy)
High-frequency telemetry will bloat SQLite past 2GB within weeks.
👉 **Recommended Decision:** Add an automatic rolling prune trigger maintaining a 7-day window (`DELETE FROM telemetry WHERE timestamp < strftime('%s', 'now', '-7 days')`).

---
💡 *Reply **"yes"** to accept both recommendations, or specify adjustments. You can also issue `/build` to immediately lock `mission_spec.md` and start autonomous execution.*
```
