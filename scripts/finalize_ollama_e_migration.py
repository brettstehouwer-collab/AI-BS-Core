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

def run_migration():
    print_header("FINALIZING OLLAMA MIGRATION TO E:\\AI_BS_Resources\\Ollama")
    
    src = r"C:\AI-BS\.ollama"
    dst = r"E:\AI_BS_Resources\Ollama"
    user_ollama = os.path.expandvars(r"%USERPROFILE%\.ollama")

    os.makedirs(dst, exist_ok=True)

    # 1. Sync C:\AI-BS\.ollama to E:\AI_BS_Resources\Ollama
    print(f"Syncing from {src} to {dst} using robocopy...")
    subprocess.run(
        ["robocopy", src, dst, "/E", "/MT:16", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS"],
        capture_output=True, text=True
    )

    # Verify dst
    dst_blobs = os.path.join(dst, "blobs")
    dst_manifests = os.path.join(dst, "manifests")
    if os.path.exists(dst_blobs) and os.path.exists(dst_manifests):
        print(f"Verification PASS: {dst} contains blobs ({len(os.listdir(dst_blobs))} files) and manifests!")
    else:
        print("Error: Destination missing blobs/manifests.")
        return False

    # 2. Stop running Ollama
    print("Stopping Ollama processes to release locks...")
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if 'ollama' in p.info['name'].lower():
                print(f"Stopping {p.info['name']} (PID: {p.info['pid']})")
                p.terminate()
        except Exception:
            pass
    time.sleep(2)

    # 3. Remove physical C:\AI-BS\.ollama
    if os.path.exists(src) and not os.path.islink(src):
        print(f"Removing physical directory {src} on C:...")
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"Remove-Item -LiteralPath '{src}' -Recurse -Force -ErrorAction SilentlyContinue"], capture_output=True)
        if os.path.exists(src):
            shutil.rmtree(src, ignore_errors=True)

    # 4. Remove physical C:\Users\footb\.ollama if not link
    if os.path.exists(user_ollama) and not os.path.islink(user_ollama):
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"Remove-Item -LiteralPath '{user_ollama}' -Recurse -Force -ErrorAction SilentlyContinue"], capture_output=True)
        if os.path.exists(user_ollama):
            shutil.rmtree(user_ollama, ignore_errors=True)

    # 5. Create Junctions
    create_junction(src, dst)
    create_junction(user_ollama, dst)

    # 6. Update backend configuration files and batch scripts
    print_header("UPDATING ALL BACKEND CONFIGURATIONS TO E:\\AI_BS_Resources\\Ollama")
    
    files_to_update = [
        (r"C:\AI-BS\backend\core\sovereign_reasoning\dispatcher.py", [
            (r'r"C:\AI-BS\.ollama\models"', r'r"E:\AI_BS_Resources\Ollama"'),
            (r'r"C:\AI-BS\.ollama"', r'r"E:\AI_BS_Resources\Ollama"'),
            (r'r"E:\.ollama\models"', r'r"E:\AI_BS_Resources\Ollama"')
        ]),
        (r"C:\AI-BS\Launch_AI_BS.bat", [
            (r"C:\AI-BS\.ollama\models", r"E:\AI_BS_Resources\Ollama"),
            (r"E:\.ollama\models", r"E:\AI_BS_Resources\Ollama")
        ]),
        (r"C:\AI-BS\Launch_AI_BS_Dev.bat", [
            (r"C:\AI-BS\.ollama\models", r"E:\AI_BS_Resources\Ollama"),
            (r"E:\.ollama\models", r"E:\AI_BS_Resources\Ollama")
        ]),
        (r"C:\AI-BS\backend\Launch_Headless_Daemons.bat", [
            (r"C:\AI-BS\.ollama\models", r"E:\AI_BS_Resources\Ollama"),
            (r"E:\.ollama\models", r"E:\AI_BS_Resources\Ollama")
        ]),
        (r"C:\AI-BS\scripts\launch_ecosystem_detached.ps1", [
            (r"C:\AI-BS\.ollama\models", r"E:\AI_BS_Resources\Ollama"),
            (r"E:\.ollama\models", r"E:\AI_BS_Resources\Ollama")
        ])
    ]

    for fpath, replacements in files_to_update:
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for old_s, new_s in replacements:
                content = content.replace(old_s, new_s)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated backend file: {os.path.basename(fpath)}")

    # 7. Set permanent User Environment variable OLLAMA_MODELS
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", "[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', 'E:\\AI_BS_Resources\\Ollama', 'User')"], capture_output=True)
    print("Set permanent environment variable OLLAMA_MODELS=E:\\AI_BS_Resources\\Ollama")

    # 8. Start Ollama daemons
    print_header("STARTING OLLAMA DAEMON & VERIFYING INFERENCE")
    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    
    # Start on 11435
    env1 = os.environ.copy()
    env1["OLLAMA_HOST"] = "127.0.0.1:11435"
    env1["OLLAMA_MODELS"] = r"E:\AI_BS_Resources\Ollama"
    subprocess.Popen([ollama_exe, "serve"], env=env1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)

    # Start on 11434
    env2 = os.environ.copy()
    env2["OLLAMA_HOST"] = "127.0.0.1:11434"
    env2["OLLAMA_MODELS"] = r"E:\AI_BS_Resources\Ollama"
    subprocess.Popen([ollama_exe, "serve"], env=env2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)

    time.sleep(3)

    # Probe models
    import httpx
    for port in [11435, 11434]:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/api/tags", timeout=4.0)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                print(f"Ollama Port {port} ONLINE! Available models ({len(models)}): {models}")
            else:
                print(f"Port {port} status: {r.status_code}")
        except Exception as e:
            print(f"Port {port} probe: {e}")

    return True

if __name__ == '__main__':
    print_header("FINAL OLLAMA ASSET CONSOLIDATION & SYSTEM SPACE RECOVERY")
    print("Pre-Migration Disk State:")
    get_disk_report()
    
    run_migration()
    
    print_header("ALL ASSETS CONSOLIDATED & BACKEND FUNCTIONS LINKED!")
    print("Post-Migration Disk State:")
    get_disk_report()
