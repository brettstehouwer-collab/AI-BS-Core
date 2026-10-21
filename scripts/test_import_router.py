import sys
import os
sys.path.insert(0, r"C:\AI-BS\backend")
sys.path.insert(0, r"C:\AI-BS")

from routers import rec_debut_router

print("rec_debut_router loaded successfully!")
print("Sentinel started:", rec_debut_router._inbound_sentinel_started)
print("sync_inbound_athlete_replies exists:", callable(rec_debut_router.sync_inbound_athlete_replies))
print("dispatch_sms_message exists:", callable(rec_debut_router.dispatch_sms_message))
print("forward_athlete_reply_to_dennis exists:", callable(rec_debut_router.forward_athlete_reply_to_dennis))
