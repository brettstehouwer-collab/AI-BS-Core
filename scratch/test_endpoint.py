"""Test API endpoint."""

import requests

try:
    response = requests.post(
        "http://127.0.0.1:8000/api/screenplay/adapt",
        json={
            "content": "The dog ran fast.",
            "type": "TV Pilot",
            "title": "Test"
        },
        timeout=30.0
    )
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)
except requests.RequestException as e:
    print("ERROR:", e)
