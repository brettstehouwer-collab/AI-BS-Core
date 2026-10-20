import os
import glob
import json
from collections import defaultdict

ROOT_DIR = r"C:\AI-BS"

files = os.listdir(ROOT_DIR)

active_launchers = [
    "Launch_AI_BS.bat", "Launch_AI_BS_Dev.bat", "Launch_Desktop_App_Dev.bat",
    "Launch_OBS_Core.bat", "Quick_Build_Windows_Exe.bat", "Update_And_Run_Windows_Dev.bat",
    "Restart_Daemon.bat", "Run_Social_Daemon.bat", "Shutdown_AI_BS.bat"
]

active_docs = [
    "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md", "AI-BS_DEVELOPMENT_RULES.md",
    "MASTER_TASKS_CHRONOLOGY.md", "MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md",
    "MASTER_HISTORICAL_INDEX.md", "task.md", "implementation_plan.md",
    "SAVED_CHECKPOINT.md", "QUICK_SAVE_CHECKPOINT.md", ".agentrules"
]

deprecated_or_superseded = []
active_core = []
active_ledgers = []
one_off_scaffolds = []
large_historical_dumps = []
other_files = []

for f in files:
    full = os.path.join(ROOT_DIR, f)
    if os.path.isdir(full):
        continue
        
    size_kb = round(os.path.getsize(full) / 1024, 1)
    
    if "deprecated" in f.lower():
        deprecated_or_superseded.append((f, size_kb, "Deprecated Legacy Launcher"))
    elif f in active_launchers:
        active_core.append((f, size_kb, "Active Production/Dev Launcher"))
    elif f in active_docs:
        active_ledgers.append((f, size_kb, "Active Architectural Chronology"))
    elif f.startswith("generate_") or f.startswith("scaffold_") or f.startswith("populate_"):
        one_off_scaffolds.append((f, size_kb, "Completed Scaffolding Utility (Output Integrated)"))
    elif f in ["symbol_graph.json", "py_health_audit.json", "lighthouse audit.html", "localhost_5173-20260719T131547.html"]:
        large_historical_dumps.append((f, size_kb, "Historical Diagnostic Snapshot"))
    else:
        other_files.append((f, size_kb, "Active Ecosystem File"))

print("=" * 75)
print("           AI-BS ECOSYSTEM MASTER PURPOSE & RELEVANCE LEDGER")
print("=" * 75)

print(f"\n[1] ACTIVE PRODUCTION & DEV LAUNCHERS ({len(active_core)} files):")
for f, sz, desc in active_core:
    print(f"  - {f:<36} | {sz:>8.1f} KB | {desc}")

print(f"\n[2] ACTIVE ARCHITECTURAL CHRONOLOGY & LEDGERS ({len(active_ledgers)} files):")
for f, sz, desc in active_ledgers:
    print(f"  - {f:<36} | {sz:>8.1f} KB | {desc}")

print(f"\n[3] HISTORICAL / SUPERSEDED LAUNCHERS ({len(deprecated_or_superseded)} files):")
for f, sz, desc in deprecated_or_superseded:
    print(f"  - {f:<36} | {sz:>8.1f} KB | {desc}")

print(f"\n[4] COMPLETED SCAFFOLDING SCRIPTS ({len(one_off_scaffolds)} files):")
for f, sz, desc in one_off_scaffolds:
    print(f"  - {f:<36} | {sz:>8.1f} KB | {desc}")

print(f"\n[5] HISTORICAL DIAGNOSTIC AUDIT DUMPS ({len(large_historical_dumps)} files):")
for f, sz, desc in large_historical_dumps:
    print(f"  - {f:<36} | {sz:>8.1f} KB | {desc}")

print("=" * 75)