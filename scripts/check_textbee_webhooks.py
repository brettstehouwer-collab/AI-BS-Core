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

endpoints = [
    "https://api.textbee.dev/api/v1/webhooks",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/webhooks",
]

for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=5)
        print(f"GET {ep} -> Status {r.status_code}")
        print("Response:", r.text)
    except Exception as e:
        print("Error:", e)
