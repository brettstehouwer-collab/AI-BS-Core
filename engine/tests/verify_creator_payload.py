"""Cross-language payload proof with independently assembled malformed inputs."""
from pathlib import Path
import json
import math
import struct
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from native_studio.game_engine.creator_payload import (
    Scope, Transaction, EditRequest, Create, SetField, Erase, PayloadError, encode_edit, decode_edit,
)

UUID = '01234567-89ab-4cde-8fab-0123456789ab'


def text(value):
    value = value.encode('utf-8') if isinstance(value, str) else value
    return struct.pack('<I', len(value)) + value


def raw(fields=(('x', 1.),), tag=0, world=UUID, project='project', description='text', count=1):
    prefix = b'\x01\0' + text(project) + text('main') + text(world) + text(UUID)
    prefix += text('operation') + struct.pack('<Q', 7) + text(description) + struct.pack('<I', count)
    body = bytes([tag]) + text('node') + text('N') + text(UUID) + struct.pack('<I', len(fields))
    return prefix + body + b''.join(text(key) + struct.pack('<d', value) for key, value in fields)


def verify(executable):
    cases = 0

    def exchange(data, accepted):
        nonlocal cases
        result = subprocess.run([str(executable)], input=data, capture_output=True, timeout=15)
        cases += 1
        if accepted:
            expected = encode_edit(decode_edit(data))
            assert result.returncode == 0 and result.stdout == expected, (cases, result.stderr)
        else:
            try:
                decode_edit(data)
            except PayloadError:
                pass
            else:
                raise AssertionError(('Python accepted invalid case', cases))
            assert result.returncode == 2 and not result.stdout and result.stderr, (cases, result.returncode)

    scope = Scope('Pencil ✏', 'main', UUID, UUID)
    for value in (-0.0, 0.0, 1.0, -1.0, 1e300, 1e-300):
        request = EditRequest(scope, Transaction('id', (1 << 64) - 1, '😀', (
            Create('n', 'N', UUID, (('x', value),)), SetField('n', 'x', value, UUID), Erase('n', UUID))))
        exchange(encode_edit(request), True)
    exchange(encode_edit(EditRequest(scope, Transaction('legacy', 0, '', (Erase('n', ''),)))), True)
    exchange(raw(fields=(('z', -0.), ('a', 3.))), True)
    sample = raw()
    for end in range(len(sample)):
        exchange(sample[:end], False)
    exchange(sample + b'extra', False)
    for candidate in (
        raw(fields=(('x', 1.), ('x', 2.))), raw(fields=tuple((str(i), 0.) for i in range(65))),
        raw(fields=(('x', math.inf),)), raw(fields=(('x', math.nan),)), raw(tag=3),
        raw(world=UUID.upper()), raw(world=''), raw(project=''), raw(project=b'\0'),
        raw(project=b'\xc0\x80'), raw(project=b'\xed\xa0\x80'), raw(project=b'\xf4\x90\x80\x80'),
        raw(project=b'\xf0\x80\x80\x80'), raw(project=b'\xf0\x9f'), raw(description='x'*4097),
        raw(count=0), raw(count=257), raw(count=0xffffffff), b'x'*(1024*1024+1),
    ):
        exchange(candidate, False)
    return {'schema_version': 1, 'status': 'passed', 'process_cases': cases,
            'completed_at': datetime.now(timezone.utc).isoformat(), 'executable': str(executable),
            'scope': 'Scoped numeric edit payload validation; no live document dispatcher'}


if __name__ == '__main__':
    report = verify(Path(sys.argv[1]).resolve())
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
