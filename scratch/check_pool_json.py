import requests, json
r = requests.get('http://localhost:8080/api/v1/mining/pearl/pool-stats')
data = r.json()
print("Top-level keys:", list(data.keys()))
if "data" in data and isinstance(data["data"], dict):
    print("data keys:", list(data["data"].keys()))
    print("stats:", data["data"].get("stats"))
    print("unconfirmed count:", len(data["data"].get("unconfirmed", [])))
