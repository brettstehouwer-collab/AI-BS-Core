import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080/api/v1/recdebut"

print("--- 1. Testing GET /sms/replies ---")
try:
    r = requests.get(f"{BASE_URL}/sms/replies", timeout=5)
    print("Status:", r.status_code)
    print("Response:", json.dumps(r.json(), indent=2))
except Exception as e:
    print("Error:", e)

print("\n--- 2. Testing POST /sms/sync-replies ---")
try:
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/sms/sync-replies", timeout=25)
    elapsed = time.time() - t0
    print(f"Status (in {elapsed:.2f}s):", r.status_code)
    print("Response:", json.dumps(r.json(), indent=2))
except Exception as e:
    print("Error:", e)

print("\n--- 3. Testing POST /sms/test-route-dennis ---")
try:
    test_payload = {
        "sample_athlete_name": "Marcus Johnson (2027 Guard)",
        "sample_athlete_phone": "616-402-3628",
        "sample_reply": "Hey Dennis! I would love to talk about playing college basketball. When is good for you?"
    }
    r = requests.post(f"{BASE_URL}/sms/test-route-dennis", params=test_payload, timeout=20)
    print("Status:", r.status_code)
    print("Response:", json.dumps(r.json(), indent=2))
except Exception as e:
    print("Error:", e)
