import requests
try:
    r = requests.get('http://127.0.0.1:8080/api/v1/mining/pearl/pool-stats', timeout=3)
    print("127.0.0.1:8080 -> Status:", r.status_code)
except Exception as e:
    print("127.0.0.1 Error:", e)
