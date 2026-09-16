import os
import sys
import unittest
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.powershell_process_engine import PowerShellProcessEngine
from tools.tool_registry import ToolRegistry
from core.typst_pandoc_engine import TypstPandocEngine
import core.sovereign_reasoning.dispatcher as dispatcher
import routers.chat_router as chat_router


class Test90MinTimeoutAndBackendToggle(unittest.TestCase):
    def test_powershell_engine_default_timeout(self):
        import inspect
        sig = inspect.signature(PowerShellProcessEngine.execute_powershell)
        self.assertEqual(sig.parameters["timeout_seconds"].default, 5400)
        print("PASS: PowerShellProcessEngine default timeout is 5400s (90 min)")

    def test_tool_registry_declarations(self):
        decls = {d["name"]: d for d in ToolRegistry.get_tool_declarations()}
        for tool_name in ["run_ecosystem_script", "run_ecosystem_command", "execute_powershell_command", "execute_wsl_command"]:
            self.assertIn(tool_name, decls)
            desc = decls[tool_name]["parameters"]["properties"]["timeout_seconds"]["description"]
            self.assertIn("5400", desc)
            print(f"PASS: {tool_name} tool declaration includes 5400s (90 min)")

    def test_chat_tab_mirror_parity_and_controls(self):
        mirror_paths = [
            r"C:\AI-BS\frontend\src\components\ChatTab.jsx",
            r"C:\AI-BS\frontend\components\ChatTab.jsx",
            r"C:\AI-BS\frontend\src\components\components\ChatTab.jsx",
            r"C:\AI-BS\frontend\components\components\ChatTab.jsx"
        ]
        for p in mirror_paths:
            self.assertTrue(os.path.exists(p), f"Mirror path {p} not found")
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            self.assertIn("isBackendDisabled", code)
            self.assertIn("abortControllerRef", code)
            self.assertIn("handleStopOrToggleBackend", code)
            self.assertIn("5400000", code)
            self.assertIn("Disable Backend", code)
            self.assertIn("Enable Backend", code)
            self.assertIn("Stop Process", code)
            print(f"PASS: {p} verified with 90m timeout and Disable/Enable Backend controls")

    def test_mobile_chat_timeout(self):
        mobile_path = r"C:\AI-BS\frontend\src\components\MobileGeminiChat.jsx"
        with open(mobile_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("5400000", code)
        print("PASS: MobileGeminiChat.jsx verified with 5400000ms timeout")


if __name__ == "__main__":
    unittest.main()
