"""Reject a compact checksummed checkpoint before unbounded replay expansion.

This deliberately malformed format-1 fixture has valid entities, scoped events,
receipts and checksum, but omits its undo history. The replay byte budget must
reject it before reaching that later history mismatch. No engine fixture or
large CreatorSession is constructed to generate the attack input.
"""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from uuid import uuid4
import zlib


def text(value: str) -> bytes:
    encoded = value.encode('utf-8')
    assert len(encoded) <= 4096
    return struct.pack('<I', len(encoded)) + encoded


def entity(alias: str, identity: str, capacity: float) -> bytes:
    return (text(alias) + text('N' * 1536) + text(identity)
            + struct.pack('<I', 1) + text('capacity') + struct.pack('<d', capacity))


def adversarial_checkpoint() -> bytes:
    identities = [str(uuid4()) for _ in range(512)]
    aliases = ['core'] + [f'node-{index:04d}' for index in range(1, len(identities))]
    world_id, checkpoint_id = str(uuid4()), str(uuid4())
    event_count = 101
    create_edits = struct.pack('<I', len(identities)) + b''.join(
        b'\x00' + entity(alias, identity, 0)
        for alias, identity in zip(aliases, identities)
    )
    set_edits = (struct.pack('<I', 1) + b'\x02' + text('core')
                 + text('capacity') + struct.pack('<d', 1) + text(identities[0]))
    events = bytearray()
    receipts = bytearray()
    for index in range(event_count):
        operation = f'operation-{index:04d}'
        edits = create_edits if index == 0 else set_edits
        description = 'Constructed the nodes' if index == 0 else 'Adjusted core capacity'
        events.extend(text('first-boot') + text('main') + text(operation)
                      + text('authoring.applied') + struct.pack('<Q', index + 1)
                      + text(world_id) + edits + text(description))
        receipts.extend(text(operation) + struct.pack('<Q', index) + edits
                        + text(description) + text('Applied in memory')
                        + struct.pack('<Q', index + 1))
    payload = (text('first-boot') + text('main') + text(world_id) + text(checkpoint_id)
               + struct.pack('<Q', event_count)
               + struct.pack('<I', 1) + text('capacity') + struct.pack('<dd', 0, 100)
               + struct.pack('<I', len(identities)) + b''.join(map(text, identities))
               + struct.pack('<I', len(identities)) + b''.join(
                   entity(alias, identity, 1 if alias == 'core' else 0)
                   for alias, identity in zip(aliases, identities))
               + struct.pack('<I', event_count) + events
               + struct.pack('<I', event_count) + receipts
               + struct.pack('<II', 0, 0))  # Intentionally omitted undo/redo worlds.
    checkpoint = b'AIBSSAVE' + struct.pack('<IQI', 1, len(payload), zlib.crc32(payload)) + payload
    assert len(checkpoint) < 16 * 1024 * 1024, 'Fixture must pass the outer size bound'
    return checkpoint


def verify(probe: Path, output: Path) -> None:
    directory = output / 'checkpoints'
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bounds-', dir=directory) as temporary:
        slot = Path(temporary) / 'malformed-expansion.aibs'
        fixture = adversarial_checkpoint()
        slot.write_bytes(fixture)
        process = subprocess.run([str(probe.resolve()), 'verify', str(slot.resolve()), '1', '101'],
                                 capture_output=True, text=True, timeout=20)
        assert process.returncode == 5, (
            f'Expected load rejection (5), got {process.returncode}: {process.stderr}')
        assert 'budget exceeded' in process.stderr, (
            f'Expected bounded replay rejection before history validation: {process.stderr}')
        assert 'byte budget exceeded' in process.stderr, (
            f'Long entity names must exercise the replay byte budget: {process.stderr}')
        print(f'PASS: {len(fixture):,}-byte checksummed fixture rejected within replay byte budget')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: verify_checkpoint_bounds.py PROBE OUTPUT_DIR')
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
