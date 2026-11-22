import os
import glob

search_dir = r"C:\AI-BS"
extensions = ['.py', '.bat']

def replace_port(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    if "8188" in content:
        # Replace only specifically the ComfyUI port context
        # In python files: 127.0.0.1:8189 -> 127.0.0.1:8189
        # In Launch_AI_BS.bat: 8188 -> 8189
        new_content = content.replace("127.0.0.1:8189", "127.0.0.1:8189")
        new_content = new_content.replace("Port 8189", "Port 8189")
        new_content = new_content.replace("8188 \"ComfyUI", "8189 \"ComfyUI")
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_path}")

for root, dirs, files in os.walk(search_dir):
    if "node_modules" in root or ".git" in root or "venv" in root:
        continue
    for file in files:
        if any(file.endswith(ext) for ext in extensions):
            replace_port(os.path.join(root, file))

# Update ComfyUI run script to bind to 8189
comfy_run_script = r"C:\AI-BS\ComfyUI\run_nvidia_gpu.bat"
if os.path.exists(comfy_run_script):
    with open(comfy_run_script, 'r') as f:
        content = f.read()
    if "--port 8189" not in content:
        content = content.replace("main.py --windows-standalone-build", "main.py --windows-standalone-build --port 8189")
        with open(comfy_run_script, 'w') as f:
            f.write(content)
        print("Updated ComfyUI run script")
