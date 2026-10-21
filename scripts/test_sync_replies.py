import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from routers.rec_debut_router import sync_inbound_athlete_replies

print("Running sync_inbound_athlete_replies()...")
res = sync_inbound_athlete_replies()
print("Result:", res)
