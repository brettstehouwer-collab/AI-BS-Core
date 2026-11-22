import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:8080/api/audio/assistant/chat"
payload = {"message": "now i want it to be able to randome a beat non of that cyber punk stuff"}

res = requests.post(url, json=payload)
print("Status Code:", res.status_code)
data = res.json()
print("Engine:", data.get("engine"))
print("Actions:", json.dumps(data.get("actions"), indent=2))
print("Suggestions:", data.get("suggestions"))
print("Reply:\n", data.get("reply"))
