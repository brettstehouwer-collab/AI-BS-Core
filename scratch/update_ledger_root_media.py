import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

ledger = r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
with open(ledger, "a", encoding="utf-8") as f:
    f.write(f"\n\n### [{timestamp}] Feature: Root Workspace Media Scanning\n")
    f.write("- **AI Rationale**: Expanded the Media & Asset Vault to scan the entire `C:\\AI-BS` root directory for any media assets (.png, .jpg, .mp4, etc.) while systematically excluding system directories (`node_modules`, `ComfyUI`, `Android Studio`, `frontend`, `backend`, etc.) to prevent performance bottlenecks. \n")
    f.write("- **Implementation**: Added a new FastAPI route `GET /api/media/serve` to stream absolute files securely, and updated `/api/media-vault/all` to perform a pruned `os.walk` directory scan, returning results under a new `Root Workspace Media` category.\n")
    f.write("- **Modified File List**: `C:\\AI-BS\\backend\\AI_BS_Backend.py`.\n")

print("Ledger updated.")
