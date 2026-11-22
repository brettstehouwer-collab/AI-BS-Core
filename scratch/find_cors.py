with open(r"c:\AI-BS\backend\AI_BS_Backend.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "add_middleware" in line or "CORSMiddleware" in line or "cors" in line.lower() and "import" not in line.lower():
            print(f"{idx+1}: {line.strip()}")
