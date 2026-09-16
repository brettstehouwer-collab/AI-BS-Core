# AI-BS Sovereign Stream & Ollama Diagnostic Notes

## Incident Context
- **Component:** Stehouwer LLM / BS-Chat Sovereign Stream (`backend\core\sovereign_reasoning\dispatcher.py`)
- **Observed Alert:** `Local Ollama Engine unreachable on port 11434 / 11435. Engaging auto-recovery...`
- **Streaming Error:** `Error in sovereign stream connection: All connection attempts failed (All connection attempts failed)`
- **Trace Target:** FastAPI Edge Server (`AI_BS_Backend.py` on port 8080)

---

## Root Cause Analysis
1. **Daemon Listener Discrepancy:**
   - Primary endpoint `http://127.0.0.1:11434` hosts the `stehouwer_llm` model (`C:\AI-BS\.ollama\models`).
   - Secondary endpoint `http://127.0.0.1:11435` points to `E:\AI_BS_Resources\LLM_Models`, which currently contains no model manifests (`{"models":[]}`).
   - If port 11434 terminates or fails to bind during boot, requests fall through to 11435. Because `stehouwer_llm` is not found on 11435, Ollama returns HTTP 404.
2. **Dispatcher Stream Handling:**
   - In `backend\core\sovereign_reasoning\dispatcher.py`, `if response.status_code == 200` silently skipped non-200 responses (such as HTTP 404).
   - This triggered the fallback auto-recovery block (`ensure_ollama_running()`), which then attempted a retry strictly against 11434.
3. **Auto-Recovery Process Invocation:**
   - `ensure_ollama_running()` invoked a PowerShell script via `subprocess.Popen(..., shell=True)` with double-nested quotes. On Windows `cmd.exe`, the backslash escaping malformed the arguments (`Cannot convert value "Hidden\" to type ProcessWindowStyle`), preventing the self-healing routine from launching Ollama.

---

## Verification & Diagnostic Commands

### 1. Process & Port Inspection
```powershell
Get-Process -Name ollama -ErrorAction SilentlyContinue
netstat -ano | findstr "11434 11435"
```

### 2. Direct HTTP Endpoint & Model Verification
```powershell
# Port 11434 (Primary - C:\AI-BS\.ollama\models)
curl.exe -s http://localhost:11434/api/tags

# Port 11435 (Secondary - E:\AI_BS_Resources\LLM_Models)
curl.exe -s http://localhost:11435/api/tags
```

### 3. Direct Model Generation Ping
```powershell
python -c "import urllib.request, json; req = urllib.request.Request('http://localhost:11434/api/generate', data=json.dumps({'model': 'stehouwer_llm', 'prompt': 'ping', 'stream': False}).encode('utf-8'), headers={'Content-Type': 'application/json'}); res = urllib.request.urlopen(req); print(res.read().decode('utf-8')[:200])"
```

---

## Actionable Remediation Checklist
- [x] Verified `stehouwer_llm` model presence in `C:\AI-BS\.ollama\models`.
- [x] Verified active listener on port 11434 (`ollama.exe serve`).
- [ ] Refactor `ensure_ollama_running()` in `backend\core\sovereign_reasoning\dispatcher.py` to use native `subprocess.Popen` array without shell quote escaping.
- [ ] Update `dispatcher.py` stream evaluation to log HTTP non-200 status codes (e.g. 404 model not found) distinctly from connection failures.
- [ ] Synchronize or symlink required model manifests into `E:\AI_BS_Resources\LLM_Models` if port 11435 is retained as an active failover target.
