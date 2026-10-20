import requests

api_key = "re_cwXi97Fw_PMQUNSCbpkTcBpU7ecLvybxW"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

url = "https://mcp.resend.com/mcp"

# 1. Initialize
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

r1 = requests.post(url, json=init_payload, headers=headers, timeout=10)
session_id = r1.headers.get("mcp-session-id")
print("Initialized session:", session_id[:30] if session_id else None)

headers["mcp-session-id"] = session_id

# 2. List Tools
tools_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

r2 = requests.post(url, json=tools_payload, headers=headers, timeout=10)
print("tools/list status:", r2.status_code)
tools = r2.json().get("result", {}).get("tools", [])
print(f"Total tools available: {len(tools)}")
for t in tools:
    print(f" - {t.get('name')}: {t.get('description')}")
