import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

domain = "recdebut.com"
url = f"https://developers.hostinger.com/api/dns/v1/zones/{domain}"

print(f"--- Fetching DNS records for {domain} via Hostinger API ---")
try:
    r = requests.get(url, headers=headers, timeout=10)
    print("Status:", r.status_code)
    print("Headers:", dict(r.headers))
    print("Response:", r.text[:500])
except Exception as e:
    print("Exception:", e)
