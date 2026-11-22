"""Authorized per-file E: NTFS compression, with same-handle byte verification."""
import argparse
import collections
import ctypes as c
from ctypes import wintypes as w
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import shutil
import time

ROOT = Path('E:/')
OUT = Path('C:\\AI-BS\\backups\\e_drive_compression_20261027\\normal_64k_20261027T195041Z')
RUN_LOCK = OUT.parent / 'run.lock'
BLOCK_TOP = {name.casefold() for name in [
    'SteamLibrary', 'Steam', 'AI-BS-DisposableProbe-v1', 'SaladData', 'Salad', 'AI-BS Broadcast Studio',
    'WindowsApps', 'WpSystem', 'XboxGames', 'Program Files', 'Program Files (x86)',
    'ProgramData', 'WINDOWS', 'windows boot', '$RECYCLE.BIN', 'System Volume Information',
    '$SysReset', 'Recovery', 'Boot', 'EFI', 'WLS2BKUP', 'CrossDevice',
    '.docker', '.ollama', '.chia', '.chia_keys', '.ssh', '.aws', '.kube', '.minikube',
    'AI_BS_Resources', '.jdks', '.local', '.cache']}
BLOCK_PART = {name.casefold() for name in [
    'Databases', 'Database', 'chroma_db', 'chromadb', 'chroma_db_8002', 'leveldb',
    'IndexedDB', 'Local Storage', 'Session Storage', 'Active Outputs', '.git',
    'models', 'checkpoints', 'loras', 'embeddings']}
BLOCK_EXT = {'.vhd', '.vhdx', '.vdi', '.vmdk', '.avhd', '.avhdx', '.qcow', '.qcow2',
    '.vbox', '.sav', '.ova', '.ovf', '.vmem', '.nvram', '.vsv', '.vmrs', '.vmcx',
    '.db', '.db3', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.ldb', '.sst',
    '.gguf', '.safetensors', '.onnx', '.pt', '.pth', '.ckpt', '.h5', '.hdf5', '.model',
    '.wim', '.esd', '.sys', '.dmp', '.etl'}
BLOCK_NAMES = {'pagefile.sys', 'swapfile.sys', 'hiberfil.sys', '.gamingroot', 'model', 'weights', 'pytorch_model.bin'}
ATTR_SKIP = 0x1 | 0x4 | 0x200 | 0x400 | 0x1000 | 0x4000 | 0x40000 | 0x400000
MAX_BYTES = 30_000_000_000
FREE_FLOOR = 8 * 2**30
MIN_BYTES = 65536
ALREADY_ENCODED_EXT = {'.zip', '.rar', '.7z', '.gz', '.bz2', '.xz', '.zst', '.cab',
                      '.exe', '.msi', '.bin', '.mp4', '.mkv', '.mov', '.webm', '.jpg', '.jpeg',
                      '.png', '.gif', '.webp', '.mp3', '.aac', '.ogg', '.flac', '.m4a', '.opus'}
K = c.WinDLL('kernel32', use_last_error=True)
K.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
K.CreateFileW.restype = w.HANDLE
K.CloseHandle.argtypes = [w.HANDLE]
K.CloseHandle.restype = w.BOOL
K.DeviceIoControl.argtypes = [w.HANDLE, w.DWORD, c.c_void_p, w.DWORD, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
K.DeviceIoControl.restype = w.BOOL
K.SetFilePointerEx.argtypes = [w.HANDLE, c.c_longlong, c.POINTER(c.c_longlong), w.DWORD]
K.SetFilePointerEx.restype = w.BOOL
K.ReadFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]
K.ReadFile.restype = w.BOOL
K.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]
K.GetFinalPathNameByHandleW.restype = w.DWORD
K.GetCompressedFileSizeW.argtypes = [w.LPCWSTR, c.POINTER(w.DWORD)]
K.GetCompressedFileSizeW.restype = w.DWORD
K.GetCurrentProcess.restype = w.HANDLE
K.SetPriorityClass.argtypes = [w.HANDLE, w.DWORD]
K.SetPriorityClass.restype = w.BOOL
K.GetDiskSpaceInformationW.argtypes = [w.LPCWSTR, c.c_void_p]
K.GetDiskSpaceInformationW.restype = c.c_long
K.GetFileInformationByHandleEx.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
K.GetFileInformationByHandleEx.restype = w.BOOL

class DiskInfo(c.Structure):
    _fields_ = [(name, c.c_ulonglong) for name in ['total', 'available', 'pool_unavailable',
                 'caller_total', 'caller_available', 'caller_unavailable', 'used', 'reserved',
                 'storage_reserve', 'committed', 'pool_available']] + [('sectors', w.DWORD), ('sector_bytes', w.DWORD)]

class StandardInfo(c.Structure):
    _fields_ = [('allocation', c.c_longlong), ('eof', c.c_longlong), ('links', w.DWORD),
                ('delete_pending', c.c_ubyte), ('directory', c.c_ubyte)]

def volume_snapshot():
    value = DiskInfo()
    hr = K.GetDiskSpaceInformationW('E:\\', c.byref(value))
    if hr < 0:
        raise OSError('GetDiskSpaceInformationW HRESULT ' + str(hr))
    unit = value.sectors * value.sector_bytes
    return {name + '_bytes': getattr(value, name) * unit for name in
            ['total', 'available', 'caller_available', 'used', 'reserved', 'storage_reserve']}

def handle_allocation(handle):
    value = StandardInfo()
    fail_if_false(K.GetFileInformationByHandleEx(handle, 1, c.byref(value), c.sizeof(value)))
    return value.allocation

class Info(c.Structure):
    _fields_ = [('attrs', w.DWORD), ('created', w.FILETIME), ('accessed', w.FILETIME),
                ('written', w.FILETIME), ('serial', w.DWORD), ('size_hi', w.DWORD),
                ('size_lo', w.DWORD), ('links', w.DWORD), ('index_hi', w.DWORD), ('index_lo', w.DWORD)]
K.GetFileInformationByHandle.argtypes = [w.HANDLE, c.POINTER(Info)]
K.GetFileInformationByHandle.restype = w.BOOL

def utc():
    return datetime.now(timezone.utc).isoformat()

def fail_if_false(value):
    if not value:
        raise c.WinError(c.get_last_error())

def excluded(path):
    parts = Path(path).parts
    if not parts or parts[0].casefold() != 'e:\\':
        return 'outside_e'
    if len(parts) > 1 and parts[1].casefold() in BLOCK_TOP:
        return 'protected_tree'
    if any(part.casefold() in BLOCK_PART for part in parts[1:-1]):
        return 'database_or_active_tree'
    name = Path(path).name.casefold()
    if name in BLOCK_NAMES or Path(path).suffix.casefold() in BLOCK_EXT or '.onnx.' in name:
        return 'protected_file_type'
    if name.endswith(('-wal', '-shm', '-journal', '.db.lock')) or name.startswith('log.old.'):
        return 'database_sidecar'
    return None

def attr_reason(st, recent_cutoff):
    if st.st_file_attributes & ATTR_SKIP:
        return 'protected_attributes'
    if st.st_file_attributes & 0x800:
        return 'already_compressed'
    if st.st_nlink > 1:
        return 'multiple_hardlinks'
    if st.st_size == 0:
        return 'empty'
    if st.st_size > MAX_BYTES:
        return 'over_30GB'
    if st.st_mtime_ns > recent_cutoff:
        return 'recently_written'
    return None

def allocation(path, info):
    if not info.attrs & (0x800 | 0x200):
        return ((info.size + 4095) // 4096) * 4096
    high = w.DWORD()
    c.set_last_error(0)
    low = K.GetCompressedFileSizeW(path, c.byref(high))
    if low == 0xffffffff and c.get_last_error():
        raise c.WinError(c.get_last_error())
    return (high.value << 32) | low

def info_for(handle):
    value = Info()
    fail_if_false(K.GetFileInformationByHandle(handle, c.byref(value)))
    value.size = (value.size_hi << 32) | value.size_lo
    value.identity = (value.serial, value.index_hi, value.index_lo)
    return value

def final_path(handle):
    buffer = c.create_unicode_buffer(32768)
    n = K.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    fail_if_false(n)
    if n >= len(buffer):
        raise RuntimeError('Canonical path too long')
    return buffer.value.removeprefix('\\\\?\\')

READ_BUFFER = c.create_string_buffer(4 * 1024 * 1024)
def sha256_handle(handle):
    fail_if_false(K.SetFilePointerEx(handle, 0, None, 0))
    digest = hashlib.sha256()
    total = 0
    while True:
        count = w.DWORD()
        fail_if_false(K.ReadFile(handle, READ_BUFFER, len(READ_BUFFER), c.byref(count), None))
        if not count.value:
            return digest.hexdigest(), total
        digest.update(READ_BUFFER.raw[:count.value])
        total += count.value

def compression_state(handle):
    state, count = c.c_ushort(), w.DWORD()
    fail_if_false(K.DeviceIoControl(handle, 0x9003c, None, 0, c.byref(state), 2, c.byref(count), None))
    return state.value

def compress_one(item):
    path = item['path']
    why = excluded(path)
    if why:
        return {'path': path, 'status': 'skipped', 'reason': why}
    st = os.stat(path, follow_symlinks=False)
    why = attr_reason(st, PLAN['recent_cutoff_ns'])
    if why or (st.st_ino, st.st_size, st.st_mtime_ns) != (item['inode'], item['size'], item['mtime_ns']):
        return {'path': path, 'status': 'skipped', 'reason': why or 'changed_since_plan'}
    # READ sharing permits compatible readers; existing writers cause a safe skip.
    handle = K.CreateFileW('\\\\?\\' + path, 0xc0000000, 1, None, 3, 0x00200000, None)
    if handle == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    result = {'path': path, 'started_utc': utc()}
    mutation_started = False
    try:
        before = info_for(handle)
        canonical = final_path(handle)
        if excluded(canonical) or canonical.casefold() != path.casefold() or before.links != 1 or before.attrs & (ATTR_SKIP | 0x800):
            return {'path': path, 'status': 'skipped', 'reason': 'handle_revalidation'}
        if before.size != item['size'] or ((before.index_hi << 32) | before.index_lo) != item['inode']:
            return {'path': path, 'status': 'skipped', 'reason': 'handle_identity_changed'}
        before_alloc = handle_allocation(handle)
        digest_before, bytes_before = sha256_handle(handle)
        result.update({'size': before.size, 'before_allocated': before_alloc, 'identity': before.identity,
                       'before_attrs': before.attrs, 'before_sha256': digest_before,
                       'creation_write_time': [before.created.dwHighDateTime, before.created.dwLowDateTime,
                                               before.written.dwHighDateTime, before.written.dwLowDateTime],
                       'before_compression': compression_state(handle)})
        # Durable intent precedes the filesystem mutation.
        with (OUT / 'intents.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        fmt, count = c.c_ushort(2), w.DWORD()
        mutation_started = True
        ok = K.DeviceIoControl(handle, 0x9c040, c.byref(fmt), 2, None, 0, c.byref(count), None)
        api_error = c.get_last_error() if not ok else 0
        digest_after, bytes_after = sha256_handle(handle)
        after = info_for(handle)
        state = compression_state(handle)
        after_alloc = handle_allocation(handle)
        preserved = (digest_before == digest_after and bytes_before == bytes_after == before.size == after.size
                     and before.identity == after.identity and final_path(handle).casefold() == canonical.casefold())
        times_preserved = (before.created.dwHighDateTime, before.created.dwLowDateTime, before.written.dwHighDateTime,
                           before.written.dwLowDateTime) == (after.created.dwHighDateTime, after.created.dwLowDateTime,
                           after.written.dwHighDateTime, after.written.dwLowDateTime)
        result.update({'after_sha256': digest_after, 'after_attrs': after.attrs, 'after_compression': state,
                       'after_allocated': after_alloc, 'saved_bytes': before_alloc - after_alloc,
                       'content_and_identity_preserved': preserved, 'creation_and_write_times_preserved': times_preserved,
                       'status': 'compressed_verified' if ok and state == 2 and preserved and times_preserved else 'verification_failed',
                       'winerror': api_error, 'finished_utc': utc()})
        if not ok and preserved and times_preserved and state == result['before_compression']:
            result['status'] = 'skipped' if api_error in {5, 32, 33, 1224} else 'operation_failed'
        return result
    except Exception as exc:
        if not mutation_started:
            raise
        result.update({'status': 'verification_failed', 'mutation_started': True,
                       'winerror': getattr(exc, 'winerror', None), 'error_type': type(exc).__name__,
                       'finished_utc': utc()})
        return result
    finally:
        if not K.CloseHandle(handle):
            if mutation_started:
                result.update({'status': 'verification_failed', 'close_winerror': c.get_last_error()})
            else:
                raise c.WinError(c.get_last_error())

def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def make_plan():
    OUT.mkdir(exist_ok=False)
    started = time.time_ns()
    cutoff = started - 15 * 60 * 10**9
    skipped = collections.Counter()
    files = []
    stack = [str(ROOT)]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for ent in entries:
                    try:
                        path = ent.path
                        reason = excluded(path)
                        if reason:
                            skipped[reason] += 1
                            continue
                        st = ent.stat(follow_symlinks=False)
                        if st.st_file_attributes & (0x400 | 0x1000 | 0x40000 | 0x400000):
                            skipped['reparse_or_offline'] += 1
                            continue
                        if ent.is_dir(follow_symlinks=False):
                            if ent.name.casefold() in BLOCK_PART:
                                skipped['database_or_active_tree'] += 1
                            else:
                                stack.append(path)
                            continue
                        # Windows Python 3.12 DirEntry.stat reports st_ino=0;
                        # explicit stat is needed for stable identity admission.
                        st = os.stat(path, follow_symlinks=False)
                        reason = attr_reason(st, cutoff)
                        if reason:
                            skipped[reason] += 1
                        else:
                            files.append({'path': path, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
                                          'inode': st.st_ino, 'attrs': st.st_file_attributes})
                    except OSError as exc:
                        skipped['metadata_winerror_' + str(getattr(exc, 'winerror', None))] += 1
        except OSError as exc:
            skipped['directory_winerror_' + str(getattr(exc, 'winerror', None))] += 1
    plan = {'created_utc': utc(), 'authorization': 'User: ignore steam and compress the rest',
            'recent_cutoff_ns': cutoff, 'free_before': shutil.disk_usage(ROOT).free,
            'file_count': len(files), 'logical_bytes': sum(item['size'] for item in files),
            'skipped_counts': dict(skipped), 'excluded_top_trees': sorted(BLOCK_TOP),
            'excluded_components': sorted(BLOCK_PART), 'excluded_extensions': sorted(BLOCK_EXT),
            'mode': 'Per-file LZNT1; directories not marked; no deletion/moves or permission changes', 'files': files}
    write_json('plan.json', plan)
    print(json.dumps({k: v for k, v in plan.items() if k != 'files'}), flush=True)

def repair_plan_ids():
    planpath = OUT / 'plan.json'
    original = planpath.read_bytes()
    preserved = OUT / 'plan_initial_zero_inode.json'
    if preserved.exists():
        raise RuntimeError('Identity correction already attempted')
    preserved.write_bytes(original)
    plan = json.loads(original)
    files, removed = [], collections.Counter()
    for item in plan['files']:
        try:
            st = os.stat(item['path'], follow_symlinks=False)
            reason = attr_reason(st, plan['recent_cutoff_ns'])
            if reason or (st.st_size, st.st_mtime_ns) != (item['size'], item['mtime_ns']):
                removed[reason or 'changed_since_initial_plan'] += 1
                continue
            item['inode'] = st.st_ino
            files.append(item)
        except OSError as exc:
            removed['stat_winerror_' + str(getattr(exc, 'winerror', None))] += 1
    plan.update({'files': files, 'file_count': len(files), 'logical_bytes': sum(item['size'] for item in files),
                 'identity_correction_utc': utc(), 'identity_correction_removed': dict(removed)})
    for name in ['pilot_results.jsonl', 'pilot_receipt.json']:
        path = OUT / name
        if path.exists():
            path.rename(OUT / ('initial_guard_' + name))
    write_json('plan.json', plan)
    print(json.dumps({'files': len(files), 'removed': dict(removed), 'e_mutations': False}))

def apply(mode):
    global PLAN
    PLAN = json.loads((OUT / 'plan.json').read_text())
    done = set()
    totals = collections.Counter()
    previous = []
    for logname in ['pilot_results.jsonl', 'results.jsonl']:
        path = OUT / logname
        if path.exists():
            for line in path.read_text().splitlines():
                row = json.loads(line)
                if row['status'] in {'verification_failed', 'operation_failed'}:
                    raise RuntimeError('Unresolved prior failure; explicit reconciliation required')
                previous.append(row)
                done.add(row['path'])
                totals[row['status']] += 1
                totals['saved_bytes'] += row.get('saved_bytes', 0)
    for line in (OUT / 'intents.jsonl').read_text().splitlines():
        if json.loads(line)['path'] not in done:
            raise RuntimeError('Unreconciled durable mutation intent')
    restored = []
    if (OUT / 'reservation_reversal_probe.json').exists():
        restored.append(json.loads((OUT / 'reservation_reversal_probe.json').read_text()))
    if (OUT / 'restoration_results.jsonl').exists():
        restored.extend(json.loads(line) for line in (OUT / 'restoration_results.jsonl').read_text().splitlines())
    for row in restored:
        if not row['verified']:
            raise RuntimeError('Unresolved restoration verification failure')
    restoration_terminal = {(row['path'], row['started_utc']) for row in restored if row['verified']}
    if (OUT / 'restoration_intents.jsonl').exists():
        for line in (OUT / 'restoration_intents.jsonl').read_text().splitlines():
            row = json.loads(line)
            if (row['path'], row['started_utc']) not in restoration_terminal:
                raise RuntimeError('Unreconciled durable restoration intent')
    restored_paths = {row['path'] for row in restored}
    for row in previous:
        if row['path'] in restored_paths and row['status'] == 'compressed_verified':
            totals['compressed_verified'] -= 1
            totals['saved_bytes'] -= row.get('saved_bytes', 0)
            totals['restored_unhelpful'] += 1
    if mode == 'all':
        pilot = json.loads((OUT / 'pilot_receipt.json').read_text())
        if not pilot['all_content_verified'] or pilot['compressed_verified'] < 2:
            raise RuntimeError('Pilot not accepted')
    fail_if_false(K.SetPriorityClass(K.GetCurrentProcess(), 0x20))
    K.GetPriorityClass.argtypes = [w.HANDLE]
    K.GetPriorityClass.restype = w.DWORD
    priority_class = K.GetPriorityClass(K.GetCurrentProcess())
    if priority_class != 0x20:
        raise RuntimeError('Normal process priority was not verified')
    priority_ok = True
    files = [item for item in PLAN['files'] if item['path'] not in done]
    if mode == 'pilot':
        log = next(item for item in files if item['path'].casefold() == r'E:\move_log.txt'.casefold())
        wav = next(item for item in files if Path(item['path']).suffix.casefold() == '.wav' and 2**20 < item['size'] < 10*2**20)
        files = [log, wav]
    logfile = OUT / ('pilot_results.jsonl' if mode == 'pilot' else 'results.jsonl')
    last_notice = time.monotonic()
    failed_streak = 0
    run_results = []
    started = utc()
    run_volume_before = volume_snapshot()
    halt = None
    with logfile.open('a', encoding='utf-8', buffering=1) as stream:
        for item in files:
            if (OUT / 'stop_requested').exists():
                halt = 'stop_requested'
                break
            if shutil.disk_usage(ROOT).free < FREE_FLOOR:
                halt = 'free_space_floor'
                break
            result = None
            try:
                if item['size'] < MIN_BYTES:
                    result = {'path': item['path'], 'status': 'skipped',
                              'reason': 'below_64k_policy', 'planned_size': item['size'],
                              'minimum_file_bytes': MIN_BYTES}
                elif Path(item['path']).suffix.casefold() in ALREADY_ENCODED_EXT:
                    result = {'path': item['path'], 'status': 'skipped', 'reason': 'already_encoded_format'}
                else:
                    volume_before = volume_snapshot()
                    result = compress_one(item)
                    if result['status'] == 'compressed_verified':
                        volume_after = volume_snapshot()
                        result.update({'volume_before': volume_before, 'volume_after_closed': volume_after})
                        delta = volume_after['available_bytes'] - volume_before['available_bytes']
                        result['available_bytes_delta'] = delta
                        if delta <= 0 or result['saved_bytes'] <= 0:
                            from restore_e_compressed_normal64k_20261027 import restore
                            try:
                                reversal = restore(item['path'], result, OUT / 'restoration_results.jsonl')
                                result.update({'status': 'compressed_then_reverted_no_net_gain',
                                               'compressed_attempt_saved_bytes': result['saved_bytes'],
                                               'compressed_attempt_after_allocated': result['after_allocated'],
                                               'saved_bytes': 0, 'restoration_verified': reversal['verified'],
                                               'after_allocated': reversal['after_allocation_api'],
                                               'after_attrs': result['before_attrs'],
                                               'after_compression': 0,
                                               'final_volume': volume_snapshot()})
                            except Exception as exc:
                                result.update({'status': 'verification_failed', 'restoration_verified': False,
                                               'error_type': type(exc).__name__,
                                               'winerror': getattr(exc, 'winerror', None)})
            except OSError as exc:
                code = getattr(exc, 'winerror', None)
                result = {'path': item['path'], 'status': 'verification_failed' if result and result.get('status') == 'compressed_verified' else
                          ('skipped' if code in {2, 3, 5, 32, 33, 1224} else 'operation_failed'),
                          'winerror': code, 'error_type': type(exc).__name__}
            except Exception as exc:
                result = {'path': item['path'], 'status': 'verification_failed' if result and result.get('status') == 'compressed_verified' else 'operation_failed',
                          'error_type': type(exc).__name__}
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            totals[result['status']] += 1
            totals['saved_bytes'] += result.get('saved_bytes', 0)
            if mode == 'pilot':
                run_results.append(result)
            failed_streak = failed_streak + 1 if result['status'] == 'operation_failed' else 0
            if result['status'] == 'verification_failed' or result.get('winerror') in {23, 112, 1117} or failed_streak >= 2:
                halt = result['status'] + ':' + str(result.get('winerror'))
                break
            if time.monotonic() - last_notice > 15:
                progress = {'timestamp_utc': utc(), 'mode': mode, 'totals': dict(totals),
                            'minimum_file_bytes': MIN_BYTES, 'priority_mode': 'normal',
                            'priority_class': priority_class, 'pid': os.getpid(),
                            'remaining': PLAN['file_count'] - sum(v for k,v in totals.items() if k != 'saved_bytes'),
                            'free_now': shutil.disk_usage(ROOT).free, 'last_path': item['path']}
                write_json('progress.json', progress)
                print(json.dumps(progress), flush=True)
                last_notice = time.monotonic()
    receipt = {'started_utc': started, 'finished_utc': utc(), 'mode': mode,
               'background_priority_applied': False, 'normal_priority_applied': priority_ok,
               'priority_class': priority_class, 'minimum_file_bytes': MIN_BYTES,
               'pid': os.getpid(), 'halt_reason': halt, 'totals': dict(totals),
               'free_before_plan': PLAN['free_before'], 'free_after': shutil.disk_usage(ROOT).free,
               'run_volume_before': run_volume_before, 'final_volume': volume_snapshot(),
               'all_content_verified': not halt and totals['verification_failed'] == 0 and totals['operation_failed'] == 0,
               'compressed_verified': totals['compressed_verified'], 'sample_results': run_results}
    receipt['processed_count'] = sum(v for k,v in totals.items() if k != 'saved_bytes')
    receipt['planned_count'] = PLAN['file_count']
    receipt['remaining_count'] = PLAN['file_count'] - receipt['processed_count']
    receipt['eligible_pass_complete'] = halt is None and receipt['remaining_count'] == 0
    write_json('pilot_receipt.json' if mode == 'pilot' else 'completion.json', receipt)
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['plan', 'repair_plan_ids', 'pilot', 'all'])
    args = parser.parse_args()
    if args.mode == 'plan':
        make_plan()
    elif args.mode == 'repair_plan_ids':
        repair_plan_ids()
    else:
        with RUN_LOCK.open('a+b') as lock:
            lock.seek(0)
            if not lock.read(1):
                lock.write(b'1')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                apply(args.mode)
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
