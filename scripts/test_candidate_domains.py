import requests

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

candidates = [
    "recdebut.com",
    "recreationaldebut.com",
    "recdebut.org",
    "recreationaldebut.org",
    "rec-debut.com",
    "recreational-debut.com",
    "dennisbell.com",
    "dennisbellsports.com",
    "stehouwer.com",
    "stehouwerpublishing.com",
    "ai-bs.com",
    "aibsbio.com",
    "aibssports.com"
]

print("--- Testing Domain Ownership in Hostinger Account ---")
for d in candidates:
    url = f"https://developers.hostinger.com/api/dns/v1/zones/{d}"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"{d} -> {r.status_code}: {r.json().get('message') or r.text[:60]}")
        if r.status_code == 200:
            print(f"!!! FOUND OWNED DOMAIN: {d} !!!")
            print("Records:", r.json())
    except Exception as e:
        print(f"{d} -> error: {e}")
