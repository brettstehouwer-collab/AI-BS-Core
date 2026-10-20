from pathlib import Path

content = Path("backend/routers/rec_debut_router.py").read_text(encoding="utf-8")
idx = content.find("class MassBroadcastPayload")
if idx != -1:
    print(content[idx:idx+800])
else:
    print("Not found")
