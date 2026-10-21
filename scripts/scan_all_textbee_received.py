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

# Check if query parameter works:
url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/messages?type=RECEIVED"
r = requests.get(url, headers=headers, timeout=10)
if r.status_code == 200:
    res = r.json()
    print("With type=RECEIVED, total:", res.get("meta", {}).get("total"))
    msgs = res.get("data", [])
    if msgs:
        for m in msgs:
            print(f"ID: {m.get('_id')} | Type: {m.get('type')} | Sender: {m.get('sender')} | Time: {m.get('receivedAt')}")
            print(f"Message: {m.get('message')}\n")

# Now let's loop through all pages if type filter didn't get all of them
all_received = []
page = 1
while True:
    p_url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/messages?page={page}&limit=100"
    resp = requests.get(p_url, headers=headers, timeout=10)
    if resp.status_code != 200:
        break
    data = resp.json()
    items = data.get("data", [])
    if not items:
        break
    for item in items:
        if item.get("type") == "RECEIVED":
            all_received.append(item)
    total_pages = data.get("meta", {}).get("totalPages", 1)
    if page >= total_pages:
        break
    page += 1

print(f"\nScan complete across {page} pages. Found {len(all_received)} total RECEIVED messages:")
for m in all_received:
    print(f"ID: {m.get('_id')} | Sender: {m.get('sender')} | Time: {m.get('receivedAt')}")
    print(f"Message: {m.get('message')}")
    print("-" * 50)
