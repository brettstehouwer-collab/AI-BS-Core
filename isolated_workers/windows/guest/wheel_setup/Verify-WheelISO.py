"""Independently parse ISO9660/Joliet directories and compare every media payload.

Trusted host infrastructure only. No mounting, guest launch, shell, or installation.
The production guest helper does not import or execute this source.
"""
import hashlib
import json
import os
import re
import stat
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

SECTOR = 2048
LABEL = "AIBS_WHEELS_V1"
FILES = {
    "AI-BS Wheel Setup.exe",
    "psutil-7.2.2-cp37-abi3-win_amd64.whl",
    "pywin32-312-cp313-cp313-win_amd64.whl",
    "README.txt",
    "manifest.json",
}
WHEELS = {
    "psutil-7.2.2-cp37-abi3-win_amd64.whl": (137737, "EB7E81434C8D223EC4A219B5FC1C47D0417B12BE7EA866E24FB5AD6E84B3D988"),
    "pywin32-312-cp313-cp313-win_amd64.whl": (6914298, "C53E878D15A1C44788082BFE712A905433473AA38F86375B7CF8B45E3ACBAAF9"),
}


def require(ok, text):
    if not ok:
        raise ValueError(text)


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def both32(data, offset):
    require(offset >= 0 and offset + 8 <= len(data), "Truncated 32-bit field")
    lo, hi = struct.unpack_from("<I", data, offset)[0], struct.unpack_from(">I", data, offset + 4)[0]
    require(lo == hi, "32-bit endian mismatch")
    return lo


def both16(data, offset):
    require(offset >= 0 and offset + 4 <= len(data), "Truncated 16-bit field")
    lo, hi = struct.unpack_from("<H", data, offset)[0], struct.unpack_from(">H", data, offset + 2)[0]
    require(lo == hi, "16-bit endian mismatch")
    return lo


def read_extent(image, sector, length):
    require(isinstance(sector, int) and isinstance(length, int) and sector >= 0 and length >= 0, "Invalid extent")
    start = sector * SECTOR
    require(start <= len(image) and length <= len(image) - start, "Extent outside image")
    return image[start:start + length]


def parse_record(raw, joliet):
    require(34 <= len(raw) <= 255 and raw[0] == len(raw), "Invalid directory record length")
    n = raw[32]
    require(n > 0 and 33 + n <= len(raw), "Invalid identifier length")
    require(raw[1] == 0 and raw[25] in (0, 2) and raw[26] == 0 and raw[27] == 0, "Unsupported record flags/interleave")
    require(both16(raw, 28) == 1, "Unsupported volume sequence")
    require(not any(raw[33 + n:]), "Unexpected directory system-use data")
    name_bytes = raw[33:33 + n]
    if name_bytes in (b"\0", b"\1"):
        name = "." if name_bytes == b"\0" else ".."
    else:
        require(not joliet or len(name_bytes) % 2 == 0, "Odd Joliet identifier")
        name = name_bytes.decode("utf-16-be" if joliet else "ascii", errors="strict")
        require(not any(ord(c) < 32 or c in "\\/:\x00" for c in name), "Unsafe directory identifier")
        require(name not in (".", ".."), "Ambiguous special identifier")
    return {"name": name, "sector": both32(raw, 2), "length": both32(raw, 10), "directory": raw[25] == 2}


def read_directory(image, sector, length, joliet):
    # ISO9660 declares directory bytes independently of the sector allocation.
    # IMAPI emits short roots (306/492 bytes here), with zero padding to 2048.
    require(0 < length <= 16 * SECTOR, "Unexpected root directory length")
    allocation = read_extent(image, sector, ((length + SECTOR - 1) // SECTOR) * SECTOR)
    require(not any(allocation[length:]), "Nonzero final directory sector padding")
    data = allocation[:length]
    entries, names, specials = [], set(), set()
    offset = 0
    while offset < len(data):
        n = data[offset]
        if n == 0:
            end = min(((offset // SECTOR) + 1) * SECTOR, len(data))
            require(not any(data[offset:end]), "Nonzero directory padding")
            offset = end
            continue
        require(n <= SECTOR - offset % SECTOR and offset + n <= len(data), "Record crosses directory sector")
        item = parse_record(data[offset:offset + n], joliet)
        offset += n
        key = item["name"].casefold()
        require(key not in names, "Duplicate directory identifier")
        names.add(key)
        if item["name"] in (".", ".."):
            require(item["directory"] and item["sector"] == sector and item["length"] == length, "Invalid root special entry")
            specials.add(item["name"])
        else:
            require(not item["directory"], "Unexpected subdirectory")
            require(item["length"] > 0, "Unexpected empty payload")
            read_extent(image, item["sector"], item["length"])
            entries.append(item)
    require(specials == {".", ".."}, "Missing root special entries")
    return entries


def parse_path_table(image, sector, length, root_sector, big):
    require(sector >= 16 and length == 10, "Unexpected root-only path table")
    data = read_extent(image, sector, length)
    require(data[0] == 1 and data[1] == 0 and data[8:] == b"\0\0", "Unexpected path table identifiers")
    order = ">" if big else "<"
    require(struct.unpack_from(order + "I", data, 2)[0] == root_sector, "Path table root extent mismatch")
    require(struct.unpack_from(order + "H", data, 6)[0] == 1, "Unexpected path table parent")


def windows_media_name(identifier):
    # ISO file-version suffixes are directory metadata, not Windows CDROM names.
    # Keep the raw identifiers in the directory receipt; admit only version one.
    if ";" in identifier:
        require(identifier.count(";") == 1 and identifier.endswith(";1"), "Unexpected ISO file version")
        return identifier[:-2]
    return identifier


def no_reparse(path):
    path = Path(path)
    require(path.is_absolute(), "Absolute path required")
    for candidate in (path, *path.parents):
        info = os.lstat(candidate)
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400), "Reparse path rejected")


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def stage_payloads(stage):
    no_reparse(stage)
    require(stage.is_dir(), "Media source is not a directory")
    children = list(stage.iterdir())
    require({p.name for p in children} == FILES and len(children) == len(FILES), "Unexpected staged entries")
    contents = {}
    for path in children:
        no_reparse(path)
        require(path.is_file(), "Unexpected staged non-file")
        require(path.stat().st_size <= 8 * 1024 * 1024, "Oversized staged payload")
        contents[path.name] = path.read_bytes()
    for name, (length, sha) in WHEELS.items():
        require(len(contents[name]) == length and digest(contents[name]) == sha, "Approved wheel pin mismatch")
    require(0 < len(contents["AI-BS Wheel Setup.exe"]) <= 1024 * 1024 and contents["AI-BS Wheel Setup.exe"][:2] == b"MZ", "Invalid helper payload")
    require(0 < len(contents["README.txt"]) <= 8192, "Invalid README payload size")
    require(0 < len(contents["manifest.json"]) <= 8192, "Invalid manifest payload size")
    manifest = json.loads(contents["manifest.json"].decode("utf-8-sig"), object_pairs_hook=strict_object)
    require(set(manifest) == {"schema", "volume_label", "files"} and type(manifest["schema"]) is int and manifest["schema"] == 1 and manifest["volume_label"] == LABEL, "Unexpected manifest header")
    records = manifest["files"]
    require(isinstance(records, list) and len(records) == 4, "Unexpected manifest entries")
    seen = set()
    for entry in records:
        require(isinstance(entry, dict) and set(entry) == {"name", "length", "sha256"}, "Unexpected manifest record fields")
        name = entry["name"]
        require(name in FILES - {"manifest.json"} and name not in seen, "Unexpected/duplicate manifest record")
        require(type(entry["length"]) is int and entry["length"] == len(contents[name]) and isinstance(entry["sha256"], str) and re.fullmatch(r"[A-Fa-f0-9]{64}", entry["sha256"]) and entry["sha256"].upper() == digest(contents[name]), "Manifest payload mismatch")
        seen.add(name)
    return contents


def verify_image(iso, stage):
    no_reparse(iso)
    require(iso.is_file() and 0 < iso.stat().st_size <= 32 * 1024 * 1024, "Invalid ISO size")
    image = iso.read_bytes()
    require(len(image) % SECTOR == 0, "Partial ISO sector")
    contents = stage_payloads(stage)
    descriptors, terminated = {}, False
    for sector in range(16, min(64, len(image) // SECTOR)):
        data = read_extent(image, sector, SECTOR)
        require(data[1:7] == b"CD001\x01", "Invalid volume descriptor signature")
        kind = data[0]
        if kind == 255:
            terminated = True
            descriptor_end = sector + 1
            break
        require(kind in (1, 2) and kind not in descriptors, "Unexpected/duplicate volume descriptor")
        descriptors[kind] = (sector, data)
    require(terminated and set(descriptors) == {1, 2}, "Missing ISO9660/Joliet descriptors")
    metadata = [(16, descriptor_end)]
    parsed, receipt = {}, []
    for kind in (1, 2):
        sector, data = descriptors[kind]
        joliet = kind == 2
        require(both32(data, 80) == len(image) // SECTOR and both16(data, 128) == SECTOR, "Volume size/block mismatch")
        require(both16(data, 120) == 1 and both16(data, 124) == 1, "Unexpected volume set/sequence")
        label = data[40:72].decode("utf-16-be" if joliet else "ascii", errors="strict").rstrip(" \0")
        require(label == LABEL, "Volume label mismatch")
        if joliet:
            require(data[88:91] in (b"%/@", b"%/C", b"%/E"), "Invalid Joliet escape sequence")
        root = parse_record(data[156:156 + data[156]], joliet)
        require(root["directory"] and root["name"] == ".", "Invalid descriptor root")
        entries = read_directory(image, root["sector"], root["length"], joliet)
        require(len(entries) == 5, "Unexpected root file count")
        metadata.append((root["sector"], root["sector"] + (root["length"] + SECTOR - 1) // SECTOR))
        path_length = both32(data, 132)
        for offset, big in ((140, False), (144, False), (148, True), (152, True)):
            loc = struct.unpack_from(">I" if big else "<I", data, offset)[0]
            if offset in (144, 152) and loc == 0:
                continue
            parse_path_table(image, loc, path_length, root["sector"], big)
            metadata.append((loc, loc + (path_length + SECTOR - 1) // SECTOR))
        parsed[kind] = entries
        receipt.append({"namespace": "Joliet" if joliet else "ISO9660", "descriptor_sector": sector, "root_sector": root["sector"], "root_length": root["length"], "complete_file_count": len(entries), "identifiers": [e["name"] for e in entries]})
    exact = []
    for raw_entry in parsed[2]:
        entry = dict(raw_entry)
        entry["name"] = windows_media_name(entry["name"])
        exact.append(entry)
    require({e["name"] for e in exact} == FILES, "Unexpected Joliet files")
    spans, files = [], []
    for entry in exact:
        start = entry["sector"]
        end = start + (entry["length"] + SECTOR - 1) // SECTOR
        require(start >= descriptor_end and end <= len(image) // SECTOR, "Invalid payload extent")
        require(all(end <= lo or start >= hi for lo, hi in metadata), "Payload overlaps filesystem metadata")
        require(all(end <= lo or start >= hi for lo, hi in spans), "Overlapping payload extents")
        spans.append((start, end))
        payload = read_extent(image, start, entry["length"])
        require(payload == contents[entry["name"]], "Payload differs from staged file")
        files.append({"name": entry["name"], "length": entry["length"], "sector": start, "sha256": digest(payload), "verified": True})
    primary_extents = sorted((e["sector"], e["length"], digest(read_extent(image, e["sector"], e["length"]))) for e in parsed[1])
    joliet_extents = sorted((e["sector"], e["length"], digest(read_extent(image, e["sector"], e["length"]))) for e in exact)
    require(primary_extents == joliet_extents, "ISO9660/Joliet payload extent mismatch")
    return {"verified_utc": datetime.now(timezone.utc).isoformat(), "iso_path": str(iso), "iso_length": len(image), "iso_sha256": digest(image), "volume_label": LABEL, "sector_size": SECTOR, "directory_verification": receipt, "files": sorted(files, key=lambda item: item["name"]), "mounted_or_launched": False}


def main():
    require(len(sys.argv) == 4, "Usage: Verify-WheelISO.py ISO STAGE NEW_RECEIPT")
    iso, stage, report = (Path(value) for value in sys.argv[1:])
    require(report.is_absolute() and not report.exists(), "Receipt must be a fresh absolute file")
    no_reparse(report.parent)
    result = verify_image(iso, stage)
    with report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print("VERIFIED complete ISO9660/Joliet directories, extent boundaries and all five payloads; no mount or launch.")
    print("ISO SHA256 " + result["iso_sha256"])


if __name__ == "__main__":
    main()
