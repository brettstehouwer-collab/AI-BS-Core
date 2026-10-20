import requests
import json

api_key = "mSw6wInv2gFupi4t0u1lzPwcXrItIs0mgPhfLKMKa2f661b2"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "AI-BS/5.0"
}

url = "https://developers.hostinger.com/api/dns/v1/zones/recdebut.com"

# Test 1: records as list of strings
payload1 = {
    "zone": [
        {
            "name": "resend._domainkey",
            "type": "TXT",
            "records": [
                "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUIqZX3zRgbIFS/P6MYRf6g1TmGM/LrP6FmDD7XrMw0w+z6fZtYBD35ugGRxa9HgkYhltOHVsW7HJwysjzLdImdGlW+yLd1MNYWPft7zpzSNrmtG8hGx6JjnJ81n/4tteT1Ww/RyiQQ3XfudoiJVAcVrzo+VdFPfZ/HgZWnejUrQIDAQAB"
            ],
            "ttl": 3600
        },
        {
            "name": "rsend",
            "type": "CNAME",
            "records": [
                "rsend.forge.rmta.net"
            ],
            "ttl": 3600
        },
        {
            "name": "send",
            "type": "CNAME",
            "records": [
                "send.forge.rmta.net"
            ],
            "ttl": 3600
        }
    ]
}

# Test 2: records as string
payload2 = {
    "zone": [
        {
            "name": "resend._domainkey",
            "type": "TXT",
            "records": "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUIqZX3zRgbIFS/P6MYRf6g1TmGM/LrP6FmDD7XrMw0w+z6fZtYBD35ugGRxa9HgkYhltOHVsW7HJwysjzLdImdGlW+yLd1MNYWPft7zpzSNrmtG8hGx6JjnJ81n/4tteT1Ww/RyiQQ3XfudoiJVAcVrzo+VdFPfZ/HgZWnejUrQIDAQAB",
            "ttl": 3600
        },
        {
            "name": "rsend",
            "type": "CNAME",
            "records": "rsend.forge.rmta.net",
            "ttl": 3600
        },
        {
            "name": "send",
            "type": "CNAME",
            "records": "send.forge.rmta.net",
            "ttl": 3600
        }
    ]
}

print("--- Testing Payload 1 (records as list) ---")
r1 = requests.put(url, json=payload1, headers=headers, timeout=10)
print("Status:", r1.status_code)
print("Response:", r1.text)

if r1.status_code not in (200, 201):
    print("\n--- Testing Payload 2 (records as string) ---")
    r2 = requests.put(url, json=payload2, headers=headers, timeout=10)
    print("Status:", r2.status_code)
    print("Response:", r2.text)
