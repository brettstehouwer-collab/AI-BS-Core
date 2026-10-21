import ast
from pathlib import Path

ROUTER_PATH = Path(r"C:\AI-BS\backend\routers\rec_debut_router.py")
src = ROUTER_PATH.read_text(encoding="utf-8")

start_marker = "def sync_inbound_athlete_replies() -> Dict[str, Any]:"
end_marker = '@router.get("/track/open/{campaign_id}/{athlete_id}")'

if start_marker not in src:
    print("ERROR: start_marker not found!")
if end_marker not in src:
    print("ERROR: end_marker not found!")

print("Markers found successfully!")
