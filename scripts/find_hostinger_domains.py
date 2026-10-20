import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

endpoints = [
    "https://developers.hostinger.com/api/dns/v1/zones",
    "https://developers.hostinger.com/api/dns/v1/snapshots",
    "https://developers.hostinger.com/api/domains/v1/domains",
    "https://developers.hostinger.com/api/hosting/v1/accounts",
    "https://developers.hostinger.com/api/vps/v1/virtual-servers"
]

for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=10)
        print(f"Endpoint: {ep} -> Status: {r.status_code}")
        print("Response:", r.text[:300])
    except Exception as e:
        print(f"Error {ep}: {e}")
