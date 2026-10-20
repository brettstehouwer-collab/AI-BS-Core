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

def get_c_free_space():
    u = psutil.disk_usage("C:\\")
    return u.free / (1024**3), u.total / (1024**3), u.percent

def create_junction_powershell(src, dst):
    cmd = f"New-Item -ItemType Junction -Path '{src}' -Target '{dst}' -Force"
    res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"SUCCESS: Junction created from {src} -> {dst}")
        return True
    else:
        print(f"Junction error: {res.stderr}")
        return False

def step_relocate_ollama_models():
    print_header("STEP 4: RELOCATE OLLAMA MODELS TO D:\\ollama_models")
    src = os.path.expandvars(r"%USERPROFILE%\.ollama\models")
    dst = r"D:\ollama_models"

    if not os.path.exists(src):
        print(f"No Ollama models found at {src}.")
        return

    # Check if already a link/junction
    if os.path.islink(src):
        print(f"Source {src} is already a junction/symlink.")
        return

    src_size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(src) for f in files)
    print(f"Source size: {src_size / (1024**3):.2f} GB")

    os.makedirs(dst, exist_ok=True)
    print(f"Copying models to {dst} using robocopy /MT:16 (56 GB)...")
    
    robocopy_cmd = ["robocopy", src, dst, "/E", "/MT:16", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS"]
    res = subprocess.run(robocopy_cmd, capture_output=True, text=True)

    dst_size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(dst) for f in files)
    print(f"Destination size: {dst_size / (1024**3):.2f} GB")

    if dst_size >= src_size * 0.99:
        print("Copy verified. Stopping Ollama processes to release file locks...")
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if 'ollama' in p.info['name'].lower():
                    print(f"Terminating {p.info['name']} (PID: {p.info['pid']})")
                    p.terminate()
            except Exception:
                pass
        time.sleep(2)
        
        print("Removing source directory on C:...")
        shutil.rmtree(src, ignore_errors=True)
        if not os.path.exists(src):
            create_junction_powershell(src, dst)
        else:
            # Force remove with powershell Remove-Item
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"Remove-Item -LiteralPath '{src}' -Recurse -Force -ErrorAction SilentlyContinue"], capture_output=True)
            if not os.path.exists(src):
                create_junction_powershell(src, dst)
            else:
                print("Warning: Could not completely remove src folder.")

        # Restart Ollama app if installed
        ollama_app = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe")
        if os.path.exists(ollama_app):
            subprocess.Popen([ollama_app], shell=True)
            print("Restarted Ollama app.")
    else:
        print("Error: Destination size did not match source size. Aborting deletion.")

if __name__ == '__main__':
    free_start, total, pct_start = get_c_free_space()
    print_header("STARTING OLLAMA MODELS MIGRATION")
    print(f"Current C: Free Space: {free_start:.2f} GB / {total:.2f} GB ({pct_start:.1f}% used)")

    step_relocate_ollama_models()

    free_end, _, pct_end = get_c_free_space()
    print_header("OLLAMA MIGRATION COMPLETE!")
    print(f"Initial C: Free Space : {free_start:7.2f} GB")
    print(f"Final C: Free Space   : {free_end:7.2f} GB")
    print(f"Total Space Liberated : {free_end - free_start:7.2f} GB")
    print(f"Current Usage on C:   : {pct_end:5.1f}%")
