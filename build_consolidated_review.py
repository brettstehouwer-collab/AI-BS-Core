#!/usr/bin/env python3
"""AI-BS Sovereign Ecosystem: Unified Master Review & Architectural Dossier Compiler.

Consolidates all files from:
1. C:\\Users\\footb\\OneDrive\\Desktop\\New folder
2. User-submitted C:\\AI-BS\\ root manifests
Into a single, production-grade Markdown review dossier at:
C:\\Users\\footb\\OneDrive\\Desktop\\CONSOLIDATED_REVIEW.md
for review by the operator and Gemini 4 Argon.
"""

from __future__ import annotations

import os
import sys
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

NEW_FOLDER = r"C:\Users\footb\OneDrive\Desktop\New folder"
OUTPUT_FILE = r"C:\Users\footb\OneDrive\Desktop\CONSOLIDATED_REVIEW.md"

PASTED_FILES = [
    r"C:\AI-BS\.agentrules",
    r"C:\AI-BS\.antigravityrules",
    r"C:\AI-BS\AI_BS_Trainer_Setup.exe",
    r"C:\AI-BS\AI-BS_Trainer_Setup_v2.21.0.exe",
    r"C:\AI-BS\Antigravity IDE.exe",
    r"C:\AI-BS\Antigravity-x64 (1).exe",
    r"C:\AI-BS\Antigravity-x64 (2).exe",
    r"C:\AI-BS\Antigravity-x64.exe",
    r"C:\AI-BS\cloudflared.exe",
    r"C:\AI-BS\daemon_manager.exe",
    r"C:\AI-BS\flstudio_win64_26.1.6.5639.exe",
    r"C:\AI-BS\GeminiSetup.exe",
    r"C:\AI-BS\GoogleDriveSetup.exe",
    r"C:\AI-BS\PLITCH_Setup_1662_2.21.0.exe",
    r"C:\AI-BS\Streamlabs+Desktop+Setup+1.21.9-GtfzxsBesau6v03.exe",
    r"C:\AI-BS\Streamlabs+Desktop+Setup+1.21.9-o1es4v5ynLqmDOp.exe",
    r"C:\AI-BS\tiktok_live_studio_downloader-v0.0.1-wid-98yo96rlD3M.exe",
    r"C:\AI-BS\vnc_bridge.exe",
    r"C:\AI-BS\Dockerfile.backend",
    r"C:\AI-BS\AI-BS.code-workspace.bak",
    r"C:\AI-BS\version.txt.1791231225.bak",
    r"C:\AI-BS\lighthouse audit.html",
    r"C:\AI-BS\localhost_5173-20260719T131547.html",
    r"C:\AI-BS\MyChart - Test Details.html",
    r"C:\AI-BS\TheSimpleChef_Invoice_TSC-2026-001.html",
    r"C:\AI-BS\AI-BS.code-workspace",
    r"C:\AI-BS\generation.csv",
    r"C:\AI-BS\archive (1).zip",
    r"C:\AI-BS\idesForupgrade.zip",
    r"C:\AI-BS\THE SIMPLE CHEF (3) (5).zip",
    r"C:\AI-BS\vastai_install_logs.tar.gz",
    r"C:\AI-BS\leads_store.db",
    r"C:\AI-BS\prestige_powerwash.db",
    r"C:\AI-BS\state.db",
    r"C:\AI-BS\stehouwer_vault.db",
    r"C:\AI-BS\.dockerignore",
    r"C:\AI-BS\Modelfile.Dolphin",
    r"C:\AI-BS\.env",
    r"C:\AI-BS\Dockerfile",
    r"C:\AI-BS\LICENSE",
    r"C:\AI-BS\Modelfile",
    r"C:\AI-BS\Modelfile_dolphin",
    r"C:\AI-BS\Modelfile_hermes",
    r"C:\AI-BS\Modelfile_qwen",
    r"C:\AI-BS\minerwatch.go",
    r"C:\AI-BS\Modelfile.Hermes",
    r"C:\AI-BS\Gemini_Generated_Image_edhbsjedhbsjedhb.jpg",
    r"C:\AI-BS\c_drive_scan_report.json",
    r"C:\AI-BS\client_secret.json",
    r"C:\AI-BS\codeEditorTool.json",
    r"C:\AI-BS\CppProperties.json",
    r"C:\AI-BS\crypto_offramp_guide.md.metadata.json",
    r"C:\AI-BS\daemon.json",
    r"C:\AI-BS\direct_deposit_setup_guide.md.metadata.json",
    r"C:\AI-BS\drip_ledger.json",
    r"C:\AI-BS\implementation_plan.md.metadata.json",
    r"C:\AI-BS\income_breakdown.md.metadata.json",
    r"C:\AI-BS\ingest_manifest.json",
    r"C:\AI-BS\leads_store.json",
    r"C:\AI-BS\lighthouse_report.json",
    r"C:\AI-BS\live_check_report.json",
    r"C:\AI-BS\master_memory_dump.json",
    r"C:\AI-BS\minimal_wan_api.json",
    r"C:\AI-BS\package.json",
    r"C:\AI-BS\penitscradle_audit_ledger_1789023393998.json",
    r"C:\AI-BS\py_health_audit.json",
    r"C:\AI-BS\pyrightconfig.json",
    r"C:\AI-BS\remote_agents.json",
    r"C:\AI-BS\SECURITY_INTEGRITY_MANIFEST.json",
    r"C:\AI-BS\skills-lock.json",
    r"C:\AI-BS\state.json",
    r"C:\AI-BS\step_2_exchange_setup_guide.md.metadata.json",
    r"C:\AI-BS\symbol_graph.json",
    r"C:\AI-BS\system_scan_report.json",
    r"C:\AI-BS\task.md.metadata.json",
    r"C:\AI-BS\token.json",
    r"C:\AI-BS\vercel.json",
    r"C:\AI-BS\walkthrough.md.metadata.json",
    r"C:\AI-BS\temp_chattab.jsx",
    r"C:\AI-BS\uv.lock",
    r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    r"C:\AI-BS\AI_BS_MASTER_FIX_AND_OPTIMIZATION_LOG.md",
    r"C:\AI-BS\AI_BS_MASTER_HANDOFF_SAVEPOINT.md",
    r"C:\AI-BS\AI_BS_REDUNDANCY_AUDIT_AND_CONSOLIDATION.md",
    r"C:\AI-BS\AI_BS_TOOL_INVENTORY_CATALOG.md",
    r"C:\AI-BS\AI-BS_DEVELOPMENT_RULES.md",
    r"C:\AI-BS\Brett's gemini word.md",
    r"C:\AI-BS\CODE_OF_CONDUCT.md",
    r"C:\AI-BS\CONTRIBUTING.md",
    r"C:\AI-BS\crypto_offramp_guide.md",
    r"C:\AI-BS\direct_deposit_setup_guide.md",
    r"C:\AI-BS\DIRECTORY_INDEX.md",
    r"C:\AI-BS\IMAGE_GENERATION_README.md",
    r"C:\AI-BS\implementation_plan.md",
    r"C:\AI-BS\income_breakdown.md",
    r"C:\AI-BS\John.md",
    r"C:\AI-BS\lminfo.md",
    r"C:\AI-BS\Luke.md",
    r"C:\AI-BS\Mark.md",
    r"C:\AI-BS\MASTER_HANDOFF_CHRONOLOGY.md",
    r"C:\AI-BS\MASTER_HISTORICAL_INDEX.md",
    r"C:\AI-BS\MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md",
    r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md",
    r"C:\AI-BS\Matthew.md",
    r"C:\AI-BS\miners_status_and_payout_audit.md",
    r"C:\AI-BS\mission_spec.md",
    r"C:\AI-BS\NOTES.md",
    r"C:\AI-BS\PROJECT.md",
    r"C:\AI-BS\QUICK_SAVE_CHECKPOINT.md",
    r"C:\AI-BS\ReAct_Agent_Architecture.md",
    r"C:\AI-BS\README.md",
    r"C:\AI-BS\recent_history_context.md",
    r"C:\AI-BS\safetrade_operational_guide.md",
    r"C:\AI-BS\SAVED_CHECKPOINT.md",
    r"C:\AI-BS\SECURITY.md",
    r"C:\AI-BS\Stehouwer_LLM_Upgrade_Study_Guide.md",
    r"C:\AI-BS\STEHOUWER_OMNI_CHRONOLOGICAL_MASTER_ARCHIVE.md",
    r"C:\AI-BS\step_2_exchange_setup_guide.md",
    r"C:\AI-BS\task.md",
    r"C:\AI-BS\TEST_INFRA.md",
    r"C:\AI-BS\walkthrough.md",
    r"C:\AI-BS\windows_commands_reference.md",
    r"C:\AI-BS\Brett_Stehouwer_FE_Express_Job_Application.pdf",
    r"C:\AI-BS\gist.githubusercontent.com_dbilanoski_4abb92c00e23686aa29084e123151248_raw_6ad1949e0e72de1c3cadb31b9a783c4f378c19dc_windows11-shell-folders-by-name.csv.pdf",
    r"C:\AI-BS\ma-automation-architect-handbook-ebook-670280-202401-en.pdf",
    r"C:\AI-BS\Stehouwer_Publishing_Robert_Costner_Master_NDA_Agreement.pdf",
    r"C:\AI-BS\TheSimpleChef.pdf",
    r"C:\AI-BS\TheSimpleChef_Invoice_TSC-2026-001.pdf",
    r"C:\AI-BS\audio for vid.mp3",
    r"C:\AI-BS\What Can We Fix Today.mp3",
    r"C:\AI-BS\Silent Mind (Remastered).mp4",
    r"C:\AI-BS\build_trainer_installer.nsi",
    r"C:\AI-BS\yolov8n.pt",
    r"C:\AI-BS\AI_BS_Master_Worker.py",
    r"C:\AI-BS\AI_BS_Swarm_Commander.py",
    r"C:\AI-BS\AI_BS_Vector_Seeder.py",
    r"C:\AI-BS\analyze_brains.py",
    r"C:\AI-BS\archive_ledgers.py",
    r"C:\AI-BS\archive_task.py",
    r"C:\AI-BS\audit_workspace_legacy.py",
    r"C:\AI-BS\BUD.py",
    r"C:\AI-BS\check_chat_inputs.py",
    r"C:\AI-BS\check_chat_inputs2.py",
    r"C:\AI-BS\check_scripts.py",
    r"C:\AI-BS\chia_plot_calculator.py",
    r"C:\AI-BS\copy_artifacts.py",
    r"C:\AI-BS\debug_ktxt.py",
    r"C:\AI-BS\discord_notifier.py",
    r"C:\AI-BS\extract_all_commands.py",
    r"C:\AI-BS\extract_docx.py",
    r"C:\AI-BS\extract_sections.py",
    r"C:\AI-BS\fetch_gospels.py",
    r"C:\AI-BS\fetch_matthew.py",
    r"C:\AI-BS\find_all_slash_commands.py",
    r"C:\AI-BS\find_input_area.py",
    r"C:\AI-BS\find_textarea.py",
    r"C:\AI-BS\fix_port.py",
    r"C:\AI-BS\generate_70_dbs.py",
    r"C:\AI-BS\generate_70_interactive_hubs.py",
    r"C:\AI-BS\generate_70_vector_dbs.py",
    r"C:\AI-BS\generate_functional_utilities.py",
    r"C:\AI-BS\generate_unreal_scripts.py",
    r"C:\AI-BS\live_check.py",
    r"C:\AI-BS\merge_app.py",
    r"C:\AI-BS\nvidia_ctk_wrapper.py",
    r"C:\AI-BS\patch_ktxt.py",
    r"C:\AI-BS\populate_unreal_assets.py",
    r"C:\AI-BS\quick_check_ledger.py",
    r"C:\AI-BS\run_full_scan.py",
    r"C:\AI-BS\run_scan.py",
    r"C:\AI-BS\runc_wrapper.py",
    r"C:\AI-BS\scaffold_high_perf.py",
    r"C:\AI-BS\sitecustomize.py",
    r"C:\AI-BS\test_bundles.py",
    r"C:\AI-BS\test_parse.py",
    r"C:\AI-BS\vast.py",
    r"C:\AI-BS\vast_install.py",
    r"C:\AI-BS\vault_ingest_leadengine.py",
    r"C:\AI-BS\Modelfile.Qwen",
    r"C:\AI-BS\Dockerfile.sandbox",
    r"C:\AI-BS\vastai.service",
    r"C:\AI-BS\clore_install.sh",
    r"C:\AI-BS\dmidecode_mock.sh",
    r"C:\AI-BS\setup_ubuntu_bio.sh",
    r"C:\AI-BS\vast_setup.sh",
    r"C:\AI-BS\Launch_AI_BS - Shortcut.lnk",
    r"C:\AI-BS\AI-BS.spec",
    r"C:\AI-BS\AI-BS_BTD6_Trainer.spec",
    r"C:\AI-BS\AI-BS_Trainer.spec",
    r"C:\AI-BS\brain_backend.spec",
    r"C:\AI-BS\trainer_daemon.spec",
    r"C:\AI-BS\all_unreal_assets.txt",
    r"C:\AI-BS\audit_run.log",
    r"C:\AI-BS\brain_summary.txt",
    r"C:\AI-BS\chromadb_test_log.txt",
    r"C:\AI-BS\debug.txt",
    r"C:\AI-BS\debug2.txt",
    r"C:\AI-BS\devices.txt",
    r"C:\AI-BS\extracted_noco_docs.txt",
    r"C:\AI-BS\hs_err_pid2380.log",
    r"C:\AI-BS\hs_err_pid5496.log",
    r"C:\AI-BS\hs_err_pid10276.log",
    r"C:\AI-BS\hs_err_pid10540.log",
    r"C:\AI-BS\hs_err_pid11260.log",
    r"C:\AI-BS\hs_err_pid11588.log",
    r"C:\AI-BS\hs_err_pid12936.log",
    r"C:\AI-BS\hs_err_pid14356.log",
    r"C:\AI-BS\hs_err_pid15044.log",
    r"C:\AI-BS\hs_err_pid16108.log",
    r"C:\AI-BS\hs_err_pid25012.log",
    r"C:\AI-BS\hs_err_pid27736.log",
    r"C:\AI-BS\hs_err_pid28964.log",
    r"C:\AI-BS\hs_err_pid32396.log",
    r"C:\AI-BS\hs_err_pid34564.log",
    r"C:\AI-BS\hs_err_pid36156.log",
    r"C:\AI-BS\hs_err_pid38084.log",
    r"C:\AI-BS\hs_err_pid39052.log",
    r"C:\AI-BS\hs_err_pid39940.log",
    r"C:\AI-BS\hs_err_pid41352.log",
    r"C:\AI-BS\hs_err_pid41452.log",
    r"C:\AI-BS\hs_err_pid41808.log",
    r"C:\AI-BS\hs_err_pid44432.log",
    r"C:\AI-BS\hs_err_pid45428.log",
    r"C:\AI-BS\kaalia.log",
    r"C:\AI-BS\Notos implication.txt",
    r"C:\AI-BS\QUICK_REFERENCE.txt",
    r"C:\AI-BS\replay_pid2380.log",
    r"C:\AI-BS\replay_pid5496.log",
    r"C:\AI-BS\replay_pid10276.log",
    r"C:\AI-BS\replay_pid10540.log",
    r"C:\AI-BS\replay_pid11260.log",
    r"C:\AI-BS\replay_pid11588.log",
    r"C:\AI-BS\replay_pid12936.log",
    r"C:\AI-BS\replay_pid14356.log",
    r"C:\AI-BS\replay_pid15044.log",
    r"C:\AI-BS\replay_pid16108.log",
    r"C:\AI-BS\replay_pid25012.log",
    r"C:\AI-BS\replay_pid28964.log",
    r"C:\AI-BS\replay_pid32396.log",
    r"C:\AI-BS\replay_pid36156.log",
    r"C:\AI-BS\replay_pid38084.log",
    r"C:\AI-BS\replay_pid39052.log",
    r"C:\AI-BS\replay_pid39940.log",
    r"C:\AI-BS\replay_pid41352.log",
    r"C:\AI-BS\replay_pid41452.log",
    r"C:\AI-BS\replay_pid41808.log",
    r"C:\AI-BS\replay_pid45428.log",
    r"C:\AI-BS\requirements.txt",
    r"C:\AI-BS\saved_test.txt",
    r"C:\AI-BS\scratch_all_commands.txt",
    r"C:\AI-BS\scratch_input_area.txt",
    r"C:\AI-BS\scratch_sections.txt",
    r"C:\AI-BS\scratch_textarea.txt",
    r"C:\AI-BS\scratch_ue_docs.txt",
    r"C:\AI-BS\SQLITE_FIX_SUMMARY.txt",
    r"C:\AI-BS\test_localsystem.txt",
    r"C:\AI-BS\vast_host_install.log",
    r"C:\AI-BS\version.txt",
    r"C:\AI-BS\pyproject.toml",
    r"C:\AI-BS\.gitignore",
    r"C:\AI-BS\Modelfile.unrestricted",
    r"C:\AI-BS\Launch_AI_BS_Silent.vbs",
    r"C:\AI-BS\Launch_Desktop_Studio.vbs",
    r"C:\AI-BS\start_trainer.vbs",
    r"C:\AI-BS\.vercelignore",
    r"C:\AI-BS\mess created split.wav",
    r"C:\AI-BS\Build_and_Open_Mafia_World_UE5.bat",
    r"C:\AI-BS\generate_comfy_image.bat",
    r"C:\AI-BS\Launch_AI_BS.bat",
    r"C:\AI-BS\Launch_AI_BS_Dev.bat",
    r"C:\AI-BS\Launch_BTD6_Electron_Trainer.bat",
    r"C:\AI-BS\Launch_BTD6_Trainer.bat",
    r"C:\AI-BS\Launch_ComfyUI_OnDemand.bat",
    r"C:\AI-BS\Launch_Cymatics_Sniper.bat",
    r"C:\AI-BS\Launch_Desktop_App_Dev.bat",
    r"C:\AI-BS\Launch_Desktop_Studio_Fast.bat",
    r"C:\AI-BS\Launch_Ghost_Demo.bat",
    r"C:\AI-BS\Launch_Mobile_Tunnel.bat",
    r"C:\AI-BS\Launch_Native_Studio.bat",
    r"C:\AI-BS\Launch_OBS_Core.bat",
    r"C:\AI-BS\Launch_Studio_Suite_OnDemand.bat",
    r"C:\AI-BS\Launch_Unified_Stehouwer.bat",
    r"C:\AI-BS\Launch_Unreal_OnDemand.bat",
    r"C:\AI-BS\Launch_YouTube_Live_Stream.bat",
    r"C:\AI-BS\Pause_Clore_For_Gaming.bat",
    r"C:\AI-BS\Play_BTD6_With_Trainer.bat",
    r"C:\AI-BS\push_mobile_update.bat",
    r"C:\AI-BS\Quick_Build_Windows_Exe.bat",
    r"C:\AI-BS\rebuild_frontend.bat",
    r"C:\AI-BS\Restart_Daemon.bat",
    r"C:\AI-BS\Resume_Clore_After_Gaming.bat",
    r"C:\AI-BS\run_ecosystem.deprecated.bat",
    r"C:\AI-BS\Run_Setup_Installer.bat",
    r"C:\AI-BS\Run_Social_Daemon.bat",
    r"C:\AI-BS\run_unrestricted_studio.bat",
    r"C:\AI-BS\Shutdown_AI_BS.bat",
    r"C:\AI-BS\start.deprecated.bat",
    r"C:\AI-BS\Start_Clore_Server.bat",
    r"C:\AI-BS\Start_Crypto_Swarm.bat",
    r"C:\AI-BS\Start_Mobile_Tunnel.bat",
    r"C:\AI-BS\Start_Pearl.bat",
    r"C:\AI-BS\Start_Unified_Watchdog.bat",
    r"C:\AI-BS\Start_Vast_Server.bat",
    r"C:\AI-BS\Stop_Clore_Server.bat",
    r"C:\AI-BS\Stop_Pearl.bat",
    r"C:\AI-BS\Update_And_Run_Windows_Dev.bat",
    r"C:\AI-BS\build_installer.ps1",
    r"C:\AI-BS\create_shortcuts.ps1",
    r"C:\AI-BS\download_missing_flux_redux.ps1",
    r"C:\AI-BS\find_install.ps1",
    r"C:\AI-BS\kill_all.ps1",
    r"C:\AI-BS\kill_duplicates.ps1",
    r"C:\AI-BS\kill_duplicates2.ps1",
    r"C:\AI-BS\list_procs.ps1",
    r"C:\AI-BS\Max_Performance_Mode.ps1",
    r"C:\AI-BS\push_mobile_update.ps1",
    r"C:\AI-BS\scan.ps1",
    r"C:\AI-BS\setup_obs_core.ps1",
    r"C:\AI-BS\setup_obs_websocket.ps1",
    r"C:\AI-BS\update_ledgers.ps1",
    r"C:\AI-BS\verify-mirror-parity.ps1",
    r"C:\AI-BS\config.yml",
    r"C:\AI-BS\docker-compose.sandbox.yml",
    r"C:\AI-BS\docker-compose.yml",
]

BINARY_EXTS = {
    ".exe", ".pdf", ".db", ".zip", ".mp3", ".mp4", ".pt", ".gz", ".jpg", ".lnk", ".wav", ".tar.gz"
}

LANG_MAP = {
    ".py": "python",
    ".json": "json",
    ".md": "markdown",
    ".bat": "batch",
    ".ps1": "powershell",
    ".sh": "bash",
    ".vbs": "vbscript",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".jsx": "jsx",
    ".go": "go",
    ".txt": "text",
    ".log": "text",
    ".csv": "csv",
    ".spec": "python",
    ".nsi": "nsis",
    ".lock": "toml",
    ".service": "ini",
    ".sandbox": "text",
    ".code-workspace": "json",
    ".bak": "text",
    ".hermes": "text",
    ".qwen": "text",
    ".dolphin": "text",
    ".unrestricted": "text",
    ".env": "bash",
    ".agentrules": "markdown",
    ".antigravityrules": "markdown",
    ".dockerignore": "text",
    ".gitignore": "text",
    ".vercelignore": "text",
    "dockerfile": "dockerfile",
    "modelfile": "dockerfile",
    "license": "text",
}


def get_lang(filename: str) -> str:
    lower = filename.lower()
    if lower.startswith("dockerfile"):
        return "dockerfile"
    if lower.startswith("modelfile"):
        return "dockerfile"
    if lower == "license":
        return "text"
    ext = os.path.splitext(lower)[1]
    return LANG_MAP.get(ext, "text")


def hash_file(filepath: str) -> str:
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERR: {e}"


def categorize(filename: str, filepath: str) -> str:
    lower = filename.lower()
    ext = os.path.splitext(lower)[1]

    if ext in BINARY_EXTS:
        return "10. Binary, Media & Database Asset Registry"
    if filename in ("symbol_graph.json", "py_health_audit.json"):
        return "09. Giant Data Dumps (Structural Schema & Sampling)"
    if "native_studio" in filepath.lower() or lower.endswith("_view.py") or lower in ("app.py", "engine.py", "theme.py", "widgets.py", "audio_kernel.py", "telemetry_hub.py", "telemetry_shm.py", "executive_cockpit_full.py", "bs_chat_ide_full.py"):
        return "02. Native Windows Desktop Studio (Direct2D/Win32/PyQt6)"
    if ext == ".py":
        return "03. Backend Core Engines & System Python Scripts"
    if ext in (".bat", ".ps1", ".sh", ".vbs"):
        return "04. Shell, PowerShell & Execution Scripts"
    if lower.startswith("modelfile") or "agentrules" in lower or "antigravityrules" in lower:
        return "05. AI Modelfiles, Agent Directives & Persona Prompts"
    if ext in (".json", ".yml", ".toml", ".spec", ".nsi", ".lock", ".service", ".code-workspace") or lower.startswith("dockerfile"):
        return "06. Configuration, Package Specs & Build Orchestration"
    if ext == ".md":
        return "07. Architectural Ledgers, Handoffs & Documentation"
    if ext in (".log", ".txt", ".csv", ".bak", ".html", ".jsx", ".go"):
        return "08. Telemetry Logs, Historical Artifacts & Web Handlers"
    return "01. Ecosystem Directives & Root Rules"


def main() -> None:
    print(f"[{time.strftime('%H:%M:%S')}] Initializing Master Dossier Compilation...")

    # 1. Gather all files
    files_map: Dict[str, str] = {}

    if os.path.exists(NEW_FOLDER):
        for f in os.listdir(NEW_FOLDER):
            fp = os.path.join(NEW_FOLDER, f)
            if os.path.isfile(fp):
                files_map[f] = fp

    for p in PASTED_FILES:
        if os.path.isfile(p):
            bn = os.path.basename(p)
            if bn not in files_map:
                files_map[bn] = p

    total_files = len(files_map)
    print(f"[{time.strftime('%H:%M:%S')}] Discovered {total_files} unique files.")

    # 2. Categorize
    buckets: Dict[str, List[Tuple[str, str, int]]] = {}
    for bn, fp in sorted(files_map.items()):
        sz = os.path.getsize(fp)
        cat = categorize(bn, fp)
        buckets.setdefault(cat, []).append((bn, fp, sz))

    # 3. Open output file for streaming write
    print(f"[{time.strftime('%H:%M:%S')}] Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8", errors="replace") as out:
        # Title & Meta
        out.write("# AI-BS Sovereign Ecosystem: Unified Master Review & Architectural Dossier\n\n")
        out.write(f"**Target Compiler:** Gemini 4 Argon / Multi-Agent Architectural Review Engine  \n")
        out.write(f"**Compilation Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        out.write(f"**Target Destination:** `{OUTPUT_FILE}`  \n")
        out.write(f"**Total Consolidated Files:** {total_files}  \n")
        total_raw_bytes = sum(sz for files in buckets.values() for _, _, sz in files)
        out.write(f"**Total Source Footprint:** {total_raw_bytes / (1024*1024):.2f} MB ({total_raw_bytes:,} bytes)  \n\n")

        out.write("> [!IMPORTANT]\n")
        out.write("> **Document Scope & Purpose:**\n")
        out.write("> This document is the unified, authoritative consolidation of all source files, scripts, architectural ledgers, and configurations powering the **AI-BS Sovereign Intelligence Ecosystem** and **AI-BS Native Windows Studio**.\n")
        out.write("> Zero browser runtimes, zero local web servers for desktop UI, direct Win32/Direct2D/DirectX rendering, pure in-process `EngineBus` dispatch, and direct SQLite memory-mapped databases.\n\n")
        out.write("---\n\n")

        # Table of Contents
        out.write("## Table of Contents\n\n")
        for cat_name in sorted(buckets.keys()):
            items = buckets[cat_name]
            total_cat_sz = sum(sz for _, _, sz in items) / (1024 * 1024)
            cat_anchor = cat_name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("/", "").replace(",", "")
            out.write(f"### [{cat_name}](#{cat_anchor}) ({len(items)} files — {total_cat_sz:.2f} MB)\n")
            for bn, fp, sz in items:
                file_anchor = "file-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-")
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                out.write(f"- [`{bn}`](#{file_anchor}) ({sz_str})\n")
            out.write("\n")

        out.write("---\n\n")

        # Process each bucket
        for cat_name in sorted(buckets.keys()):
            cat_anchor = cat_name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("/", "").replace(",", "")
            out.write(f"<a id=\"{cat_anchor}\"></a>\n\n")
            out.write(f"# {cat_name}\n\n")

            # Special Handling for Binary Assets
            if "Binary" in cat_name:
                out.write("| File Name | Path | Size | SHA-256 Digest | Operational Role |\n")
                out.write("| :--- | :--- | :--- | :--- | :--- |\n")
                for bn, fp, sz in buckets[cat_name]:
                    sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"
                    sha = hash_file(fp)
                    ext = os.path.splitext(bn)[1].lower()
                    if ext == ".exe":
                        role = "Standalone Windows Binary / Installer"
                    elif ext == ".pdf":
                        role = "Legal Contract / Technical Architecture Document"
                    elif ext == ".db":
                        role = "SQLite Sovereign Database Vault"
                    elif ext == ".zip" or ext == ".gz":
                        role = "Production Bundle / Log Archive"
                    elif ext in (".mp3", ".wav", ".mp4"):
                        role = "Audio/Video Media Production Asset"
                    elif ext == ".pt":
                        role = "PyTorch YOLO Neural Weights"
                    else:
                        role = "Binary Resource Asset"
                    out.write(f"| **`{bn}`** | `{fp}` | {sz_str} | `{sha[:16]}...` | {role} |\n")
                out.write("\n---\n\n")
                continue

            # Special Handling for Giant Data Dumps
            if "Giant Data" in cat_name:
                for bn, fp, sz in buckets[cat_name]:
                    file_anchor = "file-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-")
                    out.write(f"<a id=\"{file_anchor}\"></a>\n\n")
                    out.write(f"## File: `{bn}`\n\n")
                    sz_mb = sz / (1024 * 1024)
                    out.write(f"- **Original Path:** `{fp}`\n")
                    out.write(f"- **Raw Footprint:** {sz_mb:.2f} MB ({sz:,} bytes)\n")
                    out.write(f"- **MIME Type:** `application/json`\n")
                    out.write(f"- **Optimization Status:** Structural Schema & Sampled Inspection (Excludes 240MB+ raw AST to prevent token exhaustion)\n\n")

                    out.write("````json\n")
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as jf:
                            lines_head = []
                            for _ in range(120):
                                line = jf.readline()
                                if not line:
                                    break
                                lines_head.append(line)
                            out.write("".join(lines_head))
                            out.write("\n// ... [REMAINDER OF GIANT DATA GRAPH PRESERVED ON DISK AT ORIGINAL PATH] ...\n")
                    except Exception as ex:
                        out.write(f"// Error reading sample: {ex}\n")
                    out.write("````\n\n---\n\n")
                continue

            # Standard Text & Code Files
            for bn, fp, sz in buckets[cat_name]:
                file_anchor = "file-" + bn.lower().replace(" ", "-").replace(".", "-").replace("(", "").replace(")", "").replace("+", "-")
                lang = get_lang(bn)
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024*1024 else f"{sz / (1024*1024):.2f} MB"

                out.write(f"<a id=\"{file_anchor}\"></a>\n\n")
                out.write(f"## File: `{bn}`\n\n")
                out.write(f"- **Original Path:** `{fp}`\n")
                out.write(f"- **File Size:** {sz_str} ({sz:,} bytes)\n")
                out.write(f"- **Syntax Language:** `{lang}`\n\n")

                out.write(f"````{lang}\n")
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        out.write(content)
                        if not content.endswith("\n"):
                            out.write("\n")
                except Exception as ex:
                    out.write(f"// Error reading file content: {ex}\n")
                out.write("````\n\n---\n\n")

    out_sz = os.path.getsize(OUTPUT_FILE)
    print(f"[{time.strftime('%H:%M:%S')}] Compilation Complete!")
    print(f"[{time.strftime('%H:%M:%S')}] Destination: {OUTPUT_FILE}")
    print(f"[{time.strftime('%H:%M:%S')}] Consolidated Size: {out_sz / (1024*1024):.2f} MB ({out_sz:,} bytes)")


if __name__ == "__main__":
    main()
