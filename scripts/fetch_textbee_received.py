import requests
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

device_id = "6ad7b28560b1138230badd0a"
api_key = "txb_rAZOZNMuTEKtlxQ30hfcJd05dL2KlVRu"

headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/messages?limit=100"
r = requests.get(url, headers=headers, timeout=10)
if r.status_code == 200:
    data = r.json()
    messages = data.get("data", [])
    print(f"Total messages returned: {len(messages)}")
    received = [m for m in messages if m.get("type") == "RECEIVED"]
    print(f"Total RECEIVED messages: {len(received)}\n")
    for m in received:
        print(f"ID: {m.get('_id')}")
        print(f"Sender: {m.get('sender')}")
        print(f"Time: {m.get('receivedAt')}")
        print(f"Message: {m.get('message')}")
        print("-" * 50)
else:
    print("Error:", r.status_code, r.text)
