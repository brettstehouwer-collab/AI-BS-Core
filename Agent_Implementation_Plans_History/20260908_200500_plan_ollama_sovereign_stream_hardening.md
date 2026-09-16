# Implementation Plan: Sovereign Stream & Ollama Auto-Recovery Hardening (v5.224.0)

## Overview
Recent chat interactions in BS-Chat ("Stehouwer LLM") reported:
```text
▲ Local Ollama Engine unreachable on port 11434 / 11435. Engaging auto-recovery...
Error in sovereign stream connection: All connection attempts failed (All connection attempts failed)
```
Diagnostic probing confirmed:
1. Port 11434 was not running initially, while port 11435 was listening.
2. Port 11434 (`C:\AI-BS\.ollama\models`) contains the active `stehouwer_llm` model and other manifests (`llama3`, `command-r`, `mixtral`, `nomic-embed-text`).
3. Port 11435 (`E:\AI_BS_Resources\LLM_Models`) has an empty manifest catalog (`{"models":[]}`). When fallback routed to 11435, Ollama returned HTTP 404.
4. The auto-recovery routine `ensure_ollama_running()` in `dispatcher.py` failed due to Windows cmd quote-escaping syntax errors (`Cannot convert value "Hidden\" to type ProcessWindowStyle`), preventing automated daemon restoration.

---

## User Review Required
> [!IMPORTANT]
> - Should port 11435 continue to be spun up if `E:\AI_BS_Resources\LLM_Models` has no models populated, or should models from `C:\AI-BS\.ollama\models` be symlinked/copied to `E:\AI_BS_Resources\LLM_Models` for true dual-drive redundancy?
> - Changes to `backend\core\sovereign_reasoning\dispatcher.py` will harden `ensure_ollama_running()` by replacing brittle PowerShell command string invocation with direct Python `subprocess.Popen` using explicit environment mapping.

---

## Proposed Changes

### Core Sovereign Reasoning Engine

#### [MODIFY] [dispatcher.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py)
- Refactor `ensure_ollama_running()`:
  - Replace shell-escaped PowerShell string invocation with direct execution using native `subprocess.Popen` and `socket.connect_ex` check.
- Differentiate HTTP response statuses in stream generation:
  - If target endpoint returns HTTP 404 (model not found), log distinct diagnostic warning rather than masking it as an unreachable host.
  - Only engage fallback or recovery if connection is refused or timed out.

---

### Startup Orchestration

#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
- Add a 1-second delay between the primary Ollama launcher (port 11434) and secondary instance (port 11435) to prevent race conditions during GPU compute detection and socket binding.
- Add fallback to `C:\AI-BS\.ollama\models` for port 11435 if `E:\AI_BS_Resources\LLM_Models` is unpopulated.

---

## Verification Plan

### Automated Tests
- Direct HTTP endpoint status verification:
  ```powershell
  curl.exe -s http://localhost:11434/api/tags
  ```
- Inference test on port 11434:
  ```powershell
  python -c "import urllib.request, json; req = urllib.request.Request('http://localhost:11434/api/generate', data=json.dumps({'model': 'stehouwer_llm', 'prompt': 'test ping', 'stream': False}).encode('utf-8'), headers={'Content-Type': 'application/json'}); res = urllib.request.urlopen(req); print(res.read().decode('utf-8'))"
  ```
- Test `ensure_ollama_running()` directly in a standalone Python script.

### Manual Verification
- Send a test prompt to BS-Chat / Stehouwer LLM from the web dashboard (`ai-bs-dashboard.web.app` or `http://localhost:5173`).
