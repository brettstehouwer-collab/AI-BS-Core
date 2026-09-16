# Bug Fix & Hardening: Operations Audit Processes Endpoint (`/api/operations/processes`)

Address the HTTP 500 Internal Server Error encountered by the frontend when polling `http://127.0.0.1:8000/api/operations/processes` and clarify the browser's unload permissions policy violation notice.

## Root Cause Analysis

### 1. HTTP 500 on `GET /api/operations/processes`
- **Location:** `C:\AI-BS\backend\routers\operations_audit_router.py`, lines 56–180 (`get_live_processes`).
- **Immediate Fatal Defect:**
  Line 173 references `"cpu_percent": cpu_pct,` in the return dictionary:
  ```python
  "host_hardware": {
      "total_ram_gb": round(mem.total / (1024**3), 2),
      "used_ram_gb": round(mem.used / (1024**3), 2),
      "ram_percent": mem.percent,
      "cpu_percent": cpu_pct,
      "logical_cores": psutil.cpu_count(logical=True)
  }
  ```
  However, `cpu_pct` was **never instantiated or defined** within `get_live_processes`, triggering an unhandled Python `NameError: name 'cpu_pct' is not defined`.
- **Secondary Fragility Points:**
  - `p.info["name"]`, `p.info["memory_info"]`, and `p.info["status"]` were accessed using direct dictionary keys (`[...]`) instead of safe dictionary lookups (`.get(...)`).
  - Monolithic `process_iter` with memory tables took ~7.8 seconds across all 400+ Windows processes.

### 2. Browser Console Unload Policy Violation Warning
- Emitted by Chrome extensions listening to deprecated `unload` event handlers (`chext_loader.js`, `chext_driver.js`). Non-breaking browser advisory.

---

## Changes Made
1. **Defined `cpu_pct` Safely:** Added `cpu_pct = psutil.cpu_percent(interval=None)` with 0.0 default.
2. **Optimized Two-Phase Filter:** Used `psutil.process_iter(['pid', 'name'])` first, fetching `memory_info`, `status`, and `cmdline` only for matching candidates, reducing latency from 7.8s to 1.0s.
3. **Resilient Fallback Return:** Wrapped in root `try ... except Exception as e:` returning structured error JSON instead of HTTP 500.
