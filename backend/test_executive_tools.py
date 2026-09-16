"""
test_executive_tools.py
━━━━━━━━━━━━━━━━━━━━━━━━
Automated verification suite for AI-BS Executive IDE Tools & Executive Engine.
- Tests read_host_file across host paths
- Tests write_host_file with automated .bak backup creation
- Tests scan_directory_tree with extensions filter
- Tests execute_powershell_command live
- Tests manage_daemon_state port probe
- Tests ToolRegistry execute_tool integration
"""

import os
import sys
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "tools")))

from tools.tool_registry import ToolRegistry


class TestExecutiveTools(unittest.TestCase):
    def setUp(self):
        self.sandbox_dir = r"C:\AI-BS\sandbox"
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.test_file = os.path.join(self.sandbox_dir, f"test_exec_{int(time.time())}.txt")

    def tearDown(self):
        if os.path.exists(self.test_file):
            try:
                os.remove(self.test_file)
            except Exception:
                pass

    def test_01_read_host_file(self):
        # Read known file version.txt
        res = ToolRegistry.execute_tool("read_host_file", {"file_path": r"C:\AI-BS\version.txt"})
        self.assertEqual(res.get("status"), "success")
        self.assertIn("content", res)
        self.assertTrue(len(res["content"]) > 0)
        self.assertTrue(res["size_bytes"] > 0)

    def test_02_write_host_file_with_backup(self):
        # Initial write
        res1 = ToolRegistry.execute_tool("write_host_file", {
            "file_path": self.test_file,
            "content": "Line 1: Initial content"
        })
        self.assertEqual(res1.get("status"), "success")
        self.assertIsNone(res1.get("backup_path"))

        # Mutate file - should create .bak backup
        time.sleep(1)
        res2 = ToolRegistry.execute_tool("write_host_file", {
            "file_path": self.test_file,
            "content": "Line 1: Mutated content\nLine 2: New entry"
        })
        self.assertEqual(res2.get("status"), "success")
        self.assertIsNotNone(res2.get("backup_path"))
        self.assertTrue(os.path.exists(res2["backup_path"]))

        # Read back mutated file
        read_res = ToolRegistry.execute_tool("read_host_file", {"file_path": self.test_file})
        self.assertEqual(read_res.get("status"), "success")
        self.assertIn("Mutated content", read_res["content"])

        # Clean up backup
        try:
            os.remove(res2["backup_path"])
        except Exception:
            pass

    def test_03_scan_directory_tree(self):
        res = ToolRegistry.execute_tool("scan_directory_tree", {
            "dir_path": r"C:\AI-BS\backend\tools",
            "depth": 2,
            "filter_ext": ".py"
        })
        self.assertEqual(res.get("status"), "success")
        self.assertIn("tree", res)
        self.assertTrue(len(res["tree"]) > 0)
        # Check that tool_registry.py is in the tree
        names = [item["name"] for item in res["tree"] if item.get("type") == "file"]
        self.assertIn("tool_registry.py", names)

    def test_04_execute_powershell_command(self):
        res = ToolRegistry.execute_tool("execute_powershell_command", {
            "command": "Write-Output 'AIBS_EXECUTIVE_OK'"
        })
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("returncode"), 0)
        self.assertIn("AIBS_EXECUTIVE_OK", res.get("stdout", ""))

    def test_05_manage_daemon_state_probe(self):
        # Probe port 11434 (Ollama) or 8080 (FastAPI)
        res = ToolRegistry.execute_tool("manage_daemon_state", {
            "port": 11434,
            "action": "status"
        })
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("port"), 11434)
        self.assertIn("is_listening", res)

    def test_06_declarations_schema(self):
        decls = ToolRegistry.get_tool_declarations()
        names = [d["name"] for d in decls]
        expected = [
            "read_host_file",
            "write_host_file",
            "scan_directory_tree",
            "execute_powershell_command",
            "execute_wsl_command",
            "manage_daemon_state",
            "execute_subsystem_action"
        ]
        for exp in expected:
            self.assertIn(exp, names, f"Missing tool declaration: {exp}")


if __name__ == "__main__":
    unittest.main()
