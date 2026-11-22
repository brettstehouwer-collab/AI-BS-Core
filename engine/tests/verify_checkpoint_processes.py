"""Real process-exit/restart proof. No engine state is mocked."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
import struct
import zlib


def verify(probe: Path, output: Path) -> None:
    checks = []
    report = {'schema_version': 1, 'status': 'failed', 'checks': checks}
    output.mkdir(parents=True, exist_ok=True)
    try:
        def run(mode, path, *args, expected=0):
            process = subprocess.run([str(probe), mode, str(path), *map(str, args)],
                                     capture_output=True, text=True, timeout=20)
            if process.returncode != expected:
                raise AssertionError(f'{mode}: exit {process.returncode}, expected {expected}: {process.stderr}')
            return process.stdout.strip().split()

        checkpoints = output / 'checkpoints'
        checkpoints.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='process-', dir=checkpoints) as directory:
            slot = Path(directory) / 'first-boot.aibs'
            initial = run('seed', slot)
            before = run('verify', slot, 10, 1)
            assert before[:2] == initial[:2], 'restart changed world/entity identities'
            checks.append('Separate-process restart preserves world/entity UUIDs and Adam history')
            run('crash-before', slot, expected=91)
            recovered = run('verify', slot, 10, 1)
            assert recovered == initial, 'pre-publication interruption changed checkpoint'
            checks.append('Forced exit after flush/before publication retains the complete old checkpoint')
            run('crash-after', slot, expected=92)
            recovered = run('verify', slot, 75, 2)
            assert recovered[:2] == initial[:2] and recovered[2] == '2'
            checks.append('Forced exit after publication restores the complete new world and memory')
            # Retain one tiny checkpoint as inspectable monitor evidence.
            evidence = checkpoints / 'verified-first-boot.aibs'
            evidence.write_bytes(slot.read_bytes())
            original = evidence.read_bytes()
            for name, mutate in (
                ('nonfinite', lambda payload: payload.replace(struct.pack('<d', 75), struct.pack('<d', float('nan')))),
                ('scope', lambda payload: payload.replace(b'first-boot', b'wrong-boot')),
            ):
                payload = mutate(original[24:])
                altered = original[:12] + struct.pack('<QI', len(payload), zlib.crc32(payload)) + payload
                corrupted = Path(directory) / (name + '.aibs')
                corrupted.write_bytes(altered)
                run('verify', corrupted, 75, 2, expected=5)
            checks.append('Checksummed non-finite fields and mismatched project scopes are rejected')
            payload = bytearray(original[24:])
            cursor = 0
            for _ in range(4):
                size = struct.unpack_from('<I', payload, cursor)[0]
                cursor += 4 + size
            cursor += 8  # revision, followed by schema count
            struct.pack_into('<I', payload, cursor, 10001)
            malformed = Path(directory) / 'over-limit.aibs'
            malformed.write_bytes(original[:12] + struct.pack('<QI', len(payload), zlib.crc32(payload)) + payload)
            run('verify', malformed, 75, 2, expected=5)
            checks.append('Checksummed over-limit collection is rejected before expansion')
            transient = Path(directory) / 'transient.aibs'
            run('seed', transient)
            run('transient', transient)
            valid = transient.read_bytes()
            payload = valid[24:].replace(struct.pack('<d', 11), struct.pack('<d', float('nan')))
            transient.write_bytes(valid[:12] + struct.pack('<QI', len(payload), zlib.crc32(payload)) + payload)
            run('verify', transient, 10, 2, expected=5)
            checks.append('Invalid transient Create/Erase memories cannot bypass schema validation')
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
        checks.append('FAILED: ' + str(exc))
        raise
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        temporary = output / 'checkpoint_verification.tmp'
        temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, output / 'checkpoint_verification.json')


if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
