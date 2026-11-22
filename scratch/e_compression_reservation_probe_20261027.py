"""Bounded restoration of one already-verified incompressible file's original state."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import shutil
import subprocess
import compress_e_ntfs_20261027 as core

target = r'E:\Cymatics-AURORA-Sources.zip'
out = core.OUT
receipt = out / 'reservation_reversal_probe.json'
assert not receipt.exists(), 'Probe already attempted'
rows = [json.loads(line) for line in (out / 'results.jsonl').read_text().splitlines()]
original = next(row for row in rows if row['path'] == target)
assert original['status'] == 'compressed_verified' and original['before_compression'] == 0
assert not core.excluded(target)

def disk():
    return {'free': shutil.disk_usage('E:/').free,
            'fsutil': subprocess.run(['fsutil', 'volume', 'diskfree', 'E:'], capture_output=True, text=True).stdout}

def times(info):
    return [info.created.dwHighDateTime, info.created.dwLowDateTime,
            info.written.dwHighDateTime, info.written.dwLowDateTime]

result = {'path': target, 'started_utc': core.utc(), 'before_volume': disk(), 'mutation_started': False}
h = core.K.CreateFileW('\\\\?\\' + target, 0xc0000000, 1, None, 3, 0x00200000, None)
if h == c.c_void_p(-1).value:
    raise c.WinError(c.get_last_error())
try:
    before = core.info_for(h)
    assert core.final_path(h).casefold() == target.casefold() and before.links == 1
    assert before.attrs & core.ATTR_SKIP == 0 and before.identity == tuple(original['identity'])
    digest, size = core.sha256_handle(h)
    assert digest == original['after_sha256'] and size == before.size == original['size']
    assert core.compression_state(h) == 2
    result.update({'before_sha256': digest, 'identity': before.identity, 'size': size, 'before_times': times(before),
                   'before_allocation_api': core.allocation(target, before), 'original_receipt': original})
    (out / 'reservation_reversal_probe_intent.json').write_text(json.dumps(result, indent=2) + '\n')
    fmt, count = c.c_ushort(0), w.DWORD()
    result['mutation_started'] = True
    core.fail_if_false(core.K.DeviceIoControl(h, 0x9c040, c.byref(fmt), 2, None, 0, c.byref(count), None))
    digest_after, size_after = core.sha256_handle(h)
    after = core.info_for(h)
    state = core.compression_state(h)
    result.update({'after_sha256': digest_after, 'after_allocation_api': core.allocation(target, after),
                   'after_compression': state,
                   'verified': digest_after == digest and size_after == size == after.size and
                               before.identity == after.identity and times(before) == times(after) and
                               core.final_path(h).casefold() == target.casefold() and state == 0})
    assert result['verified'], 'Restoration preservation check failed'
except Exception as exc:
    result.update({'error_type': type(exc).__name__, 'winerror': getattr(exc, 'winerror', None), 'verified': False})
    raise
finally:
    core.K.CloseHandle(h)
    result.update({'after_volume_closed': disk(), 'finished_utc': core.utc()})
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
