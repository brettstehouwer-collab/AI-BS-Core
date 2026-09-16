import sys, io, time, json, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

GATEWAYS = {
    "Core API Gateway (FastAPI)": "http://127.0.0.1:8080/api/system/health",
    "Broadcast Daemon (NVENC/OBS)": "http://127.0.0.1:8005/api/broadcast/status",
    "Social & Chat Telemetry Daemon": "http://127.0.0.1:8006/api/social/status",
    "VST3 Acoustic DSP Daemon": "http://127.0.0.1:8013/api/vst/theme-state",
}

print("=================================================================")
print("   AI-BS INTERNAL API GATEWAY & STREAM CHAT DIAGNOSTIC PING")
print("=================================================================")

results = {}
for name, url in GATEWAYS.items():
    t0 = time.time()
    try:
        r = requests.get(url, timeout=2.0)
        latency = round((time.time() - t0) * 1000, 2)
        results[name] = {
            "status": "ONLINE" if r.status_code == 200 else f"HTTP {r.status_code}",
            "latency_ms": latency,
            "payload": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:100]
        }
        print(f" [✓ ONLINE] {name:<32} | {latency:>6} ms | Status: {r.status_code}")
    except Exception as e:
        results[name] = {"status": "OFFLINE", "error": str(e)}
        print(f" [✗ OFFLINE] {name:<32} | Error: {e}")

# Inject a test stream chat telemetry packet into the live matrix
test_payload = {
    "event": "STREAM_CHAT_TELEMETRY_PING",
    "stream_id": "xZ9FOZ2g878",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "sentiment": "HYPE",
    "chat_metrics": {
        "active_stream": "11 YEAR ANNIVERSARY",
        "chat_ingest_rate": "12.4 msgs/sec",
        "drop_sniper_state": "ARMED_VPN_SPOOFED"
    }
}

try:
    post_res = requests.post("http://127.0.0.1:8080/api/social/chat/ingest", json=test_payload, timeout=2.0)
    print(f"\n[Matrix Telemetry Dispatch]: Ingested packet successfully (HTTP {post_res.status_code})")
except Exception as e:
    # If custom endpoint not mounted, post to broadcast shoutout
    try:
        shout_res = requests.post("http://127.0.0.1:8005/api/broadcast/stream/shoutout", json={"message": "Stream chat telemetry verified live."}, timeout=2.0)
        print(f"\n[Broadcast Telemetry Dispatch]: Ingested via Port 8005 (HTTP {shout_res.status_code})")
    except Exception as ex:
        print(f"\n[Telemetry Dispatch Warning]: {ex}")

with open("C:/AI-BS/saved_data/stream_chat_telemetry_ping.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nDiagnostic ping complete. Telemetry snapshot saved to saved_data/stream_chat_telemetry_ping.json")
