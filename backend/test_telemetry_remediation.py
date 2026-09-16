import unittest
import hashlib
import time
from modules.network_telemetry import (
    NetworkTelemetryEngine,
    get_tcp_flags,
    compute_canonical_flow_id,
    FLOW_IDLE_TIMEOUT_SECONDS
)

class TestTelemetryRemediation(unittest.TestCase):
    def setUp(self):
        self.engine = NetworkTelemetryEngine(max_tx_buffer=100, max_frame_buffer=200)

    def test_01_transaction_structure_and_latency(self):
        tx = {
            "id": f"tx_{int(time.time()*1000)}_abcdef123456",
            "type": "TRANSACTION",
            "protocol": "http",
            "method": "GET",
            "path": "/api/test",
            "status_code": 200,
            "asgi_duration_ms": 14.5,
            "body_bytes_in": 0,
            "body_bytes_out": 3070,
            "payload_sha256_in": None,
            "payload_sha256_out": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "client_ip": "127.0.0.1",
            "client_id": "stehouwer_publishing",
            "host_domain": "stehouwer-publishing.com",
            "origin_domain": "https://stehouwer-publishing.com",
            "trusted_domain_match": True,
            "classification_reason": "host_exact_match",
            "is_stehouwer_publishing": True,
            "flow_id": "TCP|127.0.0.1:54321|127.0.0.1:8080"
        }
        self.engine.record_transaction(tx)
        summary = self.engine.get_summary()

        # Check decoupled transaction metrics
        tx_stats = summary["transactions"]
        self.assertEqual(tx_stats["total_count"], 1)
        self.assertEqual(tx_stats["http_body_in_bytes"], 0)
        self.assertEqual(tx_stats["http_body_out_bytes"], 3070)
        self.assertEqual(tx_stats["asgi_duration"]["avg_ms"], 14.5)
        self.assertEqual(tx_stats["status_codes"]["2xx"], 1)

    def test_02_npcap_bandwidth_hierarchy_and_overhead(self):
        raw_payload = b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"
        expected_payload_sha256 = hashlib.sha256(raw_payload).hexdigest()

        frm = {
            "id": f"frm_{int(time.time()*1000)}_fedcba654321",
            "type": "FRAME",
            "engine": "NPCAP_L2_L3",
            "protocol": "TCP",
            "transport": "TCP",
            "tcp_flags": ["PSH", "ACK"],
            "endpoint": "192.168.1.50:8080",
            "src_endpoint": "192.168.1.20:54321",
            "status_code": None,  # STRICT RULE: Must be None, never synthetic 200
            "client_ip": "192.168.1.20",
            "client_id": "wire_capture",
            "origin_domain": "192.168.1.20:54321",
            "is_stehouwer_publishing": False,
            "duration_ms": 0.0,
            # Explicit semantic hierarchy: capture size != IP size != transport payload size != overhead
            "captured_frame_bytes": 1514,
            "ip_bytes": 1500,
            "transport_payload_bytes": len(raw_payload),
            "captured_overhead_bytes": 1514 - len(raw_payload),
            "frame_payload_sha256": expected_payload_sha256,
            "l2_meta": {"src_mac": "00:11:22:33:44:55", "dst_mac": "66:77:88:99:aa:bb"},
            "flow_id": "TCP|192.168.1.20:54321|192.168.1.50:8080"
        }
        self.engine.record_frame(frm)
        summary = self.engine.get_summary()

        # Check wire frame metrics & 4 distinct bandwidth metrics
        wire_stats = summary["wire_frames"]
        self.assertEqual(wire_stats["total_count"], 1)
        self.assertEqual(wire_stats["captured_frame_bytes"], 1514)
        self.assertEqual(wire_stats["transport_payload_bytes"], len(raw_payload))
        self.assertEqual(wire_stats["captured_overhead_bytes"], 1514 - len(raw_payload))
        self.assertNotEqual(wire_stats["captured_frame_bytes"], wire_stats["transport_payload_bytes"])

        # Status codes should remain 0 across all HTTP buckets!
        self.assertEqual(summary["transactions"]["status_codes"]["2xx"], 0)

        # Frame should have status_code None and explicit frame_payload_sha256
        frames = self.engine.get_traffic(record_type="FRAME")
        self.assertIsNone(frames[0]["status_code"])
        self.assertEqual(frames[0]["frame_payload_sha256"], expected_payload_sha256)
        self.assertEqual(frames[0]["captured_overhead_bytes"], 1514 - len(raw_payload))

    def test_03_canonical_flow_id_and_nullability(self):
        # Deterministic sorting: regardless of src/dst order, flow_id is identical
        fid_a = compute_canonical_flow_id("TCP", "192.168.1.50", 8080, "192.168.1.20", 54321)
        fid_b = compute_canonical_flow_id("TCP", "192.168.1.20", 54321, "192.168.1.50", 8080)
        self.assertEqual(fid_a, fid_b)
        self.assertEqual(fid_a, "TCP|192.168.1.20:54321|192.168.1.50:8080")

        # Nullability: unresolvable or loopback 0.0.0.0 produces None (never forced correlation)
        self.assertIsNone(compute_canonical_flow_id("TCP", "0.0.0.0", 0, "127.0.0.1", 8080))
        self.assertIsNone(compute_canonical_flow_id(None, "192.168.1.1", 80, "192.168.1.2", 80))

    def test_04_flow_lifecycle_active_and_expiration(self):
        now_t = time.time()
        flow_tcp = "TCP|10.0.0.1:1000|10.0.0.2:8080"
        flow_fin = "TCP|10.0.0.1:2000|10.0.0.2:8080"
        flow_udp = "UDP|10.0.0.1:3000|10.0.0.2:53"

        # Record active TCP frame
        self.engine.record_frame({
            "id": f"frm_{int(now_t*1000)}_000000000001",
            "type": "FRAME",
            "protocol": "TCP",
            "flow_id": flow_tcp,
            "tcp_flags": ["ACK"],
            "captured_frame_bytes": 100,
            "transport_payload_bytes": 40
        })

        # Record TCP frame with FIN flag (closes flow)
        self.engine.record_frame({
            "id": f"frm_{int(now_t*1000)}_000000000002",
            "type": "FRAME",
            "protocol": "TCP",
            "flow_id": flow_fin,
            "tcp_flags": ["FIN", "ACK"],
            "captured_frame_bytes": 60,
            "transport_payload_bytes": 0
        })

        # Record active UDP frame
        self.engine.record_frame({
            "id": f"frm_{int(now_t*1000)}_000000000003",
            "type": "FRAME",
            "protocol": "UDP",
            "flow_id": flow_udp,
            "tcp_flags": [],
            "captured_frame_bytes": 80,
            "transport_payload_bytes": 50
        })

        summary = self.engine.get_summary()
        flows_summary = summary["flows"]

        # Total observed is 3, but active_count is 2 (the FIN flow is closed!)
        self.assertEqual(flows_summary["total_observed"], 3)
        self.assertEqual(flows_summary["active_count"], 2)
        self.assertEqual(flows_summary["tcp_active"], 1)
        self.assertEqual(flows_summary["udp_active"], 1)
        self.assertTrue(self.engine.flows[flow_fin]["closed"])
        self.assertEqual(self.engine.flows[flow_fin]["closure_reason"], "FIN")

        # Test idle timeout expiration: mock last_seen to 75 seconds ago (> 60s timeout)
        self.engine.flows[flow_tcp]["last_seen"] = now_t - 75
        summary_after_idle = self.engine.get_summary()
        self.assertEqual(summary_after_idle["flows"]["active_count"], 1) # Only UDP remains active
        self.assertEqual(summary_after_idle["flows"]["tcp_active"], 0)
        self.assertEqual(summary_after_idle["flows"]["udp_active"], 1)

    def test_05_formal_flow_correlation(self):
        flow_id = "TCP|10.0.0.1:50000|10.0.0.2:8080"
        tx = {
            "id": "tx_1789000000000_123456789abc",
            "type": "TRANSACTION",
            "method": "POST",
            "path": "/api/submit",
            "status_code": 200,
            "asgi_duration_ms": 25.0,
            "flow_id": flow_id,
            "body_bytes_in": 500,
            "body_bytes_out": 200
        }
        self.engine.record_transaction(tx)

        for i in range(3):
            frm = {
                "id": f"frm_1789000000000_frame0000000{i}",
                "type": "FRAME",
                "transport": "TCP",
                "flow_id": flow_id,
                "captured_frame_bytes": 300,
                "transport_payload_bytes": 240,
                "frame_payload_sha256": f"hash_{i}"
            }
            self.engine.record_frame(frm)

        corr = self.engine.get_flow_correlation(transaction_id=tx["id"])
        self.assertIsNotNone(corr)
        self.assertEqual(corr["flow_id"], flow_id)
        self.assertEqual(corr["total_transactions"], 1)
        self.assertEqual(corr["total_wire_frames"], 3)
        self.assertEqual(corr["target_transaction"]["id"], tx["id"])

    def test_06_websocket_telemetry_l7_classification(self):
        # WS events must be classified as TRANSACTION, never FRAME
        ws_msg = {
            "id": f"tx_{int(time.time()*1000)}_wsmsg1234567",
            "type": "TRANSACTION",
            "engine": "ASGI",
            "protocol": "websocket",
            "method": "WS_RECEIVE",
            "path": "/api/ws",
            "status_code": 200,
            "body_bytes_in": 128,
            "body_bytes_out": 0,
            "payload_sha256_in": "a1b2c3d4e5f6",
            "flow_id": "TCP|127.0.0.1:60000|127.0.0.1:8080"
        }
        self.engine.record_transaction(ws_msg)
        self.assertEqual(self.engine.total_transactions, 1)
        self.assertEqual(self.engine.total_frames, 0)
        self.assertEqual(len(self.engine.transaction_buffer), 1)
        self.assertEqual(len(self.engine.frame_buffer), 0)

if __name__ == "__main__":
    unittest.main()
