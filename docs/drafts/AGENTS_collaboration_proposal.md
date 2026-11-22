# Proposed Addition to `C:\AI-BS\AGENTS.md` (Proposal Only)

> **Status:** Proposal only — `C:\AI-BS\AGENTS.md` has not been modified.

```markdown
## Multi-Assistant Collaboration

- **Canonical Checkout & Worktrees:** Use `C:\AI-BS` as the canonical checkout. Create isolated task worktrees from `C:\AI-BS` for concurrent backend (`backend/`) and UI (`frontend/`) work rather than editing the shared working tree directly.
- **File Ownership & Preservation:** Do not revert, overwrite, or stage another assistant's uncommitted changes. Check `git status` before editing shared files (such as `backend/AI_BS_Backend.py`, `backend/core/media_intent_policy.py`, `frontend/App.jsx`, or `frontend/components/ChatTab.jsx`).
- **Running Services:** Do not restart, kill, or modify running local services (ports `8000`, `8002`, `8007`, `8017`, `8025`, `8026`, `8080`, `5173`, `11434`, `20241`) unless explicitly authorized for the task.
- **Verification & Evidence:** Record only commands actually run and outputs directly observed. Mark unverified commands as untested and distinguish live runtime observations from older notes.
- **Handoffs:** Use `docs/drafts/HANDOFF_TEMPLATE.md` (or the active handoff format) to record starting/result commits, scope, checks run, remaining uncertainties, and next actions.
```
