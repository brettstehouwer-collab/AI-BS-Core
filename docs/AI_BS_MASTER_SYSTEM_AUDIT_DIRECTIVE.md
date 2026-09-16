# AI-BS Master System Audit Directive
**Version:** 1.0.0
**Target Scope:** `C:\AI-BS` (All folders, subfolders, files, and executable code)

## Executive Summary
This directive mandates a comprehensive, line-by-line audit and functional verification of the entire AI-BS ecosystem. The objective is to guarantee that every component, script, and documentation file functions as intended, aligns with the master architectural ledgers, and does not contain conflicting or obsolete logic. 

## Phase 1: Markdown Knowledge Base Audit
**Priority:** Highest
**Order of Execution:** Chronological (Newest to Oldest)
**Target:** All `.md` files in the AI-BS directory structure.

1. **Discovery & Sorting:** Aggregate all `.md` files and sort by `LastWriteTime` descending.
2. **Review Criteria:**
   - Scan line-by-line for obsolete instructions or deprecated configurations.
   - Cross-check against `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
   - Reconcile any conflicting rules or duplicate entries.
3. **Validation:** Ensure all markdown files accurately reflect the current state of the backend, frontend, and daemon systems.

## Phase 2: Structural Folder & File Scan
**Target:** All directories and non-executable files.
1. **Directory Traversal:** Iterate through every top-level folder and subfolder.
2. **Cleanup:** Identify and flag orphaned files, temporary backups (e.g., `.bak`), and empty directories.
3. **Inventory:** Update the master ledger with any undocumented directories.

## Phase 3: Deep Code & Function Audit (Line-by-Line)
**Target:** Python (`.py`), JavaScript (`.js`/`.jsx`), Batch (`.bat`), Shell (`.sh`), Go (`.go`).
1. **Syntax & Linting:** Pass every script through strict syntax and linting checks.
2. **Logic Verification:** Review each function line-by-line for intended behavior.
3. **Cross-Checking:** Identify duplicate functions across different files (e.g., duplicate database connection logic in backend vs daemons) and consolidate them.

## Phase 4: Functional Testing & Ecosystem Verification
1. **Component Testing:** Run unit tests for isolated functions.
2. **Integration Testing:** Start the `Launch_AI_BS.bat` sequence and verify IPC bridges, database connections (SQLite/ChromaDB), and API endpoints.
3. **Frontend Verification:** Ensure the React frontend correctly routes API calls and media assets.

## Phase 5: Reporting & Master Ledger Synchronization
1. **Documentation Updates:** Immediately log all additions, reductions, and architectural modifications in `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
2. **Save Point:** Generate a `SAVED_CHECKPOINT.md` detailing the completed audit and providing a resumption keyword for future work.
