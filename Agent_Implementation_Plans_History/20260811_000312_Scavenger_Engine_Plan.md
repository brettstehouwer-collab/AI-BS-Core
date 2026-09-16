# Refactor Scavenger Engine (Phase 4)

I reviewed `c:\AI-BS\backend\tools\scavenger_tool_agent.py`. It is very clear why it's causing issues. 

Currently, the Scavenger Engine does not actually use the LLM to fix code. Instead, it uses a naive hardcoded string replacement. If a script fails, it just slaps `# Auto-Healed` at the top and `print('Fix Verified.')` at the bottom, and then blindly executes it again. If the script had a syntax error, it will instantly crash again, leading to an infinite execution loop that just keeps appending print statements to broken code.

## User Review Required

> [!WARNING]
> The current Scavenger Engine is a recursive bomb that wastes CPU cycles and bloats files. We need to either disable it entirely, or upgrade it to actually use the local Stehouwer LLM to generate real code fixes.

## Proposed Changes

I propose we replace this naive implementation with a true AI-driven healing loop that uses the local Ollama API (exactly like the test script we just ran). 

### Backend Components

#### [MODIFY] [scavenger_tool_agent.py](file:///c:/AI-BS/backend/tools/scavenger_tool_agent.py)
- **Remove** the hardcoded string-appending logic.
- **Implement** a true LLM call. When a `.error` log is found, the agent will send the broken script's code + the error stack trace to `http://127.0.0.1:11434/api/chat`.
- **Enforce** a strict "Max Retries = 2" rule. If a script fails 3 times, the Scavenger Engine will rename it to `.quarantine` and stop trying to execute it, preventing infinite loops.

## Open Questions

> [!IMPORTANT]
> Would you prefer I completely rewrite the Scavenger Engine to use the local Ollama API for true self-healing, or would you rather I just disable/delete the sweep function entirely to keep the architecture simpler?
