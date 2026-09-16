# Implementation Plan: Chat Host File Read & Write Autonomous System (v5.270.0)

Enable BS-Chat in the AI-BS frontend (`ChatTab.jsx` across all 4 mirror paths) and backend streaming engine (`hybrid_reasoning_engine.py` / `AI_BS_Backend.py`) to read and write files on the host filesystem (`C:\AI-BS`, `D:\`, `E:\`) via direct slash commands (`/read`, `/write`, `/ls`, `/edit`) and natural language prompts.

## Proposed Changes

### Backend Core & Hybrid Reasoning Engine

#### [MODIFY] [hybrid_reasoning_engine.py](file:///C:/AI-BS/backend/core/hybrid_reasoning_engine.py)
- In `detect_tool_intent(prompt)`:
  - Add recognition for `read_host_file` (matching `/read`, `/cat`, `/view`, `/file`, plus natural language "read file X", "what is in file Y", "show me contents of file Z").
  - Add recognition for `write_host_file` (matching `/write`, `/save`, `/create_file`, plus code-block writes and inline writes "write to file X with content Y").
  - Add recognition for `scan_directory_tree` (matching `/ls`, `/dir`, `/tree`, plus "list files in folder X").
- In `stream_stehouwer_hybrid_response(prompt, messages)`:
  - Add handler for `read_host_file`: Execute `ToolRegistry.execute_tool('read_host_file')`, render syntax-highlighted code block with line/size badges. If the prompt contains a follow-up analytical question, feed the file content to `stream_sovereign_response` to synthesize the exact answer.
  - Add handler for `write_host_file`: Execute `ToolRegistry.execute_tool('write_host_file')`, write UTF-8 content, create automatic `.bak` backup, report status badge, byte count, and backup location.
  - Add handler for `scan_directory_tree`: Execute `ToolRegistry.execute_tool('scan_directory_tree')`, render formatted markdown table with file types and sizes.

#### [MODIFY] [dispatcher.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py)
- In `stehouwer_system_prompt`:
  - Add explicit host filesystem grounding:
    "FILE SYSTEM & HOST OPERATIONS DIRECTIVE: You have root read and write access to the host filesystem (C:\AI-BS, D:\, E:\). When the user asks to read, view, check, write, modify, save, or scan files, those operations are fully authorized and directly executed by the local host tools. Never claim you cannot read or write local files."

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- In `/api/chat` non-streaming tool handler:
  - Add handlers for `read_host_file`, `write_host_file`, and `scan_directory_tree` so non-streaming requests also return formatted file previews and synthesis.

---

### Frontend Chat IDE (Rule 1: 4-Mirror Synchronization)

#### [MODIFY] [ChatTab.jsx (4 Mirror Paths)](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx)
- 1. `frontend/src/components/ChatTab.jsx`
- 2. `frontend/components/ChatTab.jsx`
- 3. `frontend/src/components/components/ChatTab.jsx`
- 4. `frontend/components/components/ChatTab.jsx`
- Add command interceptor for `/read`, `/cat`, `/view`, `/file`:
  - Fetch file content via `/api/executive/run` (`command_type: 'file_read'`).
  - Render formatted code block with syntax tag, line count, and byte size.
  - Include option to open directly into `FileEditorDrawer`.
- Add command interceptor for `/write`, `/save`:
  - If content is supplied: call `/api/executive/run` (`command_type: 'file_write'`), render success badge and backup notice.
  - If no content is supplied: open blank `FileEditorDrawer` for the target path so the user can type and save interactively.
- Add command interceptor for `/ls`, `/dir`, `/tree`:
  - Fetch directory tree via `/api/tools/execute` (`scan_directory_tree`), render formatted listing.
- Add `/read`, `/write`, `/ls` to `SLASH_COMMANDS` palette under `💻 Host IDE`.
- Update input placeholder to include `/read, /write, /ls`.

---

### Version Authority & Master Ledgers (Rules 1, 3, 4)

- Bump version to `v5.270.0` in:
  - `version.txt`
  - `frontend/package.json`
  - `frontend/public/version.json`
  - `frontend/public/sw.js`
- Synchronize UI badges across all 4 mirror trees.
- Run production build & deployment: `npm run build; firebase deploy --only hosting --non-interactive`.
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, manual, chronologies, and `SAVED_CHECKPOINT.md`.

## Verification Plan

### Automated & Script Tests
- Test file read intent with `test_file_intent.py`.
- Test backend streaming endpoint with python test script querying `/api/chat/stream`:
  - Slash command `/read version.txt`
  - Natural language read: "Read version.txt and tell me the version"
  - Slash command `/write scratch/chat_test.txt Hello from chat`
  - Slash command `/ls scratch`
- Verify 4-mirror SHA-256 byte parity.
- Run `npm run build` to verify clean bundle compilation.
