"""Temporary binary fixtures; no Chroma, database, or production application."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/inspect_chroma_store.py"
HEADER = struct.Struct("<iQQQQQQiIQQQdQ")


class ChromaInspectorCliTests(unittest.TestCase):
    def load_cli(self):
        self.assertTrue(SCRIPT.is_file(), "The read-only Chroma inspection CLI is missing")
        spec = importlib.util.spec_from_file_location("chroma_inspector_cli_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"chromadb": None, "chromadb_rust_bindings": None}):
            spec.loader.exec_module(module)
        return module

    def fixture(self, root, corrupt=False):
        # Deliberately not a SQLite database: this tool must never open it.
        (root / "chroma.sqlite3").write_bytes(b"filesystem-only fixture")
        segment = root / "segment"
        segment.mkdir()
        (segment / "header.bin").write_bytes(
            HEADER.pack(1, 0, 100, 2, 36, 28, 20, 1, 0, 2, 4, 2, 0.36, 100)
        )
        records = bytearray(72)
        struct.pack_into("<Q", records, 28, 11)
        struct.pack_into("<Q", records, 64, 22)
        (segment / "data_level0.bin").write_bytes(records)
        (segment / "length.bin").write_bytes(b"\xff" * 400)
        upper = struct.pack("<I", 7340 if corrupt else 12) + bytes(12) + struct.pack("<I", 0)
        (segment / "link_lists.bin").write_bytes(upper)

    def invoke(self, module, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.dict(
            "sys.modules", {"chromadb": None, "chromadb_rust_bindings": None}
        ):
            code = module.main(["--store", str(root)])
        return code, json.loads(output.getvalue())

    def test_import_does_not_load_native_client(self):
        module = self.load_cli()
        self.assertTrue(callable(module.main))

    def test_missing_store_is_unverified_and_is_not_created(self):
        module = self.load_cli()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "absent"
            code, result = self.invoke(module, root)
            self.assertEqual(code, 3)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertFalse(root.exists())

    def test_static_pass_does_not_claim_native_or_database_health(self):
        module = self.load_cli()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            code, result = self.invoke(module, root)
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "STATIC_CHECKS_PASS")
            self.assertFalse(result["native_runtime_tested"])
            self.assertFalse(result["sqlite_opened"])
            self.assertFalse(result["data_recovery_complete"])

    def test_corrupt_graph_is_reported_without_changing_original_bytes(self):
        module = self.load_cli()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, corrupt=True)
            before = {str(p): hashlib.sha256(p.read_bytes()).digest() for p in root.rglob("*") if p.is_file()}
            code, result = self.invoke(module, root)
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "CORRUPT")
            self.assertIn("UPPER_LINK_LENGTH", [e["code"] for s in result["segments"] for e in s["errors"]])
            self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).digest() for p in root.rglob("*") if p.is_file()})

    def test_unexpected_error_does_not_echo_exception_contents(self):
        module = self.load_cli()
        output = io.StringIO()
        with patch.object(module, "_inspect_store", side_effect=RuntimeError("synthetic-private-content")), contextlib.redirect_stdout(output):
            self.assertEqual(module.main(["--store", "unused-fixture"]), 3)
        self.assertEqual(json.loads(output.getvalue())["status"], "UNVERIFIED")
        self.assertNotIn("synthetic-private-content", output.getvalue())


if __name__ == "__main__":
    unittest.main()
