import unittest
import os
import sys

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi.testclient import TestClient
from AI_BS_Backend import app

class TestExecutiveRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_executive_status(self):
        resp = self.client.get("/api/executive/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("privileges"), "root_host_unrestricted")
        for rt in ["powershell", "cmd", "wsl", "python", "node", "ts", "go", "rust", "file_read", "file_write"]:
            self.assertIn(rt, data.get("supported_command_types", []))

    def test_run_powershell(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "powershell",
            "target": "Write-Output 'EXECUTIVE_TEST_OK'"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("EXECUTIVE_TEST_OK", data.get("stdout", ""))

    def test_run_cmd(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "cmd",
            "target": "echo CMD_TEST_OK"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("CMD_TEST_OK", data.get("stdout", ""))

    def test_run_python(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "python",
            "target": "print('PY_MULTI_OK', 21 * 2)"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("PY_MULTI_OK 42", data.get("stdout", ""))

    def test_run_node(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "node",
            "target": "console.log('NODE_MULTI_OK', 100 + 23)"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("NODE_MULTI_OK 123", data.get("stdout", ""))

    def test_universal_file_write_and_read(self):
        resp1 = self.client.post("/api/executive/run", json={
            "command_type": "file_write",
            "target": "scratch/test_universal.proto",
            "payload": {"content": "syntax = 'proto3';"}
        })
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json().get("status"), "success")

        resp2 = self.client.post("/api/executive/run", json={
            "command_type": "file_write",
            "target": "scratch/test_universal.proto",
            "payload": {"content": "syntax = 'proto3'; // v2"}
        })
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.json()
        self.assertEqual(d2.get("status"), "success")
        self.assertTrue(d2.get("result", {}).get("backup_created"))

        resp_r = self.client.post("/api/executive/run", json={
            "command_type": "file_read",
            "target": "scratch/test_universal.proto"
        })
        self.assertEqual(resp_r.status_code, 200)
        dr = resp_r.json()
        self.assertEqual(dr.get("status"), "success")
        self.assertIn("// v2", dr.get("result", {}).get("content", ""))

    def test_run_file_read(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "file_read",
            "target": "version.txt"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(len(data.get("result", {}).get("content", "")) > 0)

    def test_run_tool(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "tool",
            "target": "read_host_file",
            "payload": {"file_path": "version.txt"}
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("result", {}).get("status"), "success")

    def test_invalid_command_type(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "invalid_command_type_xyz",
            "target": "echo test"
        })
        self.assertEqual(resp.status_code, 400)

if __name__ == "__main__":
    unittest.main()
