import requests
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

device_id = "6ad7b28560b1138230badd0a"
api_key = "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu"

url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/messages?limit=50"
headers = {"x-api-key": api_key, "Content-Type": "application/json"}

try:
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json().get("data", [])
    received = [m for m in data if m.get("type") == "RECEIVED"]
    print(f"Total received messages on TextBee device: {len(received)}")
    for m in received:
        print(f"From: {m.get('sender')} | At: {m.get('receivedAt')} | Body: {m.get('message')}")
except Exception as e:
    print("Error:", e)
