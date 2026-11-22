"""Synthetic generated-script regression; no host diagnostics or actual builder runs."""
import ast
import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend/core/real_system_tools.py"


class ProgramBuilderTemplateTests(unittest.TestCase):
    def route_with_synthetic_tools(self, prompt):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "check_and_execute_system_tools")
        routes = ["execute_real_oversight_monitoring", "execute_real_spaces_overview",
                  "execute_real_space_retrieval", "execute_real_space_ingestion",
                  "execute_program_builder_from_prompt", "execute_real_osint_lead_scan",
                  "execute_real_matrix_doctor", "execute_real_active_game_scan",
                  "execute_real_hardware_telemetry"]
        from typing import Optional
        calls = []
        namespace = {"Optional": Optional}
        for route in routes:
            def synthetic(*args, _route=route, **kwargs):
                calls.append(_route)
                return _route
            namespace[route] = synthetic
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
        result = namespace[function.name](prompt)
        return result, calls

    def prepare(self, prompt="build a fixture program", receipt=None):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "execute_program_builder_from_prompt")
        captured = {}

        class Builder:
            @staticmethod
            def build_program(**kwargs):
                captured.update(kwargs)
                if receipt is not None:
                    return copy.deepcopy(receipt)
                return {"execution": {"executed": True, "status": "success", "exit_code": 0,
                                       "stdout": "synthetic scaffold output"},
                        "build": {"executed": False, "status": "not_run", "exit_code": 0},
                        "project_name": kwargs["project_name"], "zip_name": "fixture.zip",
                        "code_quality": {"valid": True, "files": {"main.py": {"valid": True}}},
                        "files": [{"name": "main.py", "size_bytes": 100},
                                  {"name": "README.md", "size_bytes": 20}]}

        builder_module = types.ModuleType("core.program_builder_engine")
        builder_module.AutonomousProgramBuilder = Builder
        core = types.ModuleType("core")
        core.__path__ = []
        clock = types.ModuleType("time")
        clock.time = lambda: 123
        clock.strftime = lambda _format: "synthetic timestamp"
        clock.sleep = lambda _seconds: None
        # Deliberately omit platform here: it belongs to the generated script.
        namespace = {"time": clock}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
        with patch.dict(sys.modules, {"core": core, "core.program_builder_engine": builder_module}):
            result = namespace[function.name](prompt)
        script = next(file["content"] for file in captured["files"] if file["path"] == "main.py")
        return result, captured, script, clock

    def execute_synthetic_scaffold(self, script, clock, extra=None):
        compiled = compile(script, "synthetic-generated-main.py", "exec")
        platform = types.ModuleType("platform")
        platform.system = lambda: "SyntheticOS"
        platform.release = lambda: "SyntheticRelease"
        platform.machine = lambda: "SyntheticMachine"
        output = io.StringIO()
        namespace = {"__name__": "__main__", **(extra or {})}
        with patch.dict(sys.modules, {"platform": platform, "time": clock}), redirect_stdout(output):
            exec(compiled, namespace)
        return output.getvalue(), namespace

    def test_platform_is_resolved_by_generated_program_not_generator(self):
        result, captured, script, clock = self.prepare()
        self.assertIn("AI-BS Starter Scaffold Receipt", result)
        self.assertIn('{platform.system()}', script)
        output, _ = self.execute_synthetic_scaffold(script, clock)
        self.assertIn("SyntheticOS SyntheticRelease (SyntheticMachine)", output)
        # Preserve the existing builder handoff; tests intercept all execution.
        self.assertEqual(captured["entrypoint"], "main.py")
        self.assertTrue(captured["run_immediately"])
        self.assertEqual({file["path"] for file in captured["files"]}, {"main.py", "README.md", "run.bat"})

    def test_objective_quotes_newlines_braces_are_inert_data(self):
        prompts = ['build a program called "Example"', "build a program for Sean's notes",
                   'build a program with triple quotes """ and a newline\nnext line',
                   'build a program for C:\\notes\\draft.txt with é and {missing_name}',
                   'build a program with {side_effect()} and nested {{braces}}']
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                _, _, script, clock = self.prepare(prompt)
                side_effects = []
                output, namespace = self.execute_synthetic_scaffold(
                    script, clock, {"side_effect": lambda: side_effects.append("executed")})
                self.assertEqual(namespace["TARGET_OBJECTIVE"], prompt)
                self.assertEqual(side_effects, [])
                self.assertIn(ascii(prompt), output)

    def test_scaffold_output_and_receipt_do_not_claim_requested_work_completed(self):
        result, _, script, clock = self.prepare("build a program to monitor CPU usage")
        output, _ = self.execute_synthetic_scaffold(script, clock)
        self.assertIn("SCAFFOLD SMOKE RUN PASSED", result)
        self.assertIn("requested program logic is not implemented", output)
        self.assertIn("No telemetry worker pipeline or vault synchronization was performed", output)
        self.assertNotIn("[1/3]", output)
        self.assertNotIn("[2/3]", output)
        self.assertNotIn("[3/3]", output)
        self.assertNotIn("ready for immediate deployment", result)
        self.assertIn("deployment readiness remain unverified", result)
        self.assertIn("Compile check passed", result)
        self.assertIn("Written; source check not reported", result)

    def test_blocked_quality_receipt_reports_errors_without_package_or_success(self):
        receipt = {"status": "error", "project_name": "fixture", "files": [],
                   "code_quality": {"valid": False, "errors": ["fixture syntax failed"]},
                   "execution": {"executed": False, "status": "blocked_by_quality_gate",
                                 "exit_code": 1, "stderr": "not executed"}}
        result, _, _, _ = self.prepare(receipt=receipt)
        self.assertIn("`BLOCKED`", result)
        self.assertIn("fixture syntax failed", result)
        self.assertIn("ZIP Package:** Not reported", result)
        self.assertNotIn("SCAFFOLD SMOKE RUN PASSED", result)
        self.assertNotIn("Error in autonomous program builder", result)

    def test_zero_exit_without_execution_is_not_a_pass(self):
        result, _, _, _ = self.prepare(receipt={"project_name": "fixture", "files": [],
            "execution": {"executed": False, "status": "not_run", "exit_code": 0}})
        self.assertIn("SCAFFOLD PREPARED; NOT RUN", result)
        self.assertNotIn("SCAFFOLD SMOKE RUN PASSED", result)
        self.assertNotIn("Process completed with exit code 0", result)

    def test_error_status_with_zero_exit_retains_failure_and_stderr(self):
        result, _, _, _ = self.prepare(receipt={"project_name": "fixture", "files": [],
            "execution": {"executed": True, "status": "error", "exit_code": 0,
                          "stdout": "", "stderr": "synthetic runtime failure ``` retained"}})
        self.assertIn("SCAFFOLD SMOKE RUN FAILED", result)
        self.assertIn("synthetic runtime failure ` ` ` retained", result)
        self.assertNotIn("SCAFFOLD SMOKE RUN PASSED", result)

    def test_dispatcher_uses_a_generic_tool_result_banner(self):
        path = ROOT / "backend/core/sovereign_reasoning/dispatcher.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        tools_branch = next(node for node in ast.walk(tree)
                            if isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                            and node.test.id == "real_tool_result")
        banner = next(node.value.value for node in ast.walk(tools_branch)
                      if isinstance(node, ast.Yield) and isinstance(node.value, ast.Constant)
                      and isinstance(node.value.value, str))
        self.assertIn("Local Tool Result", banner)
        self.assertNotIn("Telemetry", banner)
        self.assertNotIn("Diagnostics", banner)

    def test_explicit_leading_creation_and_named_builder_requests_still_route(self):
        prompts = ["build a program to record fixture data", "create a script", "write a program",
                   "code a program", "generate a program", "build an app", "create an app",
                   "make a scaffold", "Please, make me a simple Python program",
                   "Can you build a program?", "Could you please create a script?",
                   "I want you to generate an app", "I need to write a script",
                   "I'd like you to make a starter scaffold", "Please run the program builder",
                   "Use the AI-BS program builder", "Can you start program builder?"]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                route, calls = self.route_with_synthetic_tools(prompt)
                self.assertEqual(route, "execute_program_builder_from_prompt")
                self.assertEqual(calls, ["execute_program_builder_from_prompt"])

    def test_descriptive_or_quoted_builder_mentions_do_not_create_projects(self):
        prompts = ["why did the program builder fail to show cpu usage?",
                   "explain the program builder", "the program builder failed",
                   "Explain why 'build a program' produced a placeholder",
                   '"create a script" was the previous request',
                   "Can you explain the program builder failure?",
                   "I want you to explain the program builder output",
                   "do not build a program", "automatic program status"]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                _, calls = self.route_with_synthetic_tools(prompt)
                self.assertNotIn("execute_program_builder_from_prompt", calls)
        route, calls = self.route_with_synthetic_tools(prompts[0])
        # Other route behavior is intentionally preserved, including this read-only fallback.
        self.assertEqual(route, "execute_real_hardware_telemetry")
        self.assertEqual(calls, ["execute_real_hardware_telemetry"])

    def test_existing_other_registered_tool_routes_are_preserved(self):
        cases = {"monitor all 43 modules": "execute_real_oversight_monitoring",
                 "spaces overview": "execute_real_spaces_overview",
                 "search all spaces": "execute_real_space_retrieval",
                 "save this to database": "execute_real_space_ingestion",
                 "commercial leads": "execute_real_osint_lead_scan",
                 "run diagnostic scan": "execute_real_matrix_doctor",
                 "what game is active": "execute_real_active_game_scan",
                 "show cpu usage": "execute_real_hardware_telemetry"}
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                route, calls = self.route_with_synthetic_tools(prompt)
                self.assertEqual(route, expected)
                self.assertEqual(calls, [expected])


if __name__ == "__main__":
    unittest.main()
