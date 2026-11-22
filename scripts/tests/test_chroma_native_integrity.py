"""Synthetic, read-only integrity checks; no Chroma/native/database imports."""
from pathlib import Path
import hashlib
import importlib.util
import struct
import tempfile
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[2] / "backend/core/chroma_native_integrity.py"
SPEC = importlib.util.spec_from_file_location("aibs_chroma_native_integrity", MODULE_PATH)
integrity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(integrity)


class ChromaNativeIntegrityTests(unittest.TestCase):
    def fixture(self, folder, labels=(11, 22), deleted=(), bad_upper=False, bad_edge=False):
        root = Path(folder)
        root.mkdir(exist_ok=True)
        count = len(labels)
        root.joinpath("header.bin").write_bytes(
            struct.pack("<iQQQQQQiIQQQdQ", 1, 0, max(100, count), count,
                        36, 28, 20, 1 if count else -1,
                        0 if count else 0xffffffff, 2, 4, 2, .36, 100)
        )
        data = bytearray()
        for index, label in enumerate(labels):
            record = bytearray(36)
            record[2] = int(index in deleted)
            struct.pack_into("<Q", record, 28, label)
            data.extend(record)
        root.joinpath("data_level0.bin").write_bytes(data)
        # Unused L2 normalization memory is not a uint32 array of link lengths.
        root.joinpath("length.bin").write_bytes(b"\xff" * max(100, count) * 4)
        if not count:
            upper = b""
        elif bad_upper:
            upper = struct.pack("<I", 7340) + bytes(12) + struct.pack("<I", 0)
        else:
            links = bytearray(12)
            if bad_edge:
                struct.pack_into("<H", links, 0, 1)
                struct.pack_into("<I", links, 4, 1)
            upper = struct.pack("<I", 12) + links + struct.pack("<I", 0) * (count - 1)
        root.joinpath("link_lists.bin").write_bytes(upper)
        return root

    @staticmethod
    def codes(result):
        return {item["code"] for item in result["errors"]}

    def test_valid_noncontiguous_labels_preserve_all_source_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            before = {p.name: hashlib.sha256(p.read_bytes()).digest() for p in root.iterdir()}
            result = integrity.inspect_hnsw_segment(root, expected_dimension=2)
            self.assertEqual(result["status"], "STATIC_CHECKS_PASS")
            self.assertTrue(result["known_format_checks_pass"])
            self.assertFalse(result["native_runtime_tested"])
            self.assertFalse(result["data_recovery_complete"])
            self.assertNotIn("safe_to_open_native", result)
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).digest() for p in root.iterdir()})

    def test_duplicate_active_labels_are_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp, (11, 11)))
            self.assertEqual(result["status"], "CORRUPT")
            self.assertIn("DUPLICATE_ACTIVE_LABELS", self.codes(result))
            self.assertEqual(result["active_duplicate_records"], 1)

    def test_deleted_record_does_not_count_as_duplicate_active_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp, (11, 11), deleted=(1,)))
            self.assertNotIn("DUPLICATE_ACTIVE_LABELS", self.codes(result))
            self.assertEqual(result["deleted_records"], 1)

    def test_observed_7340_upper_link_prefix_is_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp, bad_upper=True))
            self.assertEqual(result["status"], "CORRUPT")
            self.assertIn("UPPER_LINK_LENGTH", self.codes(result))

    def test_upper_edge_requires_target_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp, bad_edge=True))
            self.assertIn("UPPER_NEIGHBOR_LEVEL", self.codes(result))

    def test_empty_index_accepts_unused_normalization_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp, ()))
            self.assertEqual(result["status"], "STATIC_CHECKS_PASS")

    def test_dimension_mismatch_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp), expected_dimension=3)
            self.assertIn("DIMENSION_MISMATCH", self.codes(result))

    def test_unsupported_header_is_not_called_corrupt_or_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            root.joinpath("header.bin").write_bytes(b"unknown")
            result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "UNSUPPORTED")
            self.assertFalse(result["known_format_checks_pass"])

    def test_truncated_level0_is_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            root.joinpath("data_level0.bin").write_bytes(b"")
            result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "CORRUPT")
            self.assertIn("LEVEL0_STORAGE_SIZE", self.codes(result))

    def test_record_budget_is_unverified_not_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp), max_records=1)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("INSPECTION_LIMIT", self.codes(result))

    def test_file_budget_precedes_any_file_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            with mock.patch.object(integrity.os, "open", side_effect=AssertionError("file budget must precede open")):
                result = integrity.inspect_hnsw_segment(root, max_file_bytes=16)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("INSPECTION_LIMIT", self.codes(result))

    def test_upper_payload_budget_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = integrity.inspect_hnsw_segment(self.fixture(tmp), max_upper_bytes_per_node=8)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("INSPECTION_LIMIT", self.codes(result))

    def test_header_is_read_with_a_bounded_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            requests = []
            read_exact = integrity._read_exact
            def observed(stream, count):
                requests.append(count)
                return read_exact(stream, count)
            with mock.patch.object(integrity, "_read_exact", side_effect=observed):
                result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "STATIC_CHECKS_PASS")
            self.assertIn(100, requests)
            self.assertLessEqual(max(requests), 100)

    def test_changed_file_cannot_be_reported_static_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            read_exact = integrity._read_exact
            changed = False
            def append_during_read(stream, count):
                nonlocal changed
                value = read_exact(stream, count)
                if count == 36 and not changed:
                    changed = True
                    with root.joinpath("data_level0.bin").open("ab") as target:
                        target.write(b"changed")
                return value
            with mock.patch.object(integrity, "_read_exact", side_effect=append_during_read):
                result = integrity.inspect_hnsw_segment(root)
            self.assertTrue(changed)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("INSPECTION_CHANGED", self.codes(result))
            self.assertFalse(result["known_format_checks_pass"])

    def test_short_read_is_unverified_and_does_not_escape_as_struct_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            read_exact = integrity._read_exact
            def short_read(stream, count):
                return b"" if count == 36 else read_exact(stream, count)
            with mock.patch.object(integrity, "_read_exact", side_effect=short_read):
                result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("SHORT_OR_CHANGED_READ", self.codes(result))

    def test_windows_reparse_file_is_rejected_before_any_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            original_stat = integrity._stat_path
            class ReparseStat:
                st_file_attributes = 0x400
                def __init__(self, real): self.real = real
                def __getattr__(self, name): return getattr(self.real, name)
            def reparse_header(path):
                info = original_stat(path)
                return ReparseStat(info) if Path(path).name == "header.bin" else info
            with mock.patch.object(integrity, "_stat_path", side_effect=reparse_header):
                with mock.patch.object(integrity.os, "open", side_effect=AssertionError("reparse must precede open")):
                    result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "UNSUPPORTED")
            self.assertIn("LINK_NOT_ALLOWED", self.codes(result))

    def test_filesystem_store_scan_never_requires_sqlite_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("chroma.sqlite3").write_bytes(b"not SQLite; filesystem-only test")
            self.fixture(root / "segment", bad_upper=True)
            result = integrity.inspect_chroma_store(root)
            self.assertEqual(result["status"], "CORRUPT")
            self.assertFalse(result["sqlite_opened"])
            self.assertFalse(result["native_runtime_tested"])
            self.assertNotIn("safe_to_open_native", result)

    def test_store_directory_budget_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("chroma.sqlite3").write_bytes(b"fixture")
            self.fixture(root / "first")
            self.fixture(root / "second")
            result = integrity.inspect_chroma_store(root, max_segments=1)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertIn("INSPECTION_LIMIT", self.codes(result))

    def test_store_without_persisted_segments_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("chroma.sqlite3").write_bytes(b"fixture")
            result = integrity.inspect_chroma_store(root)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertFalse(result["known_format_checks_pass"])
            self.assertIn("NO_PERSISTED_SEGMENTS", self.codes(result))

    def test_windows_reparse_directory_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            original_stat = integrity._stat_path
            class ReparseStat:
                st_file_attributes = 0x400
                def __init__(self, real): self.real = real
                def __getattr__(self, name): return getattr(self.real, name)
            def reparse_root(path):
                info = original_stat(path)
                return ReparseStat(info) if Path(path) == root else info
            with mock.patch.object(integrity, "_stat_path", side_effect=reparse_root):
                with mock.patch.object(integrity.os, "open", side_effect=AssertionError("junction must precede open")):
                    result = integrity.inspect_hnsw_segment(root)
            self.assertEqual(result["status"], "UNSUPPORTED")
            self.assertIn("LINK_NOT_ALLOWED", self.codes(result))

    def test_new_persisted_segment_during_store_scan_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("chroma.sqlite3").write_bytes(b"filesystem-only fixture")
            self.fixture(root / "existing")
            scan = integrity._scan_open_files
            added = False
            def add_segment(*args, **kwargs):
                nonlocal added
                if not added:
                    added = True
                    self.fixture(root / "arrived-during-scan", bad_upper=True)
                return scan(*args, **kwargs)
            with mock.patch.object(integrity, "_scan_open_files", side_effect=add_segment):
                result = integrity.inspect_chroma_store(root)
            self.assertTrue(added)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertFalse(result["known_format_checks_pass"])
            self.assertIn("INSPECTION_CHANGED", self.codes(result))

    def test_preexisting_empty_directory_becoming_segment_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("chroma.sqlite3").write_bytes(b"filesystem-only fixture")
            self.fixture(root / "existing")
            root.joinpath("previously-empty").mkdir()
            scan = integrity._scan_open_files
            added = False
            def materialize_segment(*args, **kwargs):
                nonlocal added
                if not added:
                    added = True
                    self.fixture(root / "previously-empty", bad_upper=True)
                return scan(*args, **kwargs)
            with mock.patch.object(integrity, "_scan_open_files", side_effect=materialize_segment):
                result = integrity.inspect_chroma_store(root)
            self.assertTrue(added)
            self.assertEqual(result["status"], "UNVERIFIED")
            self.assertFalse(result["known_format_checks_pass"])
            self.assertIn("INSPECTION_CHANGED", self.codes(result))


if __name__ == "__main__":
    unittest.main()
