import requests

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

payload = {
    "overwrite": False,
    "records": records_to_add
}

url = "https://developers.hostinger.com/api/dns/v1/zones/recdebut.com"
try:
    r = requests.put(url, json=payload, headers=headers, timeout=10)
    print("PUT Status:", r.status_code)
    print("PUT Response:", r.text)
except Exception as e:
    print("Error:", e)
