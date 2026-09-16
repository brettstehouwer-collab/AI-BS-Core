import os
import time
import unittest
from tools.tool_registry import ToolRegistry


class TestCodingAgentTools(unittest.TestCase):
    def test_validate_syntax_python(self):
        valid_code = "def hello():\n    return 42\n"
        res = ToolRegistry.execute_tool("validate_syntax", {"code": valid_code, "language": "python"})
        self.assertEqual(res.get("status"), "valid")

        invalid_code = "def hello(\n    return 42"
        res2 = ToolRegistry.execute_tool("validate_syntax", {"code": invalid_code, "language": "python"})
        self.assertEqual(res2.get("status"), "invalid")
        self.assertIn("line", res2)

    def test_validate_syntax_json(self):
        valid_json = '{"name": "Stehouwer LLM", "ports": [11434, 11435]}'
        res = ToolRegistry.execute_tool("validate_syntax", {"code": valid_json, "language": "json"})
        self.assertEqual(res.get("status"), "valid")

        invalid_json = '{"name": "broken", }'
        res2 = ToolRegistry.execute_tool("validate_syntax", {"code": invalid_json, "language": "json"})
        self.assertEqual(res2.get("status"), "invalid")

    def test_validate_syntax_jsx(self):
        valid_jsx = "import React from 'react'; export default function Hello() { return <div>Hello World</div>; }"
        res = ToolRegistry.execute_tool("validate_syntax", {"code": valid_jsx, "language": "jsx"})
        self.assertEqual(res.get("status"), "valid")

        invalid_jsx = "import React from 'react'; export default function Hello() { return <div>Hello World; }"
        res2 = ToolRegistry.execute_tool("validate_syntax", {"code": invalid_jsx, "language": "jsx"})
        self.assertEqual(res2.get("status"), "invalid")

    def test_patch_host_file(self):
        test_file = r"C:\AI-BS\backend\scratch\test_patch_target.py"
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Target Test File\ndef calculate(x):\n    return x * 2\n")

        # Test non-existent target block
        res_fail = ToolRegistry.execute_tool("patch_host_file", {
            "file_path": test_file,
            "target_block": "def non_existent(): pass",
            "replacement_block": "def non_existent(): return 1",
            "validate_syntax": True
        })
        self.assertEqual(res_fail.get("status"), "error")
        self.assertIn("not found", res_fail.get("message"))

        # Test invalid syntax pre-flight rejection
        res_syntax_err = ToolRegistry.execute_tool("patch_host_file", {
            "file_path": test_file,
            "target_block": "return x * 2",
            "replacement_block": "return (x * 2",  # Missing closing paren
            "validate_syntax": True
        })
        self.assertEqual(res_syntax_err.get("status"), "error")
        self.assertIn("Pre-flight syntax check failed", res_syntax_err.get("message"))

        # Test successful patch
        res_ok = ToolRegistry.execute_tool("patch_host_file", {
            "file_path": test_file,
            "target_block": "return x * 2",
            "replacement_block": "return x * 4",
            "validate_syntax": True
        })
        self.assertEqual(res_ok.get("status"), "success")
        self.assertTrue(os.path.exists(res_ok.get("backup_path")))

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("return x * 4", content)

        # Cleanup test files
        if os.path.exists(test_file):
            os.unlink(test_file)
        if os.path.exists(res_ok.get("backup_path")):
            os.unlink(res_ok.get("backup_path"))

    def test_write_mirror_component(self):
        comp_name = "TestMirrorParityCheck.jsx"
        content = "import React from 'react'; export default function TestMirrorParityCheck() { return <div>Parity 100%</div>; }"
        res = ToolRegistry.execute_tool("write_mirror_component", {
            "component_filename": comp_name,
            "content": content
        })
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("parity"), "100%")
        self.assertEqual(res.get("mirrors_updated"), 4)

        # Clean up test mirror files
        mirror_paths = [
            os.path.join(r"C:\AI-BS\frontend\src\components", comp_name),
            os.path.join(r"C:\AI-BS\frontend\components", comp_name),
            os.path.join(r"C:\AI-BS\frontend\src\components\components", comp_name),
            os.path.join(r"C:\AI-BS\frontend\components\components", comp_name)
        ]
        for p in mirror_paths:
            if os.path.exists(p):
                os.unlink(p)

    def test_lookup_symbol(self):
        res = ToolRegistry.execute_tool("lookup_symbol", {
            "query": "telemetry",
            "scope": "all",
            "limit": 10
        })
        self.assertEqual(res.get("status"), "success")
        self.assertGreater(len(res.get("matches")), 0)
        self.assertLess(res.get("execution_time_ms"), 1500)  # Sub-second execution


if __name__ == "__main__":
    unittest.main()
