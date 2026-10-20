import requests

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

endpoints = [
    "https://developers.hostinger.com/api/me",
    "https://developers.hostinger.com/api/user",
    "https://developers.hostinger.com/api/profile",
    "https://developers.hostinger.com/api/account"
]

for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=5)
        print(ep, "->", r.status_code, r.text[:150])
    except Exception as e:
        print(ep, "error:", e)
