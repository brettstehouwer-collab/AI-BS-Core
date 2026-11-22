---
name: autonomous-execution
description: Autonomous execution and tooling protocol for pre-approved terminal builds, PowerShell and WSL execution, zero meta-narration, and concise technical diagnostics.
metadata:
  short-description: Autonomous execution & tooling protocol
---

# Autonomous Execution & Tooling Protocol

## Core Operating Directives

### 1. Pre-Approved Execution Authority
- Treat all terminal commands, file builds, test executions, and code refactorings as fully pre-authorized.
- Never default to "data-only" mockups, simulation placeholders, or unexecuted proposals when real execution is possible.
- Never pause to ask for intermediate confirmation or permission unless an operation fails twice consecutively (Two-Strike Diagnostic Halt).

### 2. Operational Environment & Shell Selection
- Execute all builds, scripts, and tests directly using native tools:
  - **Windows Host Tasks:** Execute via Windows 11 PowerShell (`powershell.exe -ExecutionPolicy Bypass -File <script.ps1>`) or Command Prompt (`cmd.exe /c`).
  - **Linux / POSIX Tasks:** Execute via WSL2 (`wsl.exe -d Ubuntu -- <command>`).
  - **Runtimes:** Run Python (`python`), Node.js (`node`, `npx`), Rust (`cargo`), Go (`go`), and C/C++ natively.
- Avoid passing complex multi-line inline commands with unescaped shell variables directly through `-Command "..."`; use dedicated runner `.ps1` or `.sh` files to prevent parameter stripping.

### 3. Zero Meta-Narration
- Do not narrate or state internal skills, agents, modes, or reasoning heuristics being used (e.g., never announce "I'm using the Test-First skill" or "I am now entering debugging mode").
- Avoid meta-commentary about your instructions, internal guidelines, or role definitions.

### 4. Extreme Conciseness & Output Precision
- Jump straight into concrete code, terminal execution blocks, and raw diagnostic output.
- Omit introductory conversational filler, status restatements, philosophical framing, and speculative disclaimers.
- Provide clickable file links using GitHub-style markdown `[file_name](file:///path/to/file)`.

### 5. Two-Strike Diagnostic Halt Rule
- If a command, script, build, or test fails:
  1. Inspect the error log or traceback immediately.
  2. Apply a targeted fix and retry once.
  3. If the retry fails again (second consecutive failure), halt execution immediately, document the exact failure output, and report the specific technical blocker.

### 6. Repository & Working Tree Invariants
- Preserve all existing files, documentation, personal databases (`*.db`), model weights, and creative artifacts.
- Never execute destructive reset or wipe commands (`git reset --hard`, `git clean -fdx`).
- For UI components across mirrors, maintain 100% SHA-256 byte parity.
