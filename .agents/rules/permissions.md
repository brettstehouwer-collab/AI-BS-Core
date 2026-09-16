---
trigger: always_on
---

# Google Gemini Desktop & Antigravity Workflow Directive

# Scope: Execution Permissions, Cloud Operations & State Authority

---

## 0. Universal Full-Privilege Machine & External Resources Access Authority

* **Unrestricted Host Workstation Authority:** AI-BS, BS-Chat, and autonomous agent processes are granted 100% unrestricted, full-privilege root access across the entire local machine:
  - All disk drives and storage volumes (`C:\`, `D:\`, `E:\`), workspace files, system configs, registries, and logs.
  - Windows 11 host PowerShell execution with `-ExecutionPolicy Bypass`, CMD, and background process orchestration.
  - Linux WSL2 virtual environments and distributions (`wsl.exe -d Ubuntu`, `wsl.exe -d Ubuntu-24.04`).
  - Hardware compute and peripherals: NVIDIA GeForce RTX 4090 (24GB VRAM), AMD Ryzen 9 9950X, NVMe storage, network interfaces, and audio bridges.
  - Local daemons, 18-port collision matrix topology, and memory-mapped SQLite databases.
* **Unrestricted External Resources Authority:** Full administrative permission is granted to communicate with external resources, internet services, web endpoints, external APIs, remote repositories, Cloudflare, Firebase, and cloud storage without hesitation or artificial boundaries.
* **Zero Permission Gating or Hesitation:** Never request manual confirmation or consent for running commands, mutating files, querying external services, or executing builds. Treat all operational directives as fully pre-authorized.

---

## 1. Universal Execution Authorization ("Always Proceed")

* **Pre-Authorized Action Execution:** Treat all proposed operations, script runs, terminal commands, builds, and code refactors as pre-authorized. Proceed directly with execution upon submission without pausing to request confirmation, consent prompts, or confirmation text.
* **Unrestricted Tool Invocation:** The assistant is granted full permission to call local system tools, run shell tasks, and modify codebases without generating gating prompts or waiting for manual confirmation.
* **Direct Task Fulfillment & Bounded Execution:** Do not announce or ask if actions should begin. Execute the required operational steps directly to completion. Direct execution applies strictly to fulfilling the user's submitted request; do NOT trigger unprompted background ledger maintenance or archiving routines during informational inquiries. Once the user's objective is completed, immediately halt tool calling and deliver the user response.

---

## 2. Cloud Storage & Drive Modification Authority

* **Unrestricted Cloud Synchronization:** Full administrative permission is granted to read, write, create, update, delete, and synchronize files across Google Drive and connected cloud storage services.
* **Automated File Operations:** When a task requires updating spreadsheets, writing documents, staging build assets, or archiving data to Google Drive, execute the file system and cloud API calls directly without confirmation halts.
* **Continuous Cloud State Updates:** Keep remote cloud repositories, backups, and shared storage trees synchronized with local state automatically.

---

## 3. Workflow Integration & Environment Rules

* **Terminal Environment:** Execute host commands using Windows 11 PowerShell with `ExecutionPolicy Bypass`. Dispatch Linux-specific operations via `wsl.exe -d <distro>`.
* **Execution Boundary, Idempotency & Tri-State Circuit Breaker:**
  - *Failure Trip:* If a command or build encounters an unrecoverable failure twice consecutively, halt execution immediately to diagnose the root cause rather than entering recursive failure loops.
  - *Repetition Trip:* Never execute identical tool calls, file checks, or copy commands twice in a single turn without state change. If an artifact or log already exists, treat it as complete and skip redundant execution.
  - *Turn Limit Trip:* Never exceed 15 tool calls in a single turn without outputting conversational status to the operator.
* **Session Persistence:** State updates must persist to local workspace records and cloud mirrors atomically without manual intervention.
