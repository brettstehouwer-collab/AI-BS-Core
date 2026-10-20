# -*- coding: utf-8 -*-
import sys
import shutil
from pathlib import Path
from datetime import datetime

root = Path(r"C:\AI-BS")

# 1. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = root / "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
content = ledger_path.read_text(encoding="utf-8")

row_5258 = (
    "| 2026-09-11 | 5.258.0 | 🎬 Production Breakdown & Budget Modal Vertical Wheel Scroll Repair, Flexbox Boundary Hardening & Stylesheet Ingestion | "
    "**AI Rationale:** Responded to operator diagnostic report indicating an inability to vertically wheel or scroll up and down across the full sheet in the screenplay script breakdown budget tool (Production Breakdown & Budget modal): "
    "(1) Stylesheet Import Ingestion: Identified that neither ProductionBreakdownModal.jsx nor StagePlayBreakdownModal.jsx imported their accompanying .css stylesheets (ProductionBreakdownModal.css / StagePlayBreakdownModal.css), causing Vite to exclude the stylesheet rules from compilation. Injected explicit imports into all 4 mirror paths of both components (frontend/src/components/ProductionBreakdownModal.jsx, frontend/src/components/components/ProductionBreakdownModal.jsx, frontend/components/ProductionBreakdownModal.jsx, frontend/components/components/ProductionBreakdownModal.jsx, and StagePlayBreakdownModal.jsx counterparts). "
    "(2) Flexbox Zero-Minimum Height Boundary Hardening (ProductionBreakdownModal.css): Enforced min-height: 0 and min-width: 0 on .modal-content-grid, .visualization-area, and .tab-content across all 4 CSS mirror trees, preventing flex child containers from infinitely expanding to fit stripboard content and unlocking standard browser scrollbar calculation. "
    "(3) Isolated Viewport-Bounded Modal Architecture: Set max-height: 90vh, overflow: hidden, and position: relative on .production-breakdown-modal, bounding the dialog inside a 95vw x 90vh viewport container with an isolated sidebar and visualization pane. "
    "(4) Wheel & Trackpad Scroll Capture: Added overscroll-behavior: contain and -webkit-overflow-scrolling: touch to .tab-content and .parameters-sidebar, preventing scroll chaining and ensuring all vertical mouse wheel events scroll the shooting schedule, script breakdown tables, DOOD matrix, and top sheet budget. "
    "(5) High-Contrast Custom Scrollbars: Engineered dedicated dark-mode scrollbars (::-webkit-scrollbar width 10px, track #0f172a, thumb #334155 with hover #475569). "
    "(6) UI Version Parity & Production Deployment: Swept version to v5.258.0 across 18 frontend components, manifests, and service worker; compiled Vite production bundle and deployed live to Firebase Hosting at ai-bs-dashboard.web.app. "
    "**Modified Files:** frontend/src/components/ProductionBreakdownModal.jsx, frontend/src/components/components/ProductionBreakdownModal.jsx, frontend/components/ProductionBreakdownModal.jsx, frontend/components/components/ProductionBreakdownModal.jsx, frontend/src/components/StagePlayBreakdownModal.jsx, frontend/src/components/components/StagePlayBreakdownModal.jsx, frontend/components/StagePlayBreakdownModal.jsx, frontend/components/components/StagePlayBreakdownModal.jsx, frontend/src/components/ProductionBreakdownModal.css, frontend/src/components/components/ProductionBreakdownModal.css, frontend/components/ProductionBreakdownModal.css, frontend/components/components/ProductionBreakdownModal.css, version.txt, frontend/package.json, frontend/public/version.json, frontend/public/updates/version.json, frontend/public/sw.js, frontend/App.jsx, frontend/src/components/TopNavbar.jsx, frontend/src/components/Sidebar.jsx, frontend/src/components/ChatTab.jsx, frontend/components/TopNavbar.jsx, frontend/components/Sidebar.jsx, frontend/components/ChatTab.jsx, frontend/src/components/components/TopNavbar.jsx, frontend/src/components/components/Sidebar.jsx, frontend/src/components/components/ChatTab.jsx, frontend/components/components/TopNavbar.jsx, frontend/components/components/Sidebar.jsx, frontend/components/components/ChatTab.jsx, docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md, saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md, NotebookLM_Records/artifact_history.md, AI_BS_MASTER_ARCHITECTURAL_LEDGER.md. |\n"
)

if "5.258.0" not in content:
    header = "# AI-BS Master Architectural Ledger\n\n"
    if content.startswith(header):
        content = header + row_5258 + content[len(header):]
    else:
        content = row_5258 + content
    ledger_path.write_text(content, encoding="utf-8")
    print("AI_BS_MASTER_ARCHITECTURAL_LEDGER.md updated with 5.258.0.")
else:
    print("5.258.0 already present in AI_BS_MASTER_ARCHITECTURAL_LEDGER.md.")

# 2. Update docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md
manual_path = root / "docs" / "AI_BS_MASTER_ECOSYSTEM_MANUAL.md"
manual_text = manual_path.read_text(encoding="utf-8")

manual_section_5258 = """## 5.258.0 - 🎬 Production Breakdown & Budget Modal Vertical Wheel Scroll Repair, Flexbox Boundary Hardening & Stylesheet Ingestion (2026-09-11)
### Script Breakdown Budget Tool Layout Isolation, Zero-Minimum Height Flexbox Containers & Smooth Wheel Scroll Telemetry
**AI Rationale & Implementation:**
- **Missing Stylesheet Ingestion (`ProductionBreakdownModal.jsx`, `StagePlayBreakdownModal.jsx`):**
  - Identified that neither `ProductionBreakdownModal.jsx` nor `StagePlayBreakdownModal.jsx` imported their accompanying `.css` stylesheets (`ProductionBreakdownModal.css` / `StagePlayBreakdownModal.css`).
  - As a result, Vite excluded the stylesheet classes from compilation, rendering the modal in unconstrained inline document flow extending 5,000+ pixels off the bottom of the viewport rather than an isolated, fixed-height modal overlay (`90vh`).
  - Injected explicit stylesheet imports across all 4 mirror paths of both components (`frontend/src/components/`, `frontend/src/components/components/`, `frontend/components/`, `frontend/components/components/`).
- **Flexbox Zero-Minimum Height Boundary Hardening (`ProductionBreakdownModal.css`):**
  - Enforced `min-height: 0` and `min-width: 0` on `.modal-content-grid`, `.visualization-area`, and `.tab-content` across all 4 CSS mirror trees.
  - This prevents flex child containers from infinitely expanding to fit stripboard content and unlocks standard browser scrollbar calculation.
- **Isolated Viewport-Bounded Modal Architecture:**
  - Set `max-height: 90vh`, `overflow: hidden`, and `position: relative` on `.production-breakdown-modal`, bounding the dialog inside a `95vw x 90vh` viewport container with an isolated parameters sidebar (320px) and visualization pane.
- **Wheel & Trackpad Scroll Capture:**
  - Added `overscroll-behavior: contain` and `-webkit-overflow-scrolling: touch` to `.tab-content` and `.parameters-sidebar`, preventing scroll chaining and ensuring all vertical mouse wheel events scroll the shooting schedule, script breakdown tables, DOOD matrix, and top sheet budget.
- **High-Contrast Custom Dark-Mode Scrollbars:**
  - Engineered dedicated dark-mode scrollbars (`::-webkit-scrollbar` width 10px, track `#0f172a`, thumb `#334155` with hover `#475569`).
- **UI Version Parity & Live Production Deployment:**
  - Swept version to `v5.258.0` across 18 frontend components, manifests, and service worker.
  - Compiled Vite production bundle (25.93s) and deployed live to Firebase Hosting at `ai-bs-dashboard.web.app`.

"""

if "## 5.258.0" not in manual_text:
    manual_text = manual_text.replace(
        "**Current Ecosystem Version:** 5.257.0",
        "**Current Ecosystem Version:** 5.258.0"
    )
    # Insert right before ## 5.257.0
    marker = "## 5.257.0"
    if marker in manual_text:
        idx = manual_text.find(marker)
        manual_text = manual_text[:idx] + manual_section_5258 + manual_text[idx:]
    manual_path.write_text(manual_text, encoding="utf-8")
    print("docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md updated with 5.258.0.")
else:
    print("5.258.0 already present in docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md.")

# 3. Save copy to saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md
artifact_copy = root / "saved_data" / "artifacts" / "20260911_AI_BS_Master_Ecosystem_Manual.md"
artifact_copy.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(manual_path, artifact_copy)
print("Persisted copy to saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md.")

# 4. Append to NotebookLM_Records/artifact_history.md
nl_path = root / "NotebookLM_Records" / "artifact_history.md"
if nl_path.exists():
    nl_entry = f"\n- **2026-09-11 18:04:00**: Persisted `saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md` (Version `5.258.0` - Production Breakdown Modal Vertical Wheel Scroll Repair, Flexbox Boundary Hardening & Stylesheet Ingestion)."
    with open(nl_path, "a", encoding="utf-8") as f:
        f.write(nl_entry)
    print("NotebookLM_Records/artifact_history.md updated.")

# 5. Append to MASTER_TASKS_CHRONOLOGY.md
mt_path = root / "MASTER_TASKS_CHRONOLOGY.md"
if mt_path.exists():
    mt_entry = f"\n- **2026-09-11 18:04:00**: Production Breakdown & Stage Play Modal Vertical Wheel Scroll Fix (`v5.258.0`): Repaired mouse wheel and trackpad vertical scrolling in screenplay script breakdown budget tool: (1) Added missing stylesheet imports for ProductionBreakdownModal.css and StagePlayBreakdownModal.css across all 4 mirror paths; (2) Enforced min-height: 0, min-width: 0, and overscroll-behavior: contain on nested flex containers; (3) Added high-contrast dark-mode custom scrollbars; (4) Swept version parity to v5.258.0; (5) Built production bundle (25.93s) and deployed live to Firebase Hosting. Archived to [`Agent_Tasks_History/20260911_180400_task_production_breakdown_vertical_scroll.md`](Agent_Tasks_History/20260911_180400_task_production_breakdown_vertical_scroll.md)."
    with open(mt_path, "a", encoding="utf-8") as f:
        f.write(mt_entry)
    print("MASTER_TASKS_CHRONOLOGY.md updated.")

# 6. Append to MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md
mp_path = root / "MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md"
if mp_path.exists():
    mp_entry = f"\n- **2026-09-11 18:04:00**: Production Breakdown Modal Vertical Wheel Scroll Repair (`v5.258.0`). Archived to [`Agent_Implementation_Plans_History/20260911_180400_plan_production_breakdown_vertical_scroll.md`](Agent_Implementation_Plans_History/20260911_180400_plan_production_breakdown_vertical_scroll.md)."
    with open(mp_path, "a", encoding="utf-8") as f:
        f.write(mp_entry)
    print("MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md updated.")

# 7. Prepend entry to MASTER_HISTORICAL_INDEX.md
idx_path = root / "MASTER_HISTORICAL_INDEX.md"
if idx_path.exists():
    idx_text = idx_path.read_text(encoding="utf-8")
    sync_line = "- [SYNC 2026-09-11 18:04:00] Master Ledgers, System Manuals, Production Breakdown Modal Vertical Wheel Scroll Repair, Flexbox Boundary Hardening & Live Deployment (Repaired mouse wheel and trackpad vertical scrolling in screenplay script breakdown budget tool: added missing stylesheet imports for ProductionBreakdownModal.css and StagePlayBreakdownModal.css across all 4 mirror paths, enforced min-height: 0, min-width: 0, and overscroll-behavior: contain on nested flex containers, added high-contrast dark-mode custom scrollbars, swept version parity to v5.258.0, built production bundle in 25.93s, and deployed live to Firebase Hosting at ai-bs-dashboard.web.app) synced.\n"
    if "SYNC 2026-09-11 18:04:00" not in idx_text:
        # Prepend after header
        lines = idx_text.splitlines(keepends=True)
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if line.startswith("# Master Historical Index") and not inserted:
                new_lines.append("\n" + sync_line)
                inserted = True
        if not inserted:
            new_lines.insert(0, sync_line)
        idx_path.write_text("".join(new_lines), encoding="utf-8")
        print("MASTER_HISTORICAL_INDEX.md updated.")

print("All ledgers synchronized successfully.")
