import requests

api_key = "re_cwXi97Fw_PMQUNSCbpkTcBpU7ecLvybxW"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

url = "https://mcp.resend.com/mcp"
init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "Antigravity",
            "version": "1.0.0"
        }
    }
}

r = requests.post(url, json=init_payload, headers=headers, timeout=10)
print("POST status:", r.status_code)
print("POST headers:", dict(r.headers))
print("POST text:", r.text[:600])
