# Hybrid LLM Integration Plan
*Stehouwer LLM + Nemotron 3.5 Lightning*

I am currently pulling the `nemotron-3.5-lightning` model in the background. While the 30B parameters download, please review the architecture plan for the hybrid integration inside your `AI_BS_Backend.py` router.

## Proposed Architecture Changes

### 1. Dynamic Context-Length Router (Book-to-Script)
I will inject a token estimation logic block inside `def chat_endpoint` right after the messages are extracted.
- **Logic:** Calculate the approximate token length of the incoming payload (e.g. `total_chars / 4`).
- **Threshold Override:** If the payload exceeds 32,000 tokens (a massive script or book), the router will explicitly bypass the requested model and force `nemotron-3.5-lightning` to utilize its 1-Million token context window and prevent an Out-Of-Memory (OOM) crash on your GPU.

### 2. Daemon Fast-Routing
Currently, background daemons (like `memory_daemon` and `research_agent_daemon`) blindly default to `stehouwer_llm`. 
- **Logic:** I will update the daemons' internal HTTP post requests to explicitly request `nemotron-3.5-lightning`.
- **Result:** This ensures that continuous background tasks run on the 3B-active parameter Mixture-of-Experts architecture, preserving your VRAM for Monetization Hosting and foreground UI tasks.

### 3. Swarm Orchestrator Handoff
- **Logic:** Update `bullshit_orchestrator.py` (Swarm Orchestrator) to use `nemotron-3.5-lightning` as the primary intent classifier and tool caller, while reserving `stehouwer_llm` as the "Lead System Architect" for complex generation handoffs.

> [!WARNING]  
> **User Review Required:**
> Do you approve this hybrid routing logic? Specifically, is an automatic threshold of **32,000 tokens** the correct point where you want the backend to automatically switch from Stehouwer LLM to Nemotron? 

## Verification Plan
- Verify the Ollama pull successfully completes.
- Modify `AI_BS_Backend.py` with the hybrid routing block.
- Modify `memory_daemon.py` and `research_agent_daemon.py` to target Nemotron.
- Send a massive text block (>40k tokens) to the API and verify via logs that it successfully intercepts and routes to Nemotron instead of crashing Stehouwer LLM.
