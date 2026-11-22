import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 1. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger = r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
with open(ledger, "a", encoding="utf-8") as f:
    f.write(f"\n\n### [{timestamp}] Bugfix: Top Bar & Sidebar Layout Collapse\n")
    f.write("- **AI Rationale**: Fixed a critical CSS Grid issue in `.app-shell` that was causing the main content area (e.g., Media & Asset Vault) and the Sidebar to collapse and leave huge blank spaces on the right. Changed `app-shell` from `display: grid` with two columns to `display: flex`, and moved `TopNavbar` inside the flex container to ensure proper vertical stacking when in Top Bar mode and proper horizontal distribution for `react-resizable-panels` when in Sidebar mode.\n")
    f.write("- **Modified File List**: `App.jsx`, `style.css`.\n")

print("Ledger updated.")
