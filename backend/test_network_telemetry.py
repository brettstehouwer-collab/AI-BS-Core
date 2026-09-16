"""
Standalone Automated Test Suite for AI-BS Network Telemetry, Cryptographic Packet Hashing
and Over-The-Air Wave Hardware Sensor Telemetry Subsystem.
"""

import sys
import json
import hashlib

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.network_telemetry import NetworkTelemetryMiddleware, NetworkTelemetryEngine
from modules.ambient_sensor_telemetry import AirWaveSensorEngine
from routers.network_telemetry_router import router as telemetry_router

def run_telemetry_tests():
    print("================================================================")
    print("[AI-BS] Starting Network Telemetry & Wave Sensor Verification")
    print("================================================================")


    # 1. Initialize isolated engine & test app
    test_engine = NetworkTelemetryEngine(max_buffer_len=100)
    app = FastAPI()
    app.add_middleware(NetworkTelemetryMiddleware, engine=test_engine)
    app.include_router(telemetry_router)

    @app.post("/test-echo")
    async def echo_endpoint(payload: dict):
        return {"status": "ok", "received": payload}

    @app.get("/test-empty")
    async def empty_endpoint():
        return {"empty": True}

    client = TestClient(app)

    # Test 1: Inbound & Outbound Byte Counting and SHA-256 Hashing
    print("\n[Test 1] Verifying Wire Byte Volume & SHA-256 Payload Hashes...")
    test_payload = {"message": "Hello AI-BS Network Telemetry", "data": [1, 2, 3, 4, 5] * 10}
    payload_bytes = json.dumps(test_payload).encode("utf-8")
    expected_hash_in = hashlib.sha256(payload_bytes).hexdigest()

    resp = client.post(
        "/test-echo",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "Host": "api.ai-bs.local"}
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    expected_hash_out = hashlib.sha256(resp.content).hexdigest()

    records = test_engine.get_traffic(limit=10)
    assert len(records) >= 1, "No transactions recorded in ring buffer"
    rec = records[0]
    
    assert rec["bytes_in"] == len(payload_bytes), f"Expected bytes_in {len(payload_bytes)}, got {rec['bytes_in']}"
    assert rec["bytes_out"] == len(resp.content), f"Expected bytes_out {len(resp.content)}, got {rec['bytes_out']}"
    assert rec["packet_hash_in"] == expected_hash_in, f"Hash in mismatch: expected {expected_hash_in}, got {rec['packet_hash_in']}"
    assert rec["packet_hash_out"] == expected_hash_out, f"Hash out mismatch: expected {expected_hash_out}, got {rec['packet_hash_out']}"
    assert rec["duration_ms"] >= 0, f"Invalid duration: {rec['duration_ms']}"
    print(f"  [PASS] Bytes in: {rec['bytes_in']} bytes | Hash In: {rec['packet_hash_in'][:16]}...")
    print(f"  [PASS] Bytes out: {rec['bytes_out']} bytes | Hash Out: {rec['packet_hash_out'][:16]}...")
    print(f"  [PASS] Execution latency: {rec['duration_ms']} ms")

    # Test 2: Credential & Sensitive Header Scrubbing
    print("\n[Test 2] Verifying Credential & Token Hygiene...")
    client.get(
        "/test-empty",
        headers={
            "Authorization": "Bearer super_secret_token_12345",
            "Cookie": "session_id=abcdef123456",
            "X-Api-Key": "key_private_9999",
            "Host": "api.ai-bs.local"
        }
    )
    rec2 = test_engine.get_traffic(limit=1)[0]
    assert rec2["headers"].get("authorization") == "[REDACTED]", "Authorization header not redacted"
    assert rec2["headers"].get("cookie") == "[REDACTED]", "Cookie header not redacted"
    assert rec2["headers"].get("x-api-key") == "[REDACTED]", "X-Api-Key header not redacted"
    print("  [PASS] Authorization, Cookie, and X-Api-Key headers successfully scrubbed to [REDACTED]")

    # Test 3: Stehouwer Publishing Domain Classification & Dedicated Ledger
    print("\n[Test 3] Verifying stehouwer-publishing.com Classification & Packet Sub-Ledger...")
    stehouwer_payload = {"campaign": "Fall Book Launch", "author": "Brett Stehouwer"}
    sh_bytes = json.dumps(stehouwer_payload).encode("utf-8")
    
    client.post(
        "/test-echo",
        content=sh_bytes,
        headers={
            "Content-Type": "application/json",
            "Host": "stehouwer-publishing.com",
            "Origin": "https://stehouwer-publishing.com"
        }
    )
    
    summary = test_engine.get_summary()
    sh_stats = summary["stehouwer_publishing"]
    assert sh_stats["total_packets"] >= 1, "Stehouwer packet not counted in sub-ledger"
    assert sh_stats["bytes_in"] >= len(sh_bytes), "Stehouwer bytes_in not tracked"
    assert len(sh_stats["recent_packet_hashes"]) >= 1, "Recent packet hashes empty for Stehouwer"
    print(f"  [PASS] Stehouwer Publishing total packets: {sh_stats['total_packets']}")
    print(f"  [PASS] Stehouwer Publishing bytes in: {sh_stats['bytes_in']} bytes")
    print(f"  [PASS] Stehouwer recent hash: {sh_stats['recent_packet_hashes'][0]['hash_in'][:16]}...")

    # Test 4: Over-The-Air RF Wave Hardware Sensor Scanning & SHA-256 Beacon Hashing
    print("\n[Test 4] Verifying Over-The-Air RF Wave Hardware Sensor Telemetry & SQLite Persistence...")
    air_engine = AirWaveSensorEngine()
    scan_res = air_engine.scan_air()
    assert scan_res["status"] == "success", "Scan status not success"
    assert scan_res["total_detected"] > 0, "No air beacons detected on host PC"
    assert scan_res["wifi_count"] > 0 or scan_res["bluetooth_count"] > 0, "Neither Wi-Fi nor Bluetooth detected"
    
    # Verify beacon hash properties
    sample_beacon = scan_res["records"][0]
    assert "beacon_hash" in sample_beacon, "Missing beacon_hash"
    assert len(sample_beacon["beacon_hash"]) == 64, f"Invalid SHA-256 length: {len(sample_beacon['beacon_hash'])}"
    assert sample_beacon["medium"] == "RF_ELECTROMAGNETIC", "Invalid medium"
    assert sample_beacon["frequency_band"] in ("2.4GHz_ISM", "5GHz_UNII", "6GHz_WIFI6E"), f"Unexpected band: {sample_beacon['frequency_band']}"
    print(f"  [PASS] Detected {scan_res['total_detected']} ambient RF wave signals across host sensors:")
    print(f"    - Wi-Fi RF (2.4/5/6 GHz): {scan_res['wifi_count']} beacons")
    print(f"    - Bluetooth / BLE: {scan_res['bluetooth_count']} devices")
    print(f"    - Sample Beacon Hash: {sample_beacon['beacon_hash']}")
    print(f"    - Frequency Band: {sample_beacon['frequency_band']} | Signal: {sample_beacon['signal_pct']}%")

    # Test 5: SQLite Database Persistence & Historical Queries
    print("\n[Test 5] Verifying Air Telemetry SQLite Persistence & Summary...")
    db_records = air_engine.get_records(limit=10)
    assert len(db_records) >= 1, "Failed to retrieve persisted records from SQLite"
    air_summary = air_engine.get_summary()
    assert air_summary["total_records"] > 0, "Total records in SQLite summary is 0"
    assert air_summary["unique_beacon_hashes"] > 0, "Unique beacon hashes is 0"
    print(f"  [PASS] SQLite Database Total Air Records: {air_summary['total_records']}")
    print(f"  [PASS] Unique Deterministic Beacon Hashes: {air_summary['unique_beacon_hashes']}")
    print(f"  [PASS] Band Breakdown: {air_summary['band_distribution']}")

    # Test 6: API Router Query Endpoints
    print("\n[Test 6] Verifying Telemetry API Router Endpoints (/api/network-telemetry)...")
    sum_resp = client.get("/api/network-telemetry/summary")
    assert sum_resp.status_code == 200, f"Summary endpoint failed: {sum_resp.status_code}"
    assert "stehouwer_publishing" in sum_resp.json(), "Missing stehouwer_publishing in summary JSON"

    traffic_resp = client.get("/api/network-telemetry/traffic?is_stehouwer=true")
    assert traffic_resp.status_code == 200, f"Traffic endpoint failed: {traffic_resp.status_code}"
    
    air_sum_resp = client.get("/api/network-telemetry/air/summary")
    assert air_sum_resp.status_code == 200, f"Air summary endpoint failed: {air_sum_resp.status_code}"
    print("  [PASS] /api/network-telemetry/summary responded 200 OK")
    print("  [PASS] /api/network-telemetry/traffic?is_stehouwer=true responded 200 OK")
    print("  [PASS] /api/network-telemetry/air/summary responded 200 OK")

    print("\n================================================================")
    print("[SUCCESS] ALL 6 VERIFICATION TEST SUITES PASSED CLEANLY (100%)")
    print("================================================================")


if __name__ == "__main__":
    run_telemetry_tests()
