with open(r"c:\AI-BS\backend\AI_BS_Backend.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines[:300]):
    if "app" in line.lower() or "cors" in line.lower() or "fastapi" in line.lower():
        print(f"{idx+1}: {line.strip()}")
