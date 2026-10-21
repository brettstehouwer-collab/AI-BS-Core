import requests
import json

BASE_URL = "http://127.0.0.1:8080/api/v1/recdebut"

payload = {
    "event": "sms:received",
    "data": {
        "_id": "test_tb_webhook_001",
        "sender": "+16164023628",
        "message": "Hi Coach Dennis, this is Marcus Johnson. I got your text! Would love to learn more about the program.",
        "receivedAt": "2026-10-20T23:10:00Z"
    }
}

# Note: +16164023628 is in exclusion set (Brett's number), so let's test with a simulated recruit number
# that is NOT excluded to verify end-to-end processing:
recruit_payload = {
    "event": "sms:received",
    "data": {
        "_id": "test_tb_webhook_recruit_777",
        "sender": "+19172131155",
        "message": "Yes sir! I'm interested in RecDebut. When can we schedule a phone call with my parents?",
        "receivedAt": "2026-10-20T23:10:00Z"
    }
}

print("--- Testing POST /webhooks/textbee ---")
r = requests.post(f"{BASE_URL}/webhooks/textbee", json=recruit_payload, timeout=20)
print("Status:", r.status_code)
print("Response:", json.dumps(r.json(), indent=2))
