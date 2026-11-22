import datetime
import os

timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 1. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
with open(ledger_path, 'a') as f:
    f.write(f"\n\n### [{timestamp}] ComfyUI Port Migration & GPU Miner Isolation\n")
    f.write("**AI Rationale & Changes:**\n")
    f.write("- **Issue:** The AI-BS image generator was failing with `{\"msg\": \"Media request intercepted by an admin routed to ComfyUI.\", \"status\": \"no_proxy_active\"}`. This occurred because the Clore.ai/Vast.ai GPU mining containers were intercepting traffic on ComfyUI's default port (8188).\n")
    f.write("- **Solution:** Migrated ComfyUI and all ecosystem references (AI_BS_Backend.py, gateway_router.py, tool_registry.py, comfy_bridge.py, Launch_AI_BS.bat, run_nvidia_gpu.bat) to use port **8189** instead of 8188.\n")
    f.write("- **Result:** Complete decoupling of local ComfyUI generation from GPU rented container networking bridges.\n")

# 2. Update AI_BS_MASTER_ECOSYSTEM_MANUAL.md
manual_path = r"C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md"
if os.path.exists(manual_path):
    with open(manual_path, 'r') as f:
        content = f.read()
    
    # Bump version
    import re
    def bump_version(match):
        major, minor, patch = map(int, match.group(1).split('.'))
        return f"Version: {major}.{minor + 1}.{patch}"
    
    content = re.sub(r'Version:\s*(\d+\.\d+\.\d+)', bump_version, content)
    
    # Add port spec
    content += f"\n\n### Updated Port Allocations (as of {timestamp})\n"
    content += "- **ComfyUI Renderer:** Port 8189 (Changed from 8188 to prevent Vast.ai/Clore.ai container collisions)\n"
    
    with open(manual_path, 'w') as f:
        f.write(content)

# 3. Create Desktop Folder was already done via PowerShell.

print("Documentation updated successfully.")
