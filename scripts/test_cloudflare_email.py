import urllib.request
import json
import os

token = "cfut_yhe6w3OJ4xbAL9sIPaS5V8entYRfK47xs3NIK5Lo15afb231"
account_id = "81041170430c35368afacc42e6efec67"

url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/sending/domains"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
})

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("Cloudflare Email Sending Domains:", data)
except Exception as e:
    print("Cloudflare Email Sending Domains error:", e)
