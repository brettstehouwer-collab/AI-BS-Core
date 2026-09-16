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
        self.assertIn("powershell", data.get("supported_command_types", []))

    def test_run_powershell(self):
        resp = self.client.post("/api/executive/run", json={
            "command_type": "powershell",
            "target": "Write-Output 'EXECUTIVE_TEST_OK'"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("EXECUTIVE_TEST_OK", data.get("stdout", ""))

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
