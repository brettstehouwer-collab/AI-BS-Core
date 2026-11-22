"""Exercise actual C++ binary pipes against the Python frame implementation."""
from pathlib import Path
import json
import struct
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio.game_engine.creator_wire import Frame, Opcode, Parser, encode, MAX_PAYLOAD


def verify(executable):
    count = 0

    def exchange(raw, accepted):
        nonlocal count
        result = subprocess.run([str(executable)], input=raw, capture_output=True, timeout=30)
        count += 1
        if accepted:
            assert result.returncode == 0 and result.stdout == raw, (count, result.stderr)
        else:
            assert result.returncode == 2 and result.stderr, (count, result.returncode)

    for opcode in Opcode:
        for response in (False, True):
            frame = Frame(opcode, (1 << 64) - 1, bytes(range(16)), (1 << 64) - 1,
                          bytes(range(256)) + struct.pack('<d', -0.0), response)
            raw = encode(frame)
            exchange(raw, True)
            parser = Parser()
            assert parser.feed(raw) == [frame]
            parser.finish()
    sample = encode(Frame(Opcode.PREVIEW, 1, bytes(16), 3, b'abc'))
    exchange(b'', True)
    for end in range(1, len(sample)):
        exchange(sample[:end], False)
    for offset, value in ((0, b'NOPE'), (4, b'\x02\0'), (6, b'\x31\0'),
                          (8, b'\x99\0'), (10, b'\x02\0'),
                          (12, struct.pack('<I', MAX_PAYLOAD + 1)), (16, bytes(8))):
        bad = bytearray(sample)
        bad[offset:offset + len(value)] = value
        exchange(bytes(bad), False)
    exchange(encode(Frame(Opcode.SNAPSHOT_PAGE, 1, bytes(16), 0, b'x' * MAX_PAYLOAD)), True)
    # Coalesced messages cross many header/payload boundaries in 37-byte reads.
    exchange(b''.join(encode(Frame(Opcode.DESCRIBE, i, bytes(16), 0, bytes(i)))
                      for i in range(1, 100)), True)
    return {'schema_version': 1, 'status': 'passed', 'process_cases': count,
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'executable': str(executable), 'scope': 'Framing and actual pipe bytes only; no command dispatcher'}


if __name__ == '__main__':
    report = verify(Path(sys.argv[1]).resolve())
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
