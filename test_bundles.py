import requests
import json

url = 'https://console.vast.ai/api/v0/bundles/'
payload = {'external': {'eq': False}, 'machine_id': {'eq': 150272}, 'type': 'on-demand', 'rentable': {'eq': True}}
res = requests.post(url, json=payload).json()
offers = res.get('offers', [])
if offers:
    print(json.dumps(offers[0], indent=2))
else:
    print("No offers found.")
