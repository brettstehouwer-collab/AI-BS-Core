import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

records_to_add = [
    {
        "type": "TXT",
        "name": "resend._domainkey",
        "content": "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUIqZX3zRgbIFS/P6MYRf6g1TmGM/LrP6FmDD7XrMw0w+z6fZtYBD35ugGRxa9HgkYhltOHVsW7HJwysjzLdImdGlW+yLd1MNYWPft7zpzSNrmtG8hGx6JjnJ81n/4tteT1Ww/RyiQQ3XfudoiJVAcVrzo+VdFPfZ/HgZWnejUrQIDAQAB",
        "ttl": 3600
    },
    {
        "type": "CNAME",
        "name": "rsend",
        "content": "rsend.forge.rmta.net",
        "ttl": 3600
    },
    {
        "type": "CNAME",
        "name": "send",
        "content": "send.forge.rmta.net",
        "ttl": 3600
    }
]

url = "https://developers.hostinger.com/api/dns/v1/zones/recdebut.com"

variations = [
    {"name": "Var 1 (zone as list)", "payload": {"zone": records_to_add}},
    {"name": "Var 2 (zone as list with overwrite=False)", "payload": {"zone": records_to_add, "overwrite": False}},
    {"name": "Var 3 (zone as dict with records)", "payload": {"zone": {"records": records_to_add}}},
    {"name": "Var 4 (zone as dict with domain and records)", "payload": {"zone": {"domain": "recdebut.com", "records": records_to_add}}}
]

for var in variations:
    print(f"--- Testing {var['name']} ---")
    try:
        r = requests.put(url, json=var['payload'], headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print("Response:", r.text[:400])
        if r.status_code in (200, 201):
            print("SUCCESS!!")
            break
    except Exception as e:
        print("Error:", e)
