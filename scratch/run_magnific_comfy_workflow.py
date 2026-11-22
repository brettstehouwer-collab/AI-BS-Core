import json
import os
import socket
import urllib.request
import urllib.parse
from pathlib import Path

# Prevent urllib socket connect hang on offline Windows ports
socket.setdefaulttimeout(1.0)

def run_magnific_free_workflow(
    input_image_path="C:/AI-BS/output/imagegen/max_detail_step1.png",
    workflow_json_path="C:/AI-BS/backend/comfyui_workflows/magnific_free_upscale_workflow.json",
    comfyui_url="http://127.0.0.1:8188"
):
    print("============================================================")
    print("MAGNIFIC AI UPSCALING (FREE COMFYUI WORKFLOW INTEGRATION)")
    print(f"Video Source Reference: _jO2MPrMiyA (Magnific Upscaling but Free)")
    print("============================================================")
    
    # 1. Load workflow definition
    if not os.path.exists(workflow_json_path):
        print(f"[Error] Workflow JSON missing at: {workflow_json_path}")
        return
        
    with open(workflow_json_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
        
    print(f"[Workflow Loader] Successfully loaded workflow schema from:")
    print(f" -> {workflow_json_path}")
    print(f"[Workflow Topology] Configured Nodes:")
    for node_id, node_data in workflow.items():
        title = node_data.get("_meta", {}).get("title", node_data.get("class_type"))
        print(f"  - Node {node_id}: {title} [{node_data.get('class_type')}]")

    # Check connection to local ComfyUI instance (testing 8188 and 8189)
    connected_port = None
    for port in [8188, 8189]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                url = f"http://127.0.0.1:{port}"
                req = urllib.request.Request(f"{url}/system_stats")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    stats = json.loads(resp.read().decode("utf-8"))
                    print(f"[ComfyUI Bridge] Status: ONLINE at {url}")
                    vram_free = stats.get("devices", [{}])[0].get("vram_free", 0) / (1024**3)
                    print(f" -> Hardware VRAM Free: {vram_free:.2f} GB")
                    connected_port = port
                    break
        except Exception:
            pass

    if connected_port:
        url = f"http://127.0.0.1:{connected_port}/prompt"
        print(f"\n[Submitting Workflow Payload to {url}]...")
        payload = json.dumps({"prompt": workflow}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                prompt_id = res.get("prompt_id")
                print(f" -> SUCCESS: Workflow queued successfully!")
                print(f" -> Prompt ID: {prompt_id}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            print(f" -> Submission Error ({e.code}): {err_body}")
        except Exception as e:
            print(f" -> Submission Error: {e}")
    else:
        print("[ComfyUI Bridge] Status: OFFLINE on ports 8188 & 8189")
        print("\n [Correct Launch Instructions]")
        print("   cd C:\\AI-BS\\ComfyUI")
        print("   python_embeded\\python.exe -s ComfyUI\\main.py --windows-standalone-build --port 8188")
        print("   OR double-click: C:\\AI-BS\\ComfyUI\\run_nvidia_gpu.bat")

    print("\n[Workflow Summary]")
    print("1. ControlNet Tile Anchorage: Locks macro-geometry (strength 0.85).")
    print("2. Model Upscaling Pass: 4x-UltraSharp super-resolution enhancement.")
    print("3. Tiled VAE Latent Buffer: Bypasses VRAM OOM during gigapixel decode.")
    print("4. Denoise Coefficient Stratification: Fixed at 0.25 (Magnific Sweet Spot).")
    print("============================================================")

if __name__ == "__main__":
    run_magnific_free_workflow()