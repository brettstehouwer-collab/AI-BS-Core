import requests, json
url = "http://127.0.0.1:8335"
auth = ("26e7f58117a4cbd55483dbb5faa3ce55", "ce21a515b1273a5e341ed7f35d13c57398e546e6dddbc5d0d974319af3af6930")
payload = {
    "jsonrpc": "1.0",
    "id": "curltest",
    "method": "getbalance",
    "params": []
}
try:
    r = requests.post(url, json=payload, auth=auth, timeout=3)
    print("getbalance:", r.status_code, r.text)
except Exception as e:
    print("Error:", e)
