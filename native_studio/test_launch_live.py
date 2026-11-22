import subprocess
import time
import os

python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
app_py = r"C:\AI-BS\native_studio\app.py"
env = os.environ.copy()
env["PYTHONPATH"] = r"C:\AI-BS;C:\AI-BS\native_studio;C:\AI-BS\backend"

proc = subprocess.Popen([python_exe, app_py], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
stdout, stderr = proc.communicate(timeout=15)
print("Exit code:", proc.returncode)
print("STDOUT:", stdout)
print("STDERR:", stderr)
