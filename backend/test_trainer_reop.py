import os
import json
import shutil
import unittest
from unittest.mock import patch, MagicMock

# Import the modules under test
import trainer
import ui_mutator


class TestTrainerREOP(unittest.TestCase):
    def setUp(self):
        self.ui_req_dir = os.path.join(os.path.dirname(__file__), "ui_mutations")
        os.makedirs(self.ui_req_dir, exist_ok=True)
        self.test_req_file = os.path.join(self.ui_req_dir, "test_mutation.json")

        # Clean up any leftover test components to avoid test pollution
        self.sovereignty_comp = os.path.join(
            ui_mutator.FRONTEND_SRC_DIR, "SovereigntyComponent.jsx"
        )
        self.broken_comp = os.path.join(
            ui_mutator.FRONTEND_SRC_DIR, "BrokenComponent.jsx"
        )

        for p in [self.sovereignty_comp, self.broken_comp]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

        # Backup App.jsx
        self.app_jsx_path = ui_mutator.APP_JSX_PATH
        self.app_jsx_bak = self.app_jsx_path + ".orig_bak"
        if os.path.exists(self.app_jsx_path):
            shutil.copy(self.app_jsx_path, self.app_jsx_bak)

    def tearDown(self):
        # Restore App.jsx
        if os.path.exists(self.app_jsx_bak):
            shutil.copy(self.app_jsx_bak, self.app_jsx_path)
            os.remove(self.app_jsx_bak)
        if os.path.exists(self.test_req_file):
            try:
                os.remove(self.test_req_file)
            except:
                pass
        for p in [self.sovereignty_comp, self.broken_comp]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

    @patch("requests.post")
    @patch("trainer.audit_code")
    def test_sovereignty_rejection(self, mock_audit, mock_post):
        # Sovereignty check fails at the audit gate, so we simulate the auditor returning False
        mock_audit.return_value = False

        # Mock trainer generator LLM response
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "response": "import boto3\nexport default function SovereigntyComponent() { return <div>AWS</div> }"
            },
        )

        # Write request payload
        payload = {
            "tab_id": "test_sovereignty",
            "tab_name": "Sovereignty Test",
            "component_name": "SovereigntyComponent",
            "human_idea": "Build a component that uses AWS cloud services.",
        }
        with open(self.test_req_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        print("\n--- Running Sovereignty Check Test ---")
        trainer.scan_for_ui_mutations()

        # Verify that the component was NOT created in src
        self.assertFalse(
            os.path.exists(self.sovereignty_comp),
            "Sovereignty component should not be deployed!",
        )
        print("Sovereignty check test passed. External imports blocked successfully.")

    @patch("requests.post")
    @patch("trainer.audit_code")
    def test_broken_code_rollback(self, mock_audit, mock_post):
        # 1. Auditor approves it (so it proceeds to inject_ui_tab)
        mock_audit.return_value = True

        # 2. Mock LLM to return invalid JSX (syntax error)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "response": "export default function BrokenComponent() { return ( <div>Unclosed tag ) }"
            },
        )

        payload = {
            "tab_id": "test_broken",
            "tab_name": "Broken Test",
            "component_name": "BrokenComponent",
            "human_idea": "Build a component with broken syntax.",
        }
        with open(self.test_req_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        print("\n--- Running Broken Code Rollback Test ---")
        trainer.scan_for_ui_mutations()

        # Verify that the component was rolled back and deleted
        self.assertFalse(
            os.path.exists(self.broken_comp),
            "Broken component should have been deleted during rollback!",
        )
        print(
            "Broken code rollback test passed. App.jsx protected from compilation errors."
        )


if __name__ == "__main__":
    unittest.main()
