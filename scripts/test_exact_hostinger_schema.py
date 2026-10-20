import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

url = "https://developers.hostinger.com/api/dns/v1/zones/recdebut.com"

payload = {
    "zone": [
        {
            "name": "resend._domainkey",
            "type": "TXT",
            "records": [
                {
                    "content": "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUIqZX3zRgbIFS/P6MYRf6g1TmGM/LrP6FmDD7XrMw0w+z6fZtYBD35ugGRxa9HgkYhltOHVsW7HJwysjzLdImdGlW+yLd1MNYWPft7zpzSNrmtG8hGx6JjnJ81n/4tteT1Ww/RyiQQ3XfudoiJVAcVrzo+VdFPfZ/HgZWnejUrQIDAQAB"
                }
            ],
            "ttl": 3600
        },
        {
            "name": "rsend",
            "type": "CNAME",
            "records": [
                {
                    "content": "rsend.forge.rmta.net"
                }
            ],
            "ttl": 3600
        },
        {
            "name": "send",
            "type": "CNAME",
            "records": [
                {
                    "content": "send.forge.rmta.net"
                }
            ],
            "ttl": 3600
        }
    ]
}

print("--- Sending PUT to Hostinger API with zone.records.content schema ---")
r = requests.put(url, json=payload, headers=headers, timeout=12)
print("Status:", r.status_code)
print("Response:", r.text)
