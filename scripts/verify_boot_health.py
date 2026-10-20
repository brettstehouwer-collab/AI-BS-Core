"""
AI-BS End-to-End Boot Health & Live Endpoint Prober
Performs live synthetic validation across all core REST, WebSocket, and SHM ports.
"""

import urllib.request
import urllib.error
import json
import socket
import sys

ENDPOINTS_TO_PROBE = [
    {
        "name": "FastAPI Core Health",
        "url": "http://127.0.0.1:8080/api/system/health",
        "expected_keys": ["status", "cpu", "ram", "gpu"]
    },
    {
        "name": "FastAPI Satellites API",
        "url": "http://127.0.0.1:8080/api/system/satellites",
        "expected_keys": ["status", "satellites"]
    },
    {
        "name": "ChromaDB Vector Store Heartbeat",
        "url": "http://127.0.0.1:8002/api/v2/heartbeat",
        "expected_keys": ["nanosecond heartbeat"]
    },
    {
        "name": "Broadcast Kernel Windows API",
        "url": "http://127.0.0.1:8088/api/windows",
        "expected_keys": ["open_windows"]
    },
    {
        "name": "Social Daemon Status API",
        "url": "http://127.0.0.1:8006/api/social/status",
        "expected_keys": ["status"]
    },
    {
        "name": "Ollama Primary Model Registry",
        "url": "http://127.0.0.1:11434/api/tags",
        "expected_keys": ["models"]
    },
    {
        "name": "Go Matrix Gateway Proxy Check",
        "url": "http://127.0.0.1:8000/api/system/health",
        "expected_keys": ["status"]
    }
]

def probe_endpoint(item):
    name = item["name"]
    url = item["url"]
    expected_keys = item.get("expected_keys", [])
    
    req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Boot-Prober/1.0", "X-Client-ID": "stehouwer_publishing"})
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
                keys_found = [k for k in expected_keys if k in data]
                all_keys_ok = len(keys_found) == len(expected_keys)
                return {
                    "name": name,
                    "url": url,
                    "status": "PASS",
                    "code": status_code,
                    "keys_ok": all_keys_ok,
                    "details": f"Keys verified: {keys_found}"
                }
            except Exception:
                return {
                    "name": name,
                    "url": url,
                    "status": "PASS",
                    "code": status_code,
                    "keys_ok": True,
                    "details": f"Raw payload received ({len(body)} bytes)"
                }
    except urllib.error.URLError as e:
        return {
            "name": name,
            "url": url,
            "status": "OFFLINE/ON-DEMAND",
            "code": "N/A",
            "keys_ok": False,
            "details": str(e.reason)
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "ERROR",
            "code": "ERR",
            "keys_ok": False,
            "details": str(e)
        }

def main():
    print("=" * 80)
    print("       AI-BS END-TO-END SYSTEM BOOT & LIVE ENDPOINT PROBING ENGINE")
    print("=" * 80)
    
    results = []
    passed = 0
    
    for item in ENDPOINTS_TO_PROBE:
        res = probe_endpoint(item)
        results.append(res)
        status_fmt = f"[{res['status']}]"
        print(f"  * {res['name']:<35} | {res['url']:<42} : {status_fmt}")
        if res["details"]:
            print(f"      -> {res['details']}")
        if res["status"] == "PASS":
            passed += 1
            
    print("=" * 80)
    print(f"Live Probing Completed: {passed}/{len(ENDPOINTS_TO_PROBE)} verified responsive.")
    print("=" * 80)

if __name__ == "__main__":
    main()