import os
import sys
import json
from pathlib import Path

root = Path(r"C:\AI-BS")

# Paths listed by user
input_paths = [
    r"C:\AI-BS\aria2-1.37.0-win-64bit-build1",
    r"C:\AI-BS\zmomreasarch",
    r"C:\AI-BS\streams",
    r"C:\AI-BS\uploads",
    r"C:\AI-BS\Agent Vector Memory",
    r"C:\AI-BS\genkit_server",
    r"C:\AI-BS\summaries",
    r"C:\AI-BS\AI-BS_Module_Video_Editing",
    r"C:\AI-BS\downloads_archive",
    r"C:\AI-BS\AI_History_BS",
    r"C:\AI-BS\Buissnessuit",
    r"C:\AI-BS\New folder",
    r"C:\AI-BS\NoCo Vision",
    r"C:\AI-BS\Heuristics",
    r"C:\AI-BS\VRAM_Tensor_Swap",
    r"C:\AI-BS\Context_Memory_Swap",
    r"C:\AI-BS\cloudflare-agent",
    r"C:\AI-BS\AI-BS_Modual_Video_Editing",
    r"C:\AI-BS\vast_logs",
    r"C:\AI-BS\MASTER_KNOWLEDGE_VAULT",
    r"C:\AI-BS\.ide_audit_logs",
    r"C:\AI-BS\AI-BS_Knowledge_Vaults",
    r"C:\AI-BS\Gemini_Takeout_Data",
    r"C:\AI-BS\Gemini_Takeout_Dataparrent",
    r"C:\AI-BS\go_telemetry_gateway",
    r"C:\AI-BS\rust_master_worker",
    r"C:\AI-BS\ScreenShots",
    r"C:\AI-BS\AI-BS-Models",
    r"C:\AI-BS\ComfyUI",
    r"C:\AI-BS\antigravity-sdk-python",
    r"C:\AI-BS\Workflows for comfy ui",
    r"C:\AI-BS\PrestigeMobileWash",
    r"C:\AI-BS\self_hosted_supabase",
    r"C:\AI-BS\schemas",
    r"C:\AI-BS\Archive_Legacy",
    r"C:\AI-BS\JuliesPlace",
    r"C:\AI-BS\workflows",
    r"C:\AI-BS\work help",
    r"C:\AI-BS\inference_unbounded",
    r"C:\AI-BS\Audio Downloads",
    r"C:\AI-BS\tools",
    r"C:\AI-BS\pearl",
    r"C:\AI-BS\apps",
    r"C:\AI-BS\custome pythons builds",
    r"C:\AI-BS\game_trainer",
    r"C:\AI-BS\trainer_frontend",
    r"C:\AI-BS\skills",
    r"C:\AI-BS\obs-core",
    r"C:\AI-BS\MP4 medial screen recordings-video",
    r"C:\AI-BS\mobile-app",
    r"C:\AI-BS\sandbox_scratch",
    r"C:\AI-BS\datasets",
    r"C:\AI-BS\pipelines",
    r"C:\AI-BS\_archive_v1",
    r"C:\AI-BS\music",
    r"C:\AI-BS\brain",
    r"C:\AI-BS\FacebookData",
    r"C:\AI-BS\Agents",
    r"C:\AI-BS\Agent_Implementation_Plans_History",
    r"C:\AI-BS\Agent_Handoff_Summaries",
    r"C:\AI-BS\sandbox",
    r"C:\AI-BS\Agent_Tasks_History",
    r"C:\AI-BS\directives",
    r"C:\AI-BS\security",
    r"C:\AI-BS\Stehouwer_Server",
    r"C:\AI-BS\AI-BS_Master_Memory",
    r"C:\AI-BS\unreal_assets",
    r"C:\AI-BS\xbox_dev",
    r"C:\AI-BS\blobs",
    r"C:\AI-BS\models",
    r"C:\AI-BS\backup_startup",
    r"C:\AI-BS\shared_cloud_drive",
    r"C:\AI-BS\screenplay_archive",
    r"C:\AI-BS\manifests",
    r"C:\AI-BS\manifests-v2",
    r"C:\AI-BS\isolated_workers",
    r"C:\AI-BS\snapshots",
    r"C:\AI-BS\learning",
    r"C:\AI-BS\NotebookLM_Records",
    r"C:\AI-BS\recordings",
    r"C:\AI-BS\October7_VocalStudio_DAW",
    r"C:\AI-BS\releases",
    r"C:\AI-BS\ui_modernization",
    r"C:\AI-BS\ScreenVideoSnipping",
    r"C:\AI-BS\workspace",
    r"C:\AI-BS\ai_model_checkpoints",
    r"C:\AI-BS\trade",
    r"C:\AI-BS\data",
    r"C:\AI-BS\UnrealHub",
    r"C:\AI-BS\screenplay_projects",
    r"C:\AI-BS\miners",
    r"C:\AI-BS\pc_check",
    r"C:\AI-BS\asset_library",
    r"C:\AI-BS\synced_drive_assets",
    r"C:\AI-BS\chroma_db_8002",
    r"C:\AI-BS\distributed_training",
    r"C:\AI-BS\engine",
    r"C:\AI-BS\logs",
    r"C:\AI-BS\docs",
    r"C:\AI-BS\chroma_db",
    r"C:\AI-BS\runtime",
    r"C:\AI-BS\go-core",
    r"C:\AI-BS\native_studio",
    r"C:\AI-BS\work",
    r"C:\AI-BS\output",
    r"C:\AI-BS\BroadcastStudioApp",
    r"C:\AI-BS\backups",
    r"C:\AI-BS\scratch",
    r"C:\AI-BS\config",
    r"C:\AI-BS\tests",
    r"C:\AI-BS\Crypto-Swarm",
    r"C:\AI-BS\stehouwer_vector_memory",
    r"C:\AI-BS\database",
    r"C:\AI-BS\backend",
    r"C:\AI-BS\frontend",
    r"C:\AI-BS\scripts",
    r"C:\AI-BS\saved_data",
    r"C:\AI-BS\tts_output",
    r"C:\AI-BS\llm_training_data",
    r"C:\AI-BS\assets"
]

results = {
    "active_in_backend": [],
    "active_in_frontend": [],
    "dormant_high_value": [],
    "data_vaults_and_archives": [],
    "legacy_backups_or_scratch": []
}

# Scan backend text for references to these folders
backend_text = ""
for py in (root / "backend").glob("*.py"):
    try:
        backend_text += py.read_text(encoding="utf-8", errors="ignore") + "\n"
    except:
        pass

# Scan frontend files for references
frontend_text = ""
for ext in ["*.jsx", "*.js", "*.tsx", "*.ts"]:
    for f in (root / "frontend" / "src").glob(ext):
        try:
            frontend_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"
        except:
            pass

for p_str in input_paths:
    p = Path(p_str)
    name = p.name
    exists = p.exists()
    
    in_backend = (name.lower() in backend_text.lower())
    in_frontend = (name.lower() in frontend_text.lower())
    
    # Categorize
    item_info = {
        "name": name,
        "path": p_str,
        "exists": exists,
        "is_dir": p.is_dir() if exists else False,
        "in_backend": in_backend,
        "in_frontend": in_frontend
    }
    
    if in_backend or in_frontend:
        if in_backend:
            results["active_in_backend"].append(item_info)
        if in_frontend:
            results["active_frontend" if "active_frontend" in results else "active_in_frontend"].append(item_info)
    else:
        # High value candidates that can be safely wired without breaking anything
        if any(keyword in name.lower() for keyword in ["screenplay", "audio", "video", "unreal", "comfy", "vector", "memory", "training", "vault", "pearl", "game_trainer"]):
            results["dormant_high_value"].append(item_info)
        elif any(keyword in name.lower() for keyword in ["takeout", "facebook", "archive", "logs", "snapshots", "records"]):
            results["data_vaults_and_archives"].append(item_info)
        else:
            results["legacy_backups_or_scratch"].append(item_info)

out_file = Path(r"C:\AI-BS\saved_data\audit_folder_check.json")
out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("Analysis complete. Saved to", out_file)
print("Active backend count:", len(results["active_in_backend"]))
print("Active frontend count:", len(results["active_in_frontend"]))
print("Dormant high-value assets:", len(results["dormant_high_value"]))
print("Data vaults & archives:", len(results["data_vaults_and_archives"]))

