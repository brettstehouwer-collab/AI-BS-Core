import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

endpoints = [
    "https://api.hostinger.com/v1/domains",
    "https://api.hostinger.com/v1/dns",
    "https://api.hostinger.com/v1/dns/zones",
    "https://api.hostinger.com/v1/dns/records/recdebut.com",
    "https://api.hostinger.com/v1/domains/recdebut.com",
    "https://api.hostinger.com/v1/dns/zones/recdebut.com"
]

print("--- Testing Hostinger API Endpoints ---")
for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=8)
        print(f"{ep} -> Status: {r.status_code}")
        if r.status_code in (200, 201):
            print(f"  Response: {r.text[:300]}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"{ep} -> Exception: {e}")
