# Heuristics & Learned System Rules

> **Storage Location:** `C:\AI-BS\Heuristics\learned_rules.md`  
> **Purpose:** Continuous self-learning log for user preferences, execution corrections, and workflow optimizations.

---

## System Directives Summary
- **Native Tools First:** Use built-in IDE/Agent workspace tools (`view_file`, `replace_file_content`, `write_to_file`, `list_dir`, `grep_search`, `browser_subagent`) over shell execution whenever possible.
- **Shell Standard:** Default to `cmd /c` for non-interactive commands. Use elevated PowerShell (`Start-Process powershell -Verb RunAs ...`) for admin tasks.
- **No Auto-Yield 'Y':** Never pipe `y` / `yes` into interactive terminals. Trigger native Proceed / Approve UI prompts for user authorization.
- **Artifact Preservation:** Save all generated artifacts to `C:\AI-BS\saved_data\artifacts\YYYYMMDD_<slug>.<ext>`. Log lineage to `C:\AI-BS\ingest_manifest.json` and `C:\AI-BS\NotebookLM_Records\artifact_history.md`.
- **Chrome Debug Launch:** `C:\Program Files\Google\Chrome\Application\chrome.exe` on `--remote-debugging-port=9222` with profile `C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data`.
- **Web Knowledge Research:** Save structured markdown notes to `C:\AI-BS\AI_BS_Knowledge_Vaults\web_research\`.
- **Master Ledger Maintenance:** Update `C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` for every code edit, design decision, or feature addition across `C:\AI-BS`.
- **`modernc.org/libc` & Platform Architecture Matrix:**
  - **Do NOT edit generated code:** `ccgo_linux_*.go`, `musl_*.go` are read-only. Edit handwritten glue/generator scripts instead.
  - **Path A (Musl/Linux):** `ccgo_linux_*.go`, `musl_*.go`.
  - **Path B (Handwritten/Windows/Non-Linux):** `libc.go`, `libc_unix.go`, `libc_<goos>.go`, `libc_windows*.go`, `pthread.go`, `mem.go`.
  - **External Symbols (`Xfoo`):** Verify whether `capi_*` updates are required.
- **Vite & SHM Gateway Rule:**
  - WebSocket proxy runs on `ws://localhost:8000/ws/shm_telemetry` at 20 Hz (50ms).
  - Frontend components (`SHMTelemetryWidget.jsx`) must handle disconnected/remote states gracefully with fallback banners.
  - Every frontend modification must automatically build (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- **Continuous Master Ecosystem Manual Synchronicity Rule:**
  - Whenever code, backend daemons, IPC bridges, pipelines, or UI components are modified, IMMEDIATELY update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
  - Bump manual version number in metadata block (e.g. `5.0.0` -> `5.1.0`).
  - Persist updated artifact copy to `saved_data/artifacts/YYYYMMDD_AI_BS_Master_Ecosystem_Manual.md`.
  - Log lineage in `NotebookLM_Records/artifact_history.md`, sync `ACTIVE_TASK.md`, update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, and save checkpoint in `SAVED_CHECKPOINT.md`.



