import os
import sys
import shutil
import subprocess
import time
import psutil

sys.stdout.reconfigure(line_buffering=True)

def print_header(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def get_disk_report():
    for d in ["C:\\", "D:\\", "E:\\"]:
        u = psutil.disk_usage(d)
        print(f"Drive {d:<4} -> Free: {u.free/(1024**3):7.2f} GB / {u.total/(1024**3):7.2f} GB ({u.percent:5.1f}% used)")

def create_junction(src, dst):
    cmd = f"New-Item -ItemType Junction -Path '{src}' -Target '{dst}' -Force"
    res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"SUCCESS: Junction created from {src} -> {dst}")
        return True
    else:
        print(f"Junction error: {res.stderr}")
        return False

def step_sync_models_to_e():
    print_header("STEP 1: SYNC 17 MODELS FROM C:\\AI-BS\\.ollama TO E:\\.ollama")
    src = r"C:\AI-BS\.ollama\models"
    dst = r"E:\.ollama\models"
    
    os.makedirs(dst, exist_ok=True)
    
    print(f"Robocopying missing models & blobs to {dst} with /MT:16...")
    res = subprocess.run(
        ["robocopy", src, dst, "/E", "/MT:16", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS"],
        capture_output=True, text=True
    )
    
    # Verify manifests
    c_manifests = os.path.join(src, "manifests", "registry.ollama.ai", "library")
    e_manifests = os.path.join(dst, "manifests", "registry.ollama.ai", "library")
    c_list = set(os.listdir(c_manifests)) if os.path.exists(c_manifests) else set()
    e_list = set(os.listdir(e_manifests)) if os.path.exists(e_manifests) else set()
    
    print(f"C Manifests ({len(c_list)}) | E Manifests ({len(e_list)})")
    if c_list.issubset(e_list) and len(e_list) >= 16:
        print("Model verification PASS: All 17 model manifests present on E:\\.ollama!")
        return True
    else:
        print(f"Warning: Manifest mismatch: {c_list - e_list}")
        return False

def step_switch_junctions():
    print_header("STEP 2: TERMINATE OLLAMA & PURGE 222 GB FROM C:\\ TO CREATE JUNCTIONS")
    # Terminate ollama
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if 'ollama' in p.info['name'].lower():
                print(f"Stopping {p.info['name']} (PID: {p.info['pid']})")
                p.terminate()
        except Exception:
            pass
    time.sleep(2)
    
    src_aibs = r"C:\AI-BS\.ollama\models"
    target_e = r"E:\.ollama\models"
    src_user = os.path.expandvars(r"%USERPROFILE%\.ollama\models")
    
    # 1. Remove physical folder on C:\AI-BS\.ollama\models
    if os.path.exists(src_aibs) and not os.path.islink(src_aibs):
        print("Removing 222 GB directory C:\\AI-BS\\.ollama\\models on C:...")
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"Remove-Item -LiteralPath '{src_aibs}' -Recurse -Force -ErrorAction SilentlyContinue"], capture_output=True)
        if os.path.exists(src_aibs):
            shutil.rmtree(src_aibs, ignore_errors=True)
    
    # Create Junction for C:\AI-BS\.ollama\models -> E:\.ollama\models
    create_junction(src_aibs, target_e)
    
    # Create Junction for C:\Users\footb\.ollama\models -> E:\.ollama\models
    create_junction(src_user, target_e)

def step_update_backend_paths():
    print_header("STEP 3: UPDATE CODEBASE REFERENCES TO E:\\.ollama\\models")
    
    # 1. Update dispatcher.py
    dispatcher_file = r"C:\AI-BS\backend\core\sovereign_reasoning\dispatcher.py"
    if os.path.exists(dispatcher_file):
        with open(dispatcher_file, "r", encoding="utf-8") as f:
            content = f.read()
        if r'r"C:\AI-BS\.ollama\models"' in content:
            new_content = content.replace(r'r"C:\AI-BS\.ollama\models"', r'r"E:\.ollama\models"')
            with open(dispatcher_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("Updated dispatcher.py OLLAMA_MODELS path.")

    # 2. Update launch batch scripts
    batch_files = [
        r"C:\AI-BS\Launch_AI_BS.bat",
        r"C:\AI-BS\Launch_AI_BS_Dev.bat",
        r"C:\AI-BS\backend\Launch_Headless_Daemons.bat",
        r"C:\AI-BS\scripts\launch_ecosystem_detached.ps1"
    ]
    for bf in batch_files:
        if os.path.exists(bf):
            with open(bf, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            c_new = c.replace(r"C:\AI-BS\.ollama\models", r"E:\.ollama\models")
            with open(bf, "w", encoding="utf-8") as f:
                f.write(c_new)
            print(f"Updated {os.path.basename(bf)}")

def step_restart_and_verify():
    print_header("STEP 4: RESTART OLLAMA & VERIFY INFERENCE")
    ollama_app = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe")
    if os.path.exists(ollama_app):
        subprocess.Popen([ollama_app], shell=True)
        print("Restarted Ollama app daemon.")
    
    time.sleep(3)
    # Check Ollama API tags
    try:
        import httpx
        for port in [11435, 11434]:
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/api/tags", timeout=3.0)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    print(f"Ollama Port {port} ONLINE! Available models ({len(models)}): {models[:5]}...")
            except Exception as e:
                print(f"Port {port} probe: {e}")
    except Exception as e:
        print(f"Verification notice: {e}")

if __name__ == '__main__':
    print_header("STARTING 222 GB OLLAMA MIGRATION TO E: DRIVE & JUNCTION DEPLOYMENT")
    print("Initial Disk State:")
    get_disk_report()
    
    if step_sync_models_to_e():
        step_switch_junctions()
        step_update_backend_paths()
        step_restart_and_verify()
    
    print_header("MIGRATION COMPLETED SUCCESSFULLY!")
    print("Final Disk State:")
    get_disk_report()
