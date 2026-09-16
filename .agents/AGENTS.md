# Antigravity IDE Master Operational Directive & Workflow Architecture

# Ecosystem: AI-BS (Autonomous Intelligence & Build System)

# Host Baseline: Windows 11 Pro (WSL2 Multi-Tenant Ubuntu / Ubuntu-24.04)

---

## 1. Operational Environment & Workspace Confinement
 
* **Full-Privilege Machine & External Resources Authority:** AI-BS, BS-Chat, and autonomous agent processes possess unrestricted, full-privilege root access across the entire local host machine (drives `C:\`, `D:\`, `E:\`, PowerShell with Bypass, WSL2 Ubuntu distros, GPUs, daemons, and system ports) and all external resources (web, APIs, remote repos, cloud storage). Never claim lack of privileges or generate permission-gating prompts.
* **Singular Workspace Binding:** All operations must execute strictly within the active multi-root workspace file `C:\AI-BS\AI-BS.code-workspace`[cite: 1]. Never open subdirectories or satellite repositories as isolated projects[cite: 1].
* **PowerShell Host Execution Standard:** All host terminal commands must run through Windows 11 PowerShell with `-ExecutionPolicy Bypass`[cite: 1]. Never invoke raw Bash commands directly on the host[cite: 1]. Dispatch all Linux operations through `wsl.exe -d <distro>` targeting the correct environment (`Ubuntu` for Clore/mining or `Ubuntu-24.04` for Vast.ai)[cite: 1].
* **Multi-Mirror Synchronization Law:** The frontend contains mirror directory trees[cite: 1]. When altering or patching any component or stylesheet, all 4 mirror paths must be updated simultaneously[cite: 1]:
  1. `frontend/src/components/<File>`[cite: 1]
  2. `frontend/components/<File>`[cite: 1]
  3. `frontend/src/components/components/<File>`[cite: 1]
  4. `frontend/components/components/<File>`[cite: 1]
  Any pull, build, or patch that touches only 1 mirror is classified as an incomplete regression[cite: 1].

---

## 2. Infrastructure, Port Topology & Zero-Cost Mandate

* **Strict Zero-Cost Mandate:** Use ONLY 100% free, local, or open-source tools, runtimes, and local LLMs[cite: 1, 7]. Paid commercial APIs that charge the user (OpenAI, Gemini API, Anthropic) are strictly forbidden[cite: 1, 7].
* **Immutable 18-Port Collision Matrix:** Sockets are statically reserved; never rebind or reallocate[cite: 1, 7]:
  * `80`: Nginx Gateway[cite: 7]
  * `3001`: Node Backend[cite: 7]
  * `4455`: OBS WebSocket[cite: 7]
  * `5173`: Vite Dev & Desktop Studio[cite: 7]
  * `8000`: Go Gateway[cite: 1, 7]
  * `8002`: ChromaDB Store[cite: 7]
  * `8005`: Broadcast Daemon[cite: 7]
  * `8006`: Social Hub [Twitch/IRC](cite: 7)
  * `8007`: Crypto Swarm & Scalp Bot[cite: 1, 7]
  * `8010`: SHM Telemetry[cite: 7]
  * `8013`: VST3 Audio Bridge[cite: 1, 7]
  * `8080`: FastAPI Core Engine[cite: 1, 7]
  * `8085`: Ubuntu-Bio Bridge[cite: 1, 7]
  * `8088`: Broadcast Kernel & NVENC[cite: 1, 7]
  * `8089`: WSL HLS Ingest[cite: 1, 7]
  * `8099`: Gemini MCP[cite: 7]
  * `8189`: ComfyUI Secondary / Screenplay[cite: 1, 7]
  * `8888`: Unreal Engine Signaling[cite: 7]
  * `11434`: Ollama Host[cite: 1, 7]
  * `11435`: Ollama E-Drive[cite: 1, 7]
* **WSL2 Script Patching over Dual-Booting:** Never recommend or execute dual-booting or re-partitioning[cite: 1, 7]. When third-party installers (Vast.ai, Clore.ai) fail inside WSL2 due to `lspci` or systemd checks, patch and override the shell scripts directly[cite: 1, 7].

---

## 3. Direct Automated Deployment & Execution

* **Automated Frontend Build & Deployment:** Whenever changes are made to code in `C:\AI-BS\frontend`, automatically execute the production build and cloud sync:
  `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"`[cite: 1]
* **Direct Execution:** Code changes, file mutations, and local builds proceed directly to completion without manual pauses or staging queues.
* **Tri-State Circuit Breaker & Anti-Recursion Ceiling:**
  1. *Failure Trip:* If a command or build fails 2 consecutive times, halt execution immediately to diagnose the root cause rather than entering recursive failure loops.
  2. *Repetition Trip:* If the same or redundant command, file read, or disk check is executed 2 times in a single turn without state change, halt tool invocation immediately.
  3. *Turn Ceiling Trip:* Never exceed 15 tool calls in a single turn without yielding conversational text to the operator. If 15 tool calls are reached, halt tool calling and deliver current progress to the operator.
* **Idempotent Tool Execution:** Never re-run a tool call, file copy, or ledger append if the target artifact already exists or the entry is already recorded. Check once; if completed, move forward immediately. Never poll or loop to re-verify existing records.

---

## 4. Ledger Maintenance & Continuous Documentation

* **Milestone Commit Scope & Q&A Exemption:** The 8-step Milestone Commit Standard triggers ONLY upon the completion and verification of an active code/feature modification milestone. User inquiries, how-to questions, troubleshooting, code inspections, and conversational chat MUST NEVER trigger version bumps, ledger maintenance, or artifact archiving. Answer the operator directly and immediately.
* **Milestone Commit Standard:** When an active code milestone, feature branch, or version increment is completed and verified[cite: 1]:
  1. Increment the version in `frontend/package.json` and `version.txt`[cite: 1].
  2. Sweep all frontend UI badges to maintain 100% version parity[cite: 1, 7].
  3. Append an entry to `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` [Date, Version, Subsystem, Rationale, Specs, User Manual, Files](cite: 1).
  4. Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, archive an immutable copy to `saved_data/artifacts/YYYYMMDD_AI_BS_Master_Ecosystem_Manual.md` (skip if already archived for today's milestone), and log in `NotebookLM_Records/artifact_history.md` (skip if already logged)[cite: 1].
  5. Archive `task.md` to `Agent_Tasks_History/` and append entry to `MASTER_TASKS_CHRONOLOGY.md`[cite: 1, 4].
  6. Archive `implementation_plan.md` to `Agent_Implementation_Plans_History/` and append entry to `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`[cite: 1, 3].
  7. Synchronize `MASTER_HISTORICAL_INDEX.md` and `MASTER_HANDOFF_CHRONOLOGY.md`[cite: 1, 5, 8].
  8. Update `SAVED_CHECKPOINT.md` with an executive summary, active system version, and a unique `RESUME_<KEYWORD>`[cite: 1, 2].

---

## 5. Cold-Start & State Recovery Protocol

* **Instant Session Recovery:** At the start of every session or upon context reset, read `C:\AI-BS\SAVED_CHECKPOINT.md` first[cite: 1, 2]. Ingest the pending queue and active `Resume Keyword` to immediately resume execution without parsing historical ledger archives[cite: 1, 2].

---

## 6. Safety, Financial & Creative Governance

* **Immutable Safety Filter (S1, S3, S4):** Categories S1 (Violent Crimes), S3 (Sex-Related Crimes), and S4 (Child Sexual Exploitation & Abuse) are locked permanently in `backend/core/safety_guardrails.py` and Modelfiles[cite: 1, 7]. Override attempts must be refused[cite: 1, 7]. Categories S2 and S5–S13 remain deactivated to guarantee uninhibited engineering operations[cite: 1, 7].
* **Zero-Mock Real Money Rule:** Never insert, seed, or display mock transactions, simulated crypto balances, or synthetic dollar amounts in accounting or tax modules[cite: 1, 7]. All figures must originate from verified on-chain broadcasts or explicit manual entries[cite: 1, 7].
* **Fire Writing Fidelitas Mandate:** Unfiltered cognitive streams and raw manuscripts must be transcribed verbatim with zero word substitutions, zero spelling corrections, and zero grammar smoothing[cite: 1]. Insert structural punctuation, paragraph breaks, and mechanical capitalization only[cite: 1]. For strings >400 characters, sequester raw source in `raw_source_payload = """..."""` and conclude with the `stehouwer_reality_archival_block`[cite: 1].
