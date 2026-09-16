import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

rtdb_base = "https://cymatics-livestream-default-rtdb.firebaseio.com"
endpoints = [
    "/.json",
    "/state.json",
    "/cards.json",
    "/drops.json",
    "/livestream.json",
    "/active.json",
    "/unlocked.json",
    "/stream.json"
]

for ep in endpoints:
    url = f"{rtdb_base}{ep}"
    try:
        r = requests.get(url, timeout=5)
        print(f"RTDB {ep}: Status {r.status_code}")
        if r.status_code == 200 and r.text != "null":
            print(f"  Response: {r.text[:300]}")
    except Exception as e:
        print(f"RTDB {ep}: Error {e}")
