# Tuning the Backend AI Model Routing Tunnels

Based on my analysis of the `C:\AI-BS\backend` architecture, I discovered a massive routing vulnerability that is likely causing models to misfire, drop context, or fail to connect. 

There are currently **81 hardcoded instances** across your Python files (such as `AI_BS_Backend.py`, `neural_router.py`, `vision_daemon.py`, etc.) where the system tries to route prompts to `http://host.docker.internal:11434` instead of a standardized, configurable environment variable or a clean `127.0.0.1` native port. 

Because your ecosystem runs natively via WSL2 / Windows 11 (without a Docker container encapsulation for these daemons), relying on `host.docker.internal` is extremely brittle and can lead to broken back-end tunnels if the DNS resolver drops. 

## Proposed Changes

To guarantee all prompts are correctly and reliably routed to the Stehouwer LLM on your local GPU, I propose a global architectural patch:

### 1. Global Tunnel Standardization
I will write and execute a custom Python patching script that scans every `.py` and `.json` file in `C:\AI-BS\backend` and perfectly replaces all instances of:
`host.docker.internal:11434`
with
`127.0.0.1:11434` (the native, hyper-reliable Windows localhost loopback).

### 2. Update Configuration
I will update `ai_bs_config.json` so that `"ollama_host"` is natively `"127.0.0.1:11434"`.

### 3. Verify Routing
I will run test endpoints in `AI_BS_Backend.py` to ensure the neural router can hit the local Stehouwer LLM without timing out.

> [!WARNING]  
> **User Review Required:**
> Do you approve this global standardization to `127.0.0.1:11434` to repair the AI routing tunnels? Alternatively, if you *prefer* to keep `host.docker.internal` for a specific reason (e.g. you have a unique WSL vSwitch configuration), please let me know and we can instead centralize the variable so it pulls dynamically from `ai_bs_config.json`. 

## Verification Plan
- Execute the global replace script.
- Verify `Total occurrences` of `host.docker.internal` drops to 0.
- Execute a test ping against `127.0.0.1:11434` to ensure Ollama acknowledges the route.
