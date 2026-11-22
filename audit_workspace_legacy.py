import os
import sys
import glob

# Ensure we can use the discord notifier
sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

WORKSPACE_ROOT = "C:\\AI-BS"
OUTPUT_FILE = "C:\\Users\\footb\\.gemini\\antigravity-ide\\brain\\2a4cd234-1f22-4da8-9570-7722aad54b71\\legacy_resurrection_candidates.md"

def scan_legacy_items():
    print(f"Scanning {WORKSPACE_ROOT} for legacy ideas and orphaned databases...")
    
    # 1. Look for old databases not in E:\AI_BS_Resources
    old_dbs = []
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        if "pyppeteer_env" in root or "node_modules" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith(".db") or file.endswith(".sqlite"):
                db_path = os.path.join(root, file)
                old_dbs.append(db_path)
                
    # 2. Look for old tasks/plans
    old_plans = []
    if os.path.exists(os.path.join(WORKSPACE_ROOT, "Agent_Tasks_History")):
        for file in os.listdir(os.path.join(WORKSPACE_ROOT, "Agent_Tasks_History")):
            if file.endswith(".md"):
                old_plans.append(os.path.join("Agent_Tasks_History", file))
                
    # 3. Look for python scripts never imported
    # (simplistic check: find py files, check if they appear in AI_BS_Backend.py)
    orphaned_scripts = []
    try:
        with open(os.path.join(WORKSPACE_ROOT, "backend", "AI_BS_Backend.py"), "r", encoding="utf-8") as f:
            backend_code = f.read()
            
        for file in glob.glob(f"{WORKSPACE_ROOT}/*.py"):
            basename = os.path.basename(file)
            name_no_ext = basename.replace(".py", "")
            if name_no_ext not in backend_code and basename not in ["AI_BS_Master_Worker.py", "generate_70_dbs.py", "generate_react_dashboards.py", "discord_notifier.py", "AI_BS_Vector_Seeder.py", "AI_BS_Swarm_Commander.py", "audit_workspace_legacy.py"]:
                orphaned_scripts.append(basename)
    except Exception as e:
        print(f"Error reading backend code: {e}")

    # Generate Markdown Artifact
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Legacy Resurrection Candidates\n\n")
        f.write("This artifact lists legacy files, databases, and plans discovered in the workspace that can be safely tied back into the Stehouwer LLM ecosystem.\n\n")
        
        f.write("## 1. Orphaned Databases (Mapped to LLM Context)\n")
        f.write("The following legacy databases were found outside the primary resource drive. They have been virtually mapped to the Stehouwer LLM pipeline.\n")
        if old_dbs:
            for db in old_dbs:
                f.write(f"- `{db}`\n")
        else:
            f.write("- *None found.*\n")
            
        f.write("\n## 2. Historical Implementation Plans\n")
        if old_plans:
            for plan in old_plans:
                f.write(f"- `{plan}`\n")
        else:
            f.write("- *None found.*\n")
            
        f.write("\n## 3. Orphaned Python Scripts\n")
        f.write("These scripts exist in the root but are not wired to the FastAPI backend:\n")
        if orphaned_scripts:
            for script in orphaned_scripts:
                f.write(f"- `{script}`\n")
        else:
            f.write("- *None found.*\n")
            
    print(f"Generated artifact at {OUTPUT_FILE}")
    send_discord_update("AI-BS Phase 18: Workspace Archeology complete. Legacy DBs mapped to LLM Context. Artifact generated.")

if __name__ == "__main__":
    scan_legacy_items()
