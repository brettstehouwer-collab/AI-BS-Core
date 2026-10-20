import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

url = "https://developers.hostinger.com/api/dns/v1/zones/recreationaldebut.com"
r = requests.get(url, headers=headers, timeout=10)
print("recreationaldebut.com Status:", r.status_code)
if r.status_code == 200:
    print("Found! Current records in recreationaldebut.com:")
    records = r.json()
    print(f"Total existing records: {len(records)}")
    for rec in records:
        print(" ", rec)
else:
    print("Error:", r.text)
