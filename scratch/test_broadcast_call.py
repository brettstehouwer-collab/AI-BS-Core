import requests
import json

url = "http://127.0.0.1:8080/api/v1/recdebut/broadcast"
payload = {
    "message_text": "Test message from debug script",
    "caller_id_email": "BrettStehouwer@gmail.com",
    "caller_id_phone": "616-402-3628",
    "dry_run": True
}

try:
    print(f"Calling {url} with dry_run=True...")
    res = requests.post(url, json=payload, timeout=10)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text[:500]}")
except Exception as e:
    print(f"Error calling broadcast: {e}")
