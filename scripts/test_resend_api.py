import requests
import json

api_key = "re_cwXi97Fw_PMQUNSCbpkTcBpU7ecLvybxW"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print("--- Testing Resend API Key ---")
# 1. Check domains
try:
    r = requests.get("https://api.resend.com/domains", headers=headers, timeout=10)
    print("Domains status:", r.status_code)
    print("Domains response:", r.text)
except Exception as e:
    print("Domains exception:", e)

# 2. Check api-keys
try:
    r = requests.get("https://api.resend.com/api-keys", headers=headers, timeout=10)
    print("API keys status:", r.status_code)
    print("API keys response:", r.text)
except Exception as e:
    print("API keys exception:", e)
