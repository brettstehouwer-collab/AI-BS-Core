import sys
import time
sys.path.insert(0, r"C:\AI-BS\backend")
sys.path.insert(0, r"C:\AI-BS")

from routers.rec_debut_router import sync_textbee_inbound_messages, sync_imap_inbound_messages

print("--- Testing sync_textbee_inbound_messages() ---")
t0 = time.time()
tb_res = sync_textbee_inbound_messages()
print(f"TextBee Sync in {time.time()-t0:.2f}s:", tb_res)

print("\n--- Testing sync_imap_inbound_messages() ---")
t0 = time.time()
imap_res = sync_imap_inbound_messages()
print(f"IMAP Sync in {time.time()-t0:.2f}s:", imap_res)
