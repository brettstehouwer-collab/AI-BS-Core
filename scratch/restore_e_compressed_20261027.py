"""Restore selected files from this pass to original compression state, preserving bytes."""
import ctypes as c
from ctypes import wintypes as w
import json
import os
import shutil
import subprocess
import sys
import compress_e_ntfs_20261027 as core

def disk():
    return {'free': shutil.disk_usage('E:/').free,
            'fsutil': subprocess.run(['fsutil', 'volume', 'diskfree', 'E:'], capture_output=True, text=True).stdout}

def times(info):
    return [info.created.dwHighDateTime, info.created.dwLowDateTime,
            info.written.dwHighDateTime, info.written.dwLowDateTime]

def restore(target, expected, record_path):
    assert not core.excluded(target)
    assert expected['status'] == 'compressed_verified' and expected['before_compression'] == 0
    result = {'path': target, 'started_utc': core.utc(), 'before_volume': disk(), 'mutation_started': False}
    h = core.K.CreateFileW('\\\\?\\' + target, 0xc0000000, 1, None, 3, 0x00200000, None)
    if h == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    try:
        before = core.info_for(h)
        assert core.final_path(h).casefold() == target.casefold() and before.links == 1
        assert before.attrs & core.ATTR_SKIP == 0 and before.identity == tuple(expected['identity'])
        if 'creation_write_time' in expected:
            assert times(before) == expected['creation_write_time'], 'File timestamps changed before restoration'
        digest, size = core.sha256_handle(h)
        assert digest == expected['after_sha256'] and size == before.size == expected['size']
        assert core.compression_state(h) == 2
        result.update({'before_sha256': digest, 'identity': before.identity, 'size': size,
                       'before_times': times(before), 'before_allocation_api': core.allocation(target, before)})
        with (core.OUT / 'restoration_intents.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
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
        if not core.K.CloseHandle(h):
            result.update({'verified': False, 'close_winerror': c.get_last_error()})
        try:
            result['after_volume_closed'] = disk()
        except Exception as exc:
            result.update({'verified': False, 'volume_error_type': type(exc).__name__})
        result['finished_utc'] = core.utc()
        with record_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    assert result['verified'], 'Restoration close/volume verification failed'
    return result

if __name__ == '__main__':
    rows = [json.loads(line) for name in ['pilot_results.jsonl', 'results.jsonl']
            for line in (core.OUT / name).read_text().splitlines()]
    core.fail_if_false(core.K.SetPriorityClass(core.K.GetCurrentProcess(), 0x100000))
    for target in sys.argv[1:]:
        original = next(row for row in rows if row['path'] == target)
        restore(target, original, core.OUT / 'restoration_results.jsonl')
