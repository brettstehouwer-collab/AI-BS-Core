from pathlib import Path

path = Path("backend/routers/rec_debut_router.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(k in line for k in ["/broadcast", "class Broadcast", "def start_broadcast", "def broadcast"]):
        print(f"Line {i+1}: {line.strip()}")
