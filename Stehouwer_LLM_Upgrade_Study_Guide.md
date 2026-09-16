# Stehouwer LLM Phased Upgrade & 200GB SQLite Integration — Complete Study Guide

**Session Date:** July 22, 2026  
**System:** AI-BS (Autonomous Intelligence & Build System)  
**Target Hardware:** Local Ryzen 9 9950X / RTX 4090 GPU / Cloudflare Tunnel / Firebase Hosting  

---

## 📚 Table of Contents
1. [Core Principles of Local LLM Tool Calling](#1-core-principles-of-local-llm-tool-calling)
2. [Phase 1: Baseline Safety & Checkpoint System](#phase-1-baseline-safety--checkpoint-system)
3. [Phase 2: Custom Modelfile Persona & System Directive Tuning](#phase-2-custom-modelfile-persona--system-directive-tuning)
4. [Phase 3: Python Tool Registry Architecture](#phase-3-python-tool-registry-architecture)
5. [Phase 4: Polyglot Scavenger Engine & Self-Healing Loop](#phase-4-polyglot-scavenger-engine--self-healing-loop)
6. [Phase 5: Multimodal & ComfyUI Tool Binding](#phase-5-multimodal--comfyui-tool-binding)
7. [Phase 6: Dedicated UI Tabs & Firebase Production Deployment](#phase-6-dedicated-ui-tabs--firebase-production-deployment)
8. [Phase 7: Handling 200GB+ SQLite Blockchain Datasets](#phase-7-handling-200gb-sqlite-blockchain-datasets)
9. [Key PowerShell & Python Commands Reference](#key-powershell--python-commands-reference)

---

## 1. Core Principles of Local LLM Tool Calling

### How an LLM "Thinks" vs. How Tools Work
An LLM (Large Language Model) does not have consciousness; it computes probabilistic predictions for the next most logical token. When operating inside an agentic framework like **AI-BS**, its capabilities expand through **Function Calling (Tool Use)**.

```
[User Request] ➔ [Context Sweep (Living Learning Memory)] ➔ [Ollama Token Prediction] ➔ [JSON Tool Output] ➔ [Backend Execution] ➔ [Synthesized Result]
```

### The 6 Master Categories of LLM Tools Built into AI-BS:
1. **Data Retrieval & Knowledge**: `query_master_memory`, `discover_and_inspect_databases`
2. **Computation & Logic**: `execute_sandbox_script` (Python execution)
3. **File & System Operations**: `read_sandbox_file`, `write_sandbox_file`
4. **Enterprise Connectors**: Firebase & Cloudflare endpoints
5. **Multimodal Generation**: `generate_comfy_image` (ComfyUI port 8188), `analyze_image` (LLaVA vision model)
6. **Meta-Cognitive & Agentic**: `ScavengerToolAgent` auto-healing background loops

---

## Phase 1: Baseline Safety & Checkpoint System

Before making architectural modifications, we backed up existing working files to ensure zero risk of corruption.

```powershell
# Backup Command
New-Item -ItemType Directory -Force -Path 'c:\AI-BS\backend\backups\pre_tool_upgrade_20260722';
Copy-Item -Path 'c:\AI-BS\backend\AI_BS_Backend.py' -Destination 'c:\AI-BS\backend\backups\pre_tool_upgrade_20260722\AI_BS_Backend.py';
```

---

## Phase 2: Custom Modelfile Persona & System Directive Tuning

We configured `stehouwer_llm` in Ollama with system directives, an 8k context window, and JSON tool calling formatting.

**File Location:** `c:\AI-BS\backend\models\stehouwer_llm.Modelfile`

```dockerfile
FROM llama3.1:latest

PARAMETER num_ctx 8192
PARAMETER temperature 0.2
PARAMETER top_p 0.9

PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"
PARAMETER stop "<|eot_id|>"

SYSTEM """
You are the Stehouwer LLM, the central cognitive intelligence engine of the AI-BS created for Brett Adam Stehouwer.
OPERATIONAL DIRECTIVES:
1. STABILITY & PRECISION: Provide accurate, zero-fluff, production-ready responses.
2. TOOL CALLING: Output JSON function calls when file, code, or memory execution is needed.
3. HEURISTIC ALIGNMENT: Prioritize user-validated historical baselines from Living Learning Memory.
"""
```

**Build Command:**
```bash
ollama create stehouwer_llm -f c:\AI-BS\backend\models\stehouwer_llm.Modelfile
```

---

## Phase 3: Python Tool Registry Architecture

**File Location:** `c:\AI-BS\backend\tools\tool_registry.py`

The `ToolRegistry` acts as a centralized dispatcher that decodes JSON tool requests emitted by `stehouwer_llm` and executes them inside isolated Python handlers.

Exposed Endpoints in `AI_BS_Backend.py`:
- `GET /api/tools`: Returns declarations for all registered tools.
- `POST /api/tools/execute`: Executes tools dynamically with parameter validation.

---

## Phase 4: Polyglot Scavenger Engine & Self-Healing Loop

**File Location:** `c:\AI-BS\backend\tools\scavenger_tool_agent.py`

The `ScavengerToolAgent` runs in the background to automatically detect broken scripts (`*.error`) in the sandbox directory, inspect `master_memory_dump.json` for verified fixes, apply corrected code, and verify that `returncode == 0` before removing the error log.

---

## Phase 5: Multimodal & ComfyUI Tool Binding

We bound local visual generation and vision model capabilities:
- **`generate_comfy_image`**: Dispatches prompt payloads to local ComfyUI instance on port 8188.
- **`analyze_image`**: Converts uploaded images to Base64 and queries local LLaVA vision model via Ollama.

---

## Phase 6: Dedicated UI Tabs & Firebase Production Deployment

1. Added dedicated **AI-BS Assistant** tab (`ChatTab`) under **AI & Data** in the Sidebar navigation (`c:\AI-BS\frontend\components\Sidebar.jsx` & `App.jsx`).
2. Maintained header model selection dropdown across all other tabs.
3. Built production bundle and deployed to Firebase Hosting:

```powershell
powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"
```
**Live URL:** https://ai-bs-dashboard.web.app

---

## Phase 7: Handling 200GB+ SQLite Blockchain Datasets

### Why SQLite Scales to 200GB+ Without Crashing RAM:
- SQLite uses disk-based B-tree indexes and OS memory-mapped I/O (`mmap`).
- It does **NOT** load 200GB into RAM. Queries read only the target pages from disk.
- Read-Only mode (`file:path?mode=ro`) ensures zero corruption risk.

### Extraction & Inspection Results:
- **Archive Path:** `D:\qbittzdlds\mainnet.2026-07-01.tar.gz`
- **Extracted Location:** `C:\AI-BS\database\blockchain_v2_mainnet.sqlite`
- **Uncompressed Size:** **199.45 GB**
- **Total Rows Analyzed:**
  - `coin_record`: **413,961,900 rows** (413 Million)
  - `full_blocks`: **8,936,286 rows** (8.9 Million)
  - `hints`: **46,282,870 rows** (46.2 Million)

### Performance Test Result:
Executing a `SELECT` query across **8.9 million block headers** on a **200 GB database** completed in **2.00 milliseconds**!

---

## Key PowerShell & Python Commands Reference

### 1. Live Terminal File Growth Watcher (PowerShell)
```powershell
while ($true) { Clear-Host; $file = Get-Item 'C:\AI-BS\database\blockchain_v2_mainnet.sqlite' -ErrorAction SilentlyContinue; if ($file) { Write-Host ("🔥 Live Extracted Database Size: {0:N2} GB" -f ($file.Length / 1GB)) -ForegroundColor Green } else { Write-Host "Waiting for extraction..." }; Start-Sleep -Seconds 2 }
```

### 2. Python Read-Only SQLite Query Test
```python
import sqlite3

db_path = r'C:\AI-BS\database\blockchain_v2_mainnet.sqlite'
conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
cursor = conn.cursor()
cursor.execute('SELECT height, in_main_chain FROM full_blocks ORDER BY height DESC LIMIT 5')
print(cursor.fetchall())
conn.close()
```
