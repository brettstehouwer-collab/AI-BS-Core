from pathlib import Path

path = Path("backend/routers/rec_debut_router.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def _run_broadcast_worker" in line:
        print(f"Line {i+1}: {line.strip()}")
