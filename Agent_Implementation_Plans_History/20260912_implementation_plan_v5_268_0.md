# Implementation Plan: BS-Chat Organized Slash Commands & Fast Options Dropdown Box

Create a clean, organized, and searchable dropdown palette for **Slash Commands and Fast Options** in BS-Chat. This cleans up the chat interface by replacing clutter with an intuitive, unified pop-up menu that activates both via a dedicated input toolbar button and automatically when typing `/` into the chat input bar.

---

## User Review Required

> [!IMPORTANT]
> - **Dual Activation Mode**: The dropdown activates either by clicking the `[/] Commands` button beside the input bar OR automatically whenever the user types `/` in the message textarea.
> - **Multi-Mirror Synchronization Law (Rule 1)**: All modifications to `ChatTab.jsx` and any newly added dropdown components will be synchronized simultaneously across all 4 mirror paths with 100% SHA-256 hash parity:
>   1. `frontend/src/components/`
>   2. `frontend/components/`
>   3. `frontend/src/components/components/`
>   4. `frontend/components/components/`
> - **Version Increment**: Ecosystem version will increment to `v5.268.0` with full ledger, manual, and deployment sync.

---

## Architecture & Proposed Design

### 1. Unified Slash Commands & Fast Options Catalog
Cataloging all existing and enhanced BS-Chat commands into 5 clean categories:

| Category | Commands & Fast Options | Functionality |
| :--- | :--- | :--- |
| **👑 Master Oversight & 43 Modules** | `/monitor`, `/oversight`<br>`/modules`<br>`/switch <tab_key>` | Live 43-module parent monitoring dashboard, catalog listing, and instantaneous workspace navigation. |
| **🏛️ Universal 11-Space Storage** | `/spaces`<br>`/retrieve <query>`<br>`/ingest <text>` | 11-database storage status overview, multi-database parallel text search, and on-demand DB persistence. |
| **💻 Host IDE & System Execution** | `/ps <cmd>`<br>`/wsl [distro] <cmd>`<br>`/edit <path>`<br>`/deploy`<br>`/kill <port>` | High-privilege PowerShell execution, Ubuntu WSL2 commands, in-chat interactive code editor, Firebase cloud deployment, and process port termination. |
| **⚡ Autonomous Shadow Coder** | `/coder <prompt>`<br>`/syntax <lang> <code>`<br>`/symbol <name>` | Local Ollama Qwen 2.5 Coder dispatch, pre-flight AST validation (Python/JS/Go), and fast symbol lookup across routes and schemas. |
| **🧹 Chat & System Utilities** | `/clear`<br>`/status`<br>`/health`, `/doctor`<br>`/help` | Save conversation to Master Memory & clear chat, 18-port topology status, health audit, and command reference guide. |
| **🚀 Fast Starters & Presets** | 18 Quick Starter Cards | One-click access to starter prompts (Screenplay, Memory, Accounting, Unreal, ComfyUI, etc.) directly inside the dropdown. |

---

### 2. Dropdown UI / UX Specifications
- **Position & Anchor**: Positioned directly above the chat input bar (`bottom: 54px`), responsive width (`min(520px, 95vw)`), max height `460px` with a custom cyber dark scrollbar.
- **Top Bar / Search**:
  - Search input: `🔍 Filter commands or options... (e.g. /monitor, /retrieve, /ps)`
  - Real-time filtered count indicator (e.g. `22 commands`)
  - Close button `✕` and keyboard hint: `[Esc] to close • [Enter] to run/select`
- **Category Filter Pills**:
  - `[All]`, `[👑 Oversight]`, `[🏛️ 11 Spaces]`, `[💻 Host IDE]`, `[⚡ Coder]`, `[🧹 Utilities]`, `[🚀 Starters]`
- **Command Item Layout**:
  - Command syntax chip (e.g., `/retrieve <query>`) with high-contrast color coding.
  - Title and descriptive summary.
  - Action triggers:
    - **`[▶ Run]`**: For commands with no arguments (e.g. `/monitor`, `/spaces`, `/modules`, `/deploy`, `/status`, `/help`, `/clear`), executes immediately on click.
    - **`[⚡ Use]`**: For parameterized commands, pre-fills the textarea and focuses cursor after the command prefix.
- **Auto-Trigger on `/`**:
  - Typing `/` as the first character automatically opens the dropdown.
  - Typing `/ret` automatically filters the list to matching commands (`/retrieve`).
  - Pressing `Escape` or clicking outside closes the dropdown.
- **Cleaned-Up BS-Chat Bar**:
  - Unifies the standalone `⚡ Presets` button into a streamlined `[/] Commands & Options` dropdown trigger button.
  - Keeps the input area clutter-free while giving instant, single-click access to all tools, commands, and starters.

---

## Proposed Changes

### Frontend Core

#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx) (and all 4 mirrors)
- Implement `SlashCommandsDropdown` component or integrated drawer with keyboard navigation (`ArrowUp`, `ArrowDown`, `Enter`, `Escape`).
- Add state `showCommandsDropdown`, `commandSearchQuery`, `selectedCommandCategory`.
- Add auto-open effect when `footerInput.startsWith('/')`.
- Add `/clear` and `/help` command handlers in the slash command interceptor loop.
- Replace the legacy separate presets button with the unified, organized `[/] Commands` dropdown.
- Synchronize simultaneously to:
  1. `frontend/src/components/ChatTab.jsx`
  2. `frontend/components/ChatTab.jsx`
  3. `frontend/src/components/components/ChatTab.jsx`
  4. `frontend/components/components/ChatTab.jsx`

---

## Verification Plan

### Automated Tests
1. **Frontend Build**:
   `powershell -ExecutionPolicy Bypass -Command "cd C:\AI-BS\frontend; npm run build"`
   Verify Vite compiles clean with 0 TypeScript/JSX errors.
2. **Mirror Parity Check**:
   Run python checksum verification to ensure all 4 mirror paths of `ChatTab.jsx` have identical SHA-256 hashes.
3. **Backend Route Smoke Check**:
   Verify backend endpoints for oversight and spaces remain functional.

### Manual / Browser Verification
1. Open BS-Chat in browser.
2. Click `[/] Commands` button -> verify categorized dropdown opens with search filter, category tabs, and action buttons.
3. Type `/` in the message input -> verify dropdown automatically pops up.
4. Type `/mon` -> verify list filters down to `/monitor`.
5. Click `[▶ Run]` on `/monitor` -> verify executive 43-module oversight dashboard renders immediately.
6. Click `/retrieve <query>` -> verify input pre-fills with `/retrieve ` and focuses cursor.
7. Press `Escape` or click outside -> verify dropdown dismisses cleanly.
8. Deploy to Firebase Hosting and verify live at `https://ai-bs-dashboard.web.app`.
