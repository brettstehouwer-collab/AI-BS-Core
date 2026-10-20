import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

endpoints = [
    "https://developers.hostinger.com/api/domains/v1/portfolio",
    "https://developers.hostinger.com/api/hosting/v1/websites",
    "https://developers.hostinger.com/api/agency-hosting/v1/domains",
    "https://developers.hostinger.com/api/agency-hosting/v1/websites"
]

for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=10)
        print(f"{ep} -> Status: {r.status_code}")
        print("Response:", r.text[:400])
    except Exception as e:
        print(f"Error {ep}: {e}")
