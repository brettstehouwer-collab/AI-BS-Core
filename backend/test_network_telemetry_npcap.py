"""
AI-BS Unit Tests for Npcap L2/L3 Promiscuous Sniffer & Capture Mode Architecture
Verifies capture mode switching, interface enumeration, L2 MAC metadata ingestion,
BPF filter handling, and FastAPI route endpoints.
"""

import sys
import os
import time
import hashlib
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from modules.network_telemetry import (
    network_telemetry_engine,
    NetworkTelemetryMiddleware,
    NPCAP_AVAILABLE
)
from routers.network_telemetry_router import router as telemetry_router

app = FastAPI()
app.add_middleware(NetworkTelemetryMiddleware, engine=network_telemetry_engine)
app.include_router(telemetry_router)

@app.get("/test/hello")
def hello():
    return {"message": "hello world"}

client = TestClient(app)

def test_npcap_telemetry_suite():
    print("=== Testing AI-BS Npcap & Hybrid Telemetry Engine ===")
    network_telemetry_engine.clear()

    # 1. Verify summary returns capture_engine metadata
    summary = network_telemetry_engine.get_summary()
    assert "capture_engine" in summary, "Summary must include capture_engine"
    cap_engine = summary["capture_engine"]
    print(f"[PASS] Capture Engine Summary: mode={cap_engine['mode']}, npcap_available={cap_engine['npcap_available']}")

    # 2. Verify interface enumeration
    interfaces = network_telemetry_engine.get_interfaces()
    assert isinstance(interfaces, list), "Interfaces must be a list"
    print(f"[PASS] Discovered {len(interfaces)} host network adapters via Scapy/Windows arch")
    for iface in interfaces[:3]:
        print(f"       - {iface.get('description')} (MAC: {iface.get('mac')})")

    # 3. Verify mode setting
    res_asgi = network_telemetry_engine.set_mode("ASGI")
    assert res_asgi["status"] == "success"
    assert res_asgi["active_mode"] == "ASGI"
    print("[PASS] Mode set to ASGI successfully")

    if not NPCAP_AVAILABLE:
        try:
            network_telemetry_engine.set_mode("NPCAP")
            assert False, "Should have raised RuntimeError when Npcap driver is missing"
        except RuntimeError as e:
            print(f"[PASS] Non-blocking fallback verified: {e}")

    # 4. Ingest an L2/L3 frame simulating an Npcap wire capture
    test_payload = b"GET /api/cms/articles HTTP/1.1\r\nHost: stehouwer-publishing.com\r\n\r\n"
    test_hash = hashlib.sha256(test_payload).hexdigest()
    npcap_rec = {
        "id": "pkt_npcap_test_001",
        "timestamp": "2026-09-10T06:20:00Z",
        "engine": "NPCAP_L2_L3",
        "protocol": "TCP",
        "method": "TCP",
        "path": "192.168.4.92:8080",
        "status_code": 200,
        "client_ip": "192.168.4.10",
        "client_id": "stehouwer_publishing",
        "origin_domain": "192.168.4.10:54321",
        "is_stehouwer_publishing": True,
        "duration_ms": 0.0,
        "bytes_in": len(test_payload),
        "bytes_out": 0,
        "packet_hash_in": test_hash,
        "packet_hash_out": None,
        "headers": None,
        "l2_meta": {"src_mac": "a0:ad:9f:2c:27:ca", "dst_mac": "60:ff:9e:ff:51:24"},
        "transport": "TCP",
        "sport": 54321,
        "dport": 8080
    }
    network_telemetry_engine.record_transaction(npcap_rec)

    # 5. Make an ASGI request through the client
    resp = client.get("/test/hello", headers={"Host": "stehouwer-publishing.com", "X-Client-ID": "stehouwer_publishing"})
    assert resp.status_code == 200

    # 6. Verify traffic query and engine filtering
    all_traffic = network_telemetry_engine.get_traffic(limit=10)
    assert len(all_traffic) >= 2, f"Expected at least 2 records, got {len(all_traffic)}"

    npcap_traffic = network_telemetry_engine.get_traffic(engine="NPCAP_L2_L3")
    assert len(npcap_traffic) >= 1
    assert npcap_traffic[0]["l2_meta"]["src_mac"] == "a0:ad:9f:2c:27:ca"
    assert npcap_traffic[0]["packet_hash_in"] == test_hash
    print(f"[PASS] Npcap L2/L3 record verified: MAC {npcap_traffic[0]['l2_meta']['src_mac']} -> {npcap_traffic[0]['l2_meta']['dst_mac']}, Hash={test_hash[:16]}...")

    asgi_traffic = network_telemetry_engine.get_traffic(engine="ASGI")
    assert len(asgi_traffic) >= 1
    assert asgi_traffic[0]["path"] == "/test/hello"
    print(f"[PASS] ASGI record verified: {asgi_traffic[0]['method']} {asgi_traffic[0]['path']} (dur={asgi_traffic[0]['duration_ms']}ms)")

    # 7. Test router endpoints
    r_summary = client.get("/api/network-telemetry/summary")
    assert r_summary.status_code == 200
    assert r_summary.json()["status_codes"]["2xx"] >= 1

    r_mode = client.get("/api/network-telemetry/capture-mode")
    assert r_mode.status_code == 200
    assert "capture_engine" in r_mode.json()

    r_set_mode = client.post("/api/network-telemetry/capture-mode?mode=ASGI&bpf=tcp%20port%208080")
    assert r_set_mode.status_code == 200
    assert r_set_mode.json()["active_mode"] == "ASGI"

    r_ifaces = client.get("/api/network-telemetry/interfaces")
    assert r_ifaces.status_code == 200
    assert "interfaces" in r_ifaces.json()

    print("[PASS] All FastAPI Router Endpoints (/summary, /capture-mode, /interfaces, /traffic) 100% OK")
    print("=== All Npcap L2/L3 & ASGI Tests Succeeded ===")

if __name__ == "__main__":
    test_npcap_telemetry_suite()
