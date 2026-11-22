"""Actual host-reader branch against temporary synthetic project documents only."""
import ast
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend/tools/tool_registry.py"
CONTRACT_SOURCE = ROOT / "backend/tools/tool_call_contract.py"
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def reader_for_fixture(project_root):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == "_resolve_host_read_path"]
    registry = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ToolRegistry")
    execute = next(node for node in registry.body if isinstance(node, ast.FunctionDef) and node.name == "execute_tool")
    branch = next(node for node in ast.walk(execute) if isinstance(node, ast.If)
                  and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name)
                  and node.test.left.id == "tool_name" and any(isinstance(value, ast.Constant)
                  and value.value == "read_host_file" for value in node.test.comparators))
    method = ast.parse("def read(arguments):\n    pass\n").body[0]
    method.body = copy.deepcopy(branch.body)

    class FixtureRoot(ast.NodeTransformer):
        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(str(project_root)), node) if node.value == r"C:\AI-BS" else node

    actual = FixtureRoot().visit(ast.Module(body=[*copy.deepcopy(helpers), method], type_ignores=[]))
    ast.fix_missing_locations(actual)
    namespace = {"os": os}
    exec(compile(actual, str(SOURCE), "exec"), namespace)
    return namespace["read"]


def registry_for_fixture(project_root):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    nodes = [node for node in tree.body if (isinstance(node, ast.FunctionDef)
             and node.name in {"_resolve_host_read_path", "_write_host_text_atomic"})
             or (isinstance(node, ast.ClassDef) and node.name == "ToolRegistry")]
    # Redirect only the production root constant; all dispatch and validation logic is actual source.
    class FixtureRoot(ast.NodeTransformer):
        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(str(project_root)), node) if node.value == r"C:\AI-BS" else node
    actual = FixtureRoot().visit(ast.Module(body=nodes, type_ignores=[]))
    ast.fix_missing_locations(actual)
    spec = importlib.util.spec_from_file_location("host_contract_fixture", CONTRACT_SOURCE)
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    namespace = {"os": os, "shutil": shutil, "validate_tool_call": contract.validate_tool_call,
                 "ToolCallValidationError": contract.ToolCallValidationError}
    exec(compile(actual, str(SOURCE), "exec"), namespace)
    return namespace["ToolRegistry"]


class ProjectDocumentLookupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aibs-host-doc-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        (self.root / "docs").mkdir()
        self.canonical = self.root / "docs/CODEX_HANDOFF.md"
        self.canonical.write_text("Synthetic handoff\nsecond line\n", encoding="utf-8")
        self.read = reader_for_fixture(self.root)

    def test_bare_known_document_resolves_to_canonical_docs_and_returns_real_metadata(self):
        result = self.read({"file_path": "CODEX_HANDOFF.md"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(Path(result["file_path"]), self.canonical)
        self.assertEqual(result["content"], self.canonical.read_bytes().decode("utf-8"))
        self.assertEqual(result["size_bytes"], self.canonical.stat().st_size)
        self.assertEqual(result["lines"], 2)
        self.assertEqual(result["sha256"], hashlib.sha256(self.canonical.read_bytes()).hexdigest())
        self.assertFalse(result["decoding_errors_replaced"])
        self.assertFalse(result["truncated"])

    def test_reader_preserves_exact_valid_utf8_bytes_and_reports_lossy_preview(self):
        path = self.root / "fixture.txt"
        for raw, replaced in (("synthetic é\r\nnext line\n".encode("utf-8"), False),
                              (b"synthetic invalid UTF8: \xff", True)):
            with self.subTest(replaced=replaced):
                path.write_bytes(raw)
                result = self.read({"file_path": str(path)})
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["size_bytes"], len(raw))
                self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(result["encoding"], "utf-8")
                self.assertEqual(result["decoding_errors_replaced"], replaced)
                self.assertFalse(result["truncated"])
                if not replaced:
                    self.assertEqual(result["content"].encode("utf-8"), raw)

    def test_existing_project_root_file_keeps_precedence_over_alias(self):
        (self.root / "CODEX_HANDOFF.md").write_text("Root document takes precedence", encoding="utf-8")
        result = self.read({"file_path": "CODEX_HANDOFF.md"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["content"], "Root document takes precedence")

    def test_explicit_absolute_missing_root_file_is_not_retargeted(self):
        result = self.read({"file_path": str(self.root / "CODEX_HANDOFF.md")})
        self.assertEqual(result["status"], "error")
        self.assertIn(str(self.root / "CODEX_HANDOFF.md"), result["message"])

    def test_explicit_relative_and_absolute_canonical_paths_keep_working(self):
        for target in ("docs/CODEX_HANDOFF.md", str(self.canonical)):
            with self.subTest(target=target):
                self.assertEqual(Path(self.read({"file_path": target})["file_path"]), self.canonical)

    def test_no_recursive_or_unknown_document_search(self):
        (self.root / "docs/PRIVATE_NOTE.md").write_text("Unrelated synthetic file", encoding="utf-8")
        result = self.read({"file_path": "PRIVATE_NOTE.md"})
        self.assertEqual(result["status"], "error")
        self.assertFalse((self.root / "PRIVATE_NOTE.md").exists())

    def test_alias_never_follows_a_docs_link_outside_the_project(self):
        self.canonical.unlink()
        self.canonical.parent.rmdir()
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "CODEX_HANDOFF.md").write_text("Outside synthetic document", encoding="utf-8")
        try:
            (self.root / "docs").symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Synthetic symlink creation unavailable: {type(error).__name__}")
        self.assertEqual(self.read({"file_path": "CODEX_HANDOFF.md"})["status"], "error")

    def test_actual_registry_contract_accepts_existing_read_and_canonical_alias(self):
        registry = registry_for_fixture(self.root)
        result = registry.execute_tool("read_host_file", {"file_path": "CODEX_HANDOFF.md"})
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(Path(result["file_path"]), self.canonical)

    def test_actual_registry_writer_keeps_distinct_preimages_for_repeated_saves(self):
        registry = registry_for_fixture(self.root)
        target = self.root / "fixture.txt"
        target.write_bytes(b"original fixture\r\n")
        with patch("time.time", return_value=1234567890):
            first = registry.execute_tool("write_host_file", {"file_path": str(target), "content": "first revision"})
            second = registry.execute_tool("write_host_file", {"file_path": str(target), "content": "second revision é"})
        self.assertEqual(first["status"], "success", first)
        self.assertEqual(second["status"], "success", second)
        self.assertNotEqual(first["backup_path"], second["backup_path"])
        self.assertEqual(Path(first["backup_path"]).read_bytes(), b"original fixture\r\n")
        self.assertEqual(Path(second["backup_path"]).read_bytes(), b"first revision")
        self.assertEqual(target.read_bytes(), "second revision é".encode("utf-8"))
        self.assertEqual(second["bytes_written"], len(target.read_bytes()))

    def test_atomic_publication_failure_does_not_truncate_original(self):
        registry = registry_for_fixture(self.root)
        target = self.root / "fixture.txt"
        target.write_bytes(b"original fixture")
        with patch.object(os, "replace", side_effect=OSError("synthetic publish failure")):
            result = registry.execute_tool("write_host_file", {"file_path": str(target), "content": "new revision"})
        self.assertEqual(result["status"], "error", result)
        self.assertEqual(target.read_bytes(), b"original fixture")
        self.assertEqual([file.read_bytes() for file in self.root.glob("fixture.txt.*.bak")], [b"original fixture"])
        self.assertEqual([file.read_bytes() for file in self.root.glob(".aibs-host-write-*.tmp")], [b"new revision"])

    def test_bad_host_arguments_are_rejected_before_any_write(self):
        registry = registry_for_fixture(self.root)
        target = self.root / "fixture.txt"
        target.write_bytes(b"preserved fixture")
        for arguments in ({"file_path": str(target), "content": {"bad": "type"}},
                          {"file_path": str(target), "content": "new", "unreviewed": True},
                          {"file_path": 7, "content": "new"}):
            with self.subTest(arguments=arguments):
                result = registry.execute_tool("write_host_file", arguments)
                self.assertEqual(result.get("error_code"), "INVALID_TOOL_CALL", result)
                self.assertEqual(target.read_bytes(), b"preserved fixture")
        self.assertEqual(list(self.root.glob("fixture.txt.*.bak")), [])

    def test_scan_contract_preserves_string_array_null_filters_and_depth_clamp(self):
        registry = registry_for_fixture(self.root)
        (self.root / "fixture.txt").write_text("synthetic fixture", encoding="utf-8")
        for filter_value in (".txt", [".txt"], None):
            with self.subTest(filter_value=filter_value):
                result = registry.execute_tool("scan_directory_tree", {
                    "dir_path": str(self.root), "depth": 500, "filter_ext": filter_value})
                self.assertEqual(result["status"], "success", result)
                self.assertEqual(result["depth_scanned"], 5)
                self.assertIn("fixture.txt", {row["name"] for row in result["tree"]})
        for invalid in (7, [7], {"bad": "type"}, True):
            with self.subTest(invalid=invalid):
                result = registry.execute_tool("scan_directory_tree", {"dir_path": str(self.root), "filter_ext": invalid})
                self.assertEqual(result.get("error_code"), "INVALID_TOOL_CALL", result)


if __name__ == "__main__":
    unittest.main()
