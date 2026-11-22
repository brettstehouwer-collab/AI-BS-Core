import os
import subprocess
import sys

os.chdir(r"C:\AI-BS\native_studio")
python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
cmd = [python_exe, "-m", "PyInstaller", "AI_BS_Studio.spec", "--noconfirm"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
output_lines = []
for line in p.stdout:
    print(line, end="")
    output_lines.append(line)
p.wait()
print(f"\nFinal Exit Code: {p.returncode}")
