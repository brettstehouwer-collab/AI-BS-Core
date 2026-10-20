import requests
import json

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
headers["mcp-session-id"] = session_id

# 2. Call list-domains or get domain
call_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "list-domains",
        "arguments": {}
    }
}

r2 = requests.post(url, json=call_payload, headers=headers, timeout=10)
print("list-domains status:", r2.status_code)
print("list-domains result:", r2.text.encode('ascii', 'replace').decode('ascii'))
