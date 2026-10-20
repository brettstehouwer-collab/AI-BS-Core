import requests

api_key = "re_cwXi97Fw_PMQUNSCbpkTcBpU7ecLvybxW"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

url = "https://mcp.resend.com/mcp"
print("--- Probing Resend MCP Server ---")
try:
    # 1. Test GET (SSE handshake)
    r_get = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
    print("GET status:", r_get.status_code)
    print("GET headers:", dict(r_get.headers))
    print("GET text:", r_get.text[:200])
except Exception as e:
    print("GET error:", e)

try:
    # 2. Test POST (JSON-RPC initialize)
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
    r_post = requests.post(url, json=init_payload, headers=headers, timeout=8)
    print("\nPOST status:", r_post.status_code)
    print("POST headers:", dict(r_post.headers))
    print("POST text:", r_post.text[:400])
except Exception as e:
    print("POST error:", e)
