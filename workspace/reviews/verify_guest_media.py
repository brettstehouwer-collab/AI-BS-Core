"""Independently parse Joliet directory records; hash payloads without mounting."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path('C:/AI-BS')
ISO = ROOT / 'saved_data/phase4_offline_media/AIBS_Windows_Guest_Provisioning_v1.iso'
STAGE = ROOT / 'backups/phase4_offline_runtime_20261024T1627099457287Z/guest_only_media'
OUT = Path((ROOT / 'scratch/phase4_append_status_checkpoint.txt').read_text().strip()) / 'agent_review'
SIZE = 2048


def main():
    data = ISO.read_bytes()
    assert hashlib.sha256(data).hexdigest() == '50f4ac4e873bdeaf088b7ae57160cb438f08269f401d811f84053f3a725a33f0'
    primary = joliet = None
    for sector in range(16, 48):
        desc = data[sector*SIZE:(sector+1)*SIZE]
        assert desc[1:6] == b'CD001' and desc[6] == 1
        if desc[0] == 1:
            primary = desc
        if desc[0] == 2 and desc[88:91] in (b'%/@', b'%/C', b'%/E'):
            joliet = desc
        if desc[0] == 255:
            break
    assert primary is not None and joliet is not None
    root_record = joliet[156:190]
    extent = struct.unpack_from('<I', root_record, 2)[0]
    length = struct.unpack_from('<I', root_record, 10)[0]
    assert 0 < length <= 1048576 and extent*SIZE + length <= len(data)
    directory = data[extent*SIZE:extent*SIZE+length]
    files = {}
    offset = 0
    while offset < len(directory):
        record_size = directory[offset]
        if record_size == 0:
            offset = ((offset//SIZE)+1)*SIZE
            continue
        record = directory[offset:offset+record_size]
        assert len(record) == record_size and record_size >= 34
        name_raw = record[33:33+record[32]]
        offset += record_size
        if name_raw in (b'\0', b'\1'):
            continue
        assert not record[25] & 2, 'Unexpected directory in provisioning root'
        name = name_raw.decode('utf-16-be').split(';')[0]
        assert name not in files and '/' not in name and '\\' not in name
        sector = struct.unpack_from('<I', record, 2)[0]
        size = struct.unpack_from('<I', record, 10)[0]
        assert sector*SIZE+size <= len(data)
        content = data[sector*SIZE:sector*SIZE+size]
        source = STAGE/name
        assert source.is_file() and not source.is_symlink()
        assert content == source.read_bytes(), name
        files[name] = dict(bytes=size, sha256=hashlib.sha256(content).hexdigest(), identical_to_verified_stage=True)
    expected = {p.name for p in STAGE.iterdir() if p.is_file()}
    assert set(files) == expected and len(files) == 7
    report = dict(iso=str(ISO), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                  primary_descriptor=True, joliet_descriptor=True, exact_file_set=True,
                  files=files, mounted=False, executed=False, guest_installation_verified=False)
    (OUT/'iso_independent_readback.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(bytes=len(data), files=len(files), all_payloads_exact=True, mounted=False)))


if __name__ == '__main__':
    main()
