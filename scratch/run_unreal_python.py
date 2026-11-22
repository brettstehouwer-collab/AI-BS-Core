import subprocess
import os

ue_cmd = r"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
uproject = r"C:\AI-BS\UnrealHub\AI_BS_Hub.uproject"
script_path = r"C:\AI-BS\UnrealHub\Content\Scripts\TheBadSide\scene_builder.py"

cmd = [
    ue_cmd,
    uproject,
    f"-ExecutePythonScript={script_path}",
    "-stdout",
    "-FullStdOutLogOutput",
    "-unattended",
    "-nullrhi"
]

print("Launching Unreal Engine Headless Command:")
print(" ".join(cmd))
res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(f"Exit Code: {res.returncode}")
print("\n--- STDOUT (Tail 30) ---")
for line in res.stdout.splitlines()[-30:]:
    print(line)

if res.stderr:
    print("\n--- STDERR ---")
    print(res.stderr[:500])
