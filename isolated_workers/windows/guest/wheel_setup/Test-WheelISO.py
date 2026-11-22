"""Trusted host infrastructure tests; never mounts media or launches a guest program."""
import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("wheel_iso", Path(__file__).with_name("Verify-WheelISO.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def both32(value):
    return struct.pack("<I", value) + struct.pack(">I", value)


def both16(value):
    return struct.pack("<H", value) + struct.pack(">H", value)


def record(name=b"FILE.TXT;1", sector=30, length=5, flags=0):
    result = bytearray(33 + len(name) + (not len(name) % 2))
    result[0] = len(result)
    result[2:10] = both32(sector)
    result[10:18] = both32(length)
    result[25] = flags
    result[28:32] = both16(1)
    result[32] = len(name)
    result[33:33+len(name)] = name
    return bytes(result)


class IsoParserTests(unittest.TestCase):
    def test_both_endian_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            module.both32(b"\x01\0\0\0\0\0\0\x02", 0)

    def test_normal_record_retains_extent(self):
        item = module.parse_record(record(), False)
        self.assertEqual(item, {"name": "FILE.TXT;1", "sector": 30, "length": 5, "directory": False})

    def test_joliet_exact_name(self):
        item = module.parse_record(record("AI-BS Wheel Setup.exe".encode("utf-16-be")), True)
        self.assertEqual(item["name"], "AI-BS Wheel Setup.exe")

    def test_imapi_joliet_version_one_identifier_maps_to_windows_name(self):
        self.assertEqual(module.windows_media_name("AI-BS Wheel Setup.exe;1"), "AI-BS Wheel Setup.exe")
        self.assertEqual(module.windows_media_name("manifest.json"), "manifest.json")

    def test_other_or_embedded_iso_file_versions_rejected(self):
        for name in ("manifest.json;2", "manifest;1.json", "manifest.json;1;1", "manifest.json;01"):
            with self.assertRaises(ValueError, msg=name):
                module.windows_media_name(name)

    def test_unsafe_record_fields_rejected(self):
        for index, value in ((1, 1), (25, 128), (26, 1), (27, 1), (32, 250)):
            raw = bytearray(record())
            raw[index] = value
            with self.assertRaises(ValueError, msg=str(index)):
                module.parse_record(bytes(raw), False)

    def test_embedded_path_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_record(record(b"OTHER/FILE;1"), False)

    def test_extent_outside_image_rejected(self):
        with self.assertRaises(ValueError):
            module.read_extent(bytes(4096), 1, 2049)

    def test_unexpected_directory_rejected(self):
        root = record(b"\0", 1, 2048, 2) + record(b"\1", 1, 2048, 2) + record(b"SUBDIR", 2, 2048, 2)
        image = bytes(2048) + root.ljust(2048, b"\0") + bytes(2048)
        with self.assertRaises(ValueError):
            module.read_directory(image, 1, 2048, False)

    def test_duplicate_names_rejected(self):
        root = record(b"\0", 1, 2048, 2) + record(b"\1", 1, 2048, 2) + record() + record()
        image = bytes(2048) + root.ljust(2048, b"\0") + bytes(30*2048)
        with self.assertRaises(ValueError):
            module.read_directory(image, 1, 2048, False)

    def test_directory_reads_all_records(self):
        root = record(b"\0", 1, 2048, 2) + record(b"\1", 1, 2048, 2) + record()
        image = bytes(2048) + root.ljust(2048, b"\0") + bytes(30*2048)
        items = module.read_directory(image, 1, 2048, False)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "FILE.TXT;1")

    def test_declared_directory_bytes_need_not_fill_last_sector(self):
        # IMAPI's actual primary root declares 306 bytes in one allocated sector.
        root = record(b"\0", 1, 306, 2) + record(b"\1", 1, 306, 2) + record()
        image = bytes(2048) + root.ljust(2048, b"\0") + bytes(30*2048)
        items = module.read_directory(image, 1, 306, False)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "FILE.TXT;1")

    def test_nonzero_bytes_after_partial_directory_rejected(self):
        root = record(b"\0", 1, 306, 2) + record(b"\1", 1, 306, 2) + record()
        allocation = bytearray(root.ljust(2048, b"\0"))
        allocation[306] = 1
        with self.assertRaises(ValueError):
            module.read_directory(bytes(2048) + bytes(allocation) + bytes(30*2048), 1, 306, False)

    def test_record_truncated_at_declared_directory_end_rejected(self):
        root = record(b"\0", 1, 90, 2) + record(b"\1", 1, 90, 2) + record()
        with self.assertRaises(ValueError):
            module.read_directory(bytes(2048) + root.ljust(2048, b"\0") + bytes(30*2048), 1, 90, False)


if __name__ == "__main__":
    unittest.main()
