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

# 1. Check device info
try:
    r = requests.get(f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}", headers=headers, timeout=10)
    print("Device info status:", r.status_code)
    print("Device info body:", r.text[:500])
except Exception as e:
    print("Device info error:", e)

# 2. Check received messages endpoints
candidates = [
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/received-sms",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/inbound-sms",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/messages",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/sms",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/inbox",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/webhooks",
    f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/webhook",
    "https://api.textbee.dev/api/v1/gateway/webhooks",
]

for url in candidates:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"\nGET {url} -> Status {r.status_code}")
        if r.status_code != 404:
            print("Response:", r.text[:400])
    except Exception as e:
        print(f"Error for {url}:", e)
