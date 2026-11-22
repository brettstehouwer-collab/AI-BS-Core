import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

ledger = r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
with open(ledger, "a", encoding="utf-8") as f:
    f.write(f"\n\n### [{timestamp}] Bugfix: UnifiedMediaVaultTab ReferenceError\n")
    f.write("- **AI Rationale**: Fixed a critical `ReferenceError: BACKEND_URL is not defined` in `UnifiedMediaVaultTab.jsx` that was silently caught in the `catch` block of `fetchMedia`, resulting in an empty categories array and the UI displaying 'No media found in this category' without any category buttons.\n")
    f.write("- **Implementation**: Updated the component to use the correctly mapped `backendUrl` prop passed down from `App.jsx`, ensuring successful API calls to `/api/media-vault/all`.\n")
    f.write("- **Modified File List**: `C:\\AI-BS\\frontend\\components\\UnifiedMediaVaultTab.jsx`.\n")

print("Ledger updated.")
