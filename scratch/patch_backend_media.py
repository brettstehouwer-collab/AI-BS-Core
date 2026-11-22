import sys

patch = """
from fastapi.responses import FileResponse
from fastapi import HTTPException
import urllib.parse

@app.get("/api/media/serve")
def serve_media(path: str):
    import os
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(r"C:\\AI-BS"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "video/mp4" if abs_path.endswith((".mp4", ".webm")) else "image/png"
    return FileResponse(abs_path, media_type=media_type)

@app.get("/api/media-vault/all")
def get_all_media_vault_items():
    import os
    import urllib.parse
    comfy_out = r"C:\\AI-BS\\ComfyUI\\ComfyUI\\output"
    
    categories = {
        "Commercial Assets": [],
        "UltraHD Renders": [],
        "Cinematic Video": [],
        "Virtual Staging": [],
        "3D & Prototypes": [],
        "LoRA & Workflows": [],
        "Standard Renders": [],
        "Root Workspace Media": []
    }
    
    # 1. ComfyUI Outputs
    if os.path.exists(comfy_out):
        for fname in sorted(os.listdir(comfy_out), reverse=True):
            if not (fname.endswith(".png") or fname.endswith(".mp4") or fname.endswith(".webp") or fname.endswith(".gif")):
                continue
                
            file_path = os.path.join(comfy_out, fname)
            size = os.path.getsize(file_path)
            media_type = "video" if fname.endswith(".mp4") or fname.endswith(".webm") else "image"
            
            item = {
                "filename": fname,
                "url": f"/api/comfy/media?filename={fname}&subfolder=&type=output",
                "type": media_type,
                "size": size
            }
            
            if fname.startswith("AI_BS_COMMERCIAL"):
                categories["Commercial Assets"].append(item)
            elif fname.startswith("AI_BS_UltraHD") or fname.startswith("AI_BS_HD"):
                categories["UltraHD Renders"].append(item)
            elif fname.startswith("WanVideo") or fname.startswith("LTX_Video") or fname.startswith("Wan2_Tour"):
                categories["Cinematic Video"].append(item)
            elif fname.startswith("VirtualStaged"):
                categories["Virtual Staging"].append(item)
            elif fname.startswith("AI_BS_3D_Model"):
                categories["3D & Prototypes"].append(item)
            elif fname.startswith("AI_BS_LoRA") or fname.startswith("AI_BS_Workflow"):
                categories["LoRA & Workflows"].append(item)
            else:
                categories["Standard Renders"].append(item)

    # 2. Root Workspace Media Scan
    root_dir = r"C:\\AI-BS"
    excludes = {
        "node_modules", ".git", ".venv", "venv", ".gemini", 
        "dist", "build", "__pycache__", ".vscode", "python_embeded",
        "Android Studio", "frontend", "backend", "ComfyUI", "Agent_Tasks_History",
        "Agent_Implementation_Plans_History", "Agent_Handoff_Summaries", "docs",
        "apps", "saved_data", "logs"
    }
    media_extensions = {".png", ".mp4", ".webp", ".gif", ".jpg", ".jpeg"}
    
    root_media = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith('.')]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in media_extensions:
                file_path = os.path.join(dirpath, f)
                try:
                    size = os.path.getsize(file_path)
                    media_type = "video" if ext in {".mp4", ".webm"} else "image"
                    # We can use /api/media/serve to serve the file
                    encoded_path = urllib.parse.quote(file_path)
                    item = {
                        "filename": f,
                        "url": f"/api/media/serve?path={encoded_path}",
                        "type": media_type,
                        "size": size
                    }
                    root_media.append(item)
                except Exception:
                    pass
    
    # Sort root media alphabetically by filename and add to category
    root_media.sort(key=lambda x: x["filename"])
    categories["Root Workspace Media"].extend(root_media)
            
    # Format for response
    result = []
    for cat_name, items in categories.items():
        if len(items) > 0:
            result.append({
                "name": cat_name,
                "files": items
            })
            
    return {"categories": result}
"""

with open(r"C:\AI-BS\backend\AI_BS_Backend.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the start of the get_all_media_vault_items function
import re
pattern = re.compile(r'@app\.get\("/api/media-vault/all"\)\ndef get_all_media_vault_items\(\):.*?\n    return {"categories": result}\n', re.DOTALL)
new_content = pattern.sub(patch.strip() + "\n", content)

with open(r"C:\AI-BS\backend\AI_BS_Backend.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Backend patched.")
