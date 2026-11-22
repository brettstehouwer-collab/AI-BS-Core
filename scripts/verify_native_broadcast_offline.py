"""Pre-import operational effect guard for reviewed native offline fixtures.

Only C-backed fixture writes are allowed. Denials fail the receipt even when
production exception handling swallows the raised guard error. No tests run on
import; invoke this runner only after the owner explicitly freezes the suite.
"""
from __future__ import annotations
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import sys
sys.dont_write_bytecode = True
import socket
import asyncio.proactor_events
_SOCKETPAIR_CODE = socket.socketpair.__code__
_SELFPIPE_CODE = asyncio.proactor_events.BaseProactorEventLoop._make_self_pipe.__code__
_SELFPIPE_EVENTS = {}
def allowed_stdlib_selfpipe(event, args):
    if event not in {'socket.__new__', 'socket.bind', 'socket.connect'}:
        return False
    frame = sys._getframe(1)
    pair = None
    owner = False
    for _ in range(18):
        if frame is None: break
        if frame.f_code is _SOCKETPAIR_CODE: pair = frame
        if frame.f_code is _SELFPIPE_CODE: owner = True
        frame = frame.f_back
    if pair is None or not owner:
        return False
    if pair.f_locals.get('family') not in (socket.AF_INET, socket.AF_INET6) or pair.f_locals.get('type') != socket.SOCK_STREAM or pair.f_locals.get('proto') != 0:
        return False
    if event == 'socket.__new__':
        permitted = len(args) >= 4 and args[1] in (socket.AF_INET, socket.AF_INET6) and args[2] == socket.SOCK_STREAM and args[3] == 0
    else:
        address = args[1]
        permitted = isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1') and ((event == 'socket.bind' and address[1] == 0) or (event == 'socket.connect' and address[1] == pair.f_locals.get('port') and address[0] == pair.f_locals.get('addr')))
    if permitted:
        _SELFPIPE_EVENTS[event] = _SELFPIPE_EVENTS.get(event, 0) + 1
    return permitted
from pathlib import Path
import json
import time
import unittest
from unittest.mock import patch
ROOT = Path('C:/AI-BS')
WORK = ROOT / 'backups/native_broadcast207_work/guarded_native'
WORK.mkdir(parents=True, exist_ok=True)
TEMP = WORK / 'tmp'
TEMP.mkdir(exist_ok=True)
for name in ('TMP', 'TEMP', 'TMPDIR'):
    os.environ[name] = str(TEMP)
import tempfile
tempfile.tempdir = str(TEMP)
sys.path.insert(0, str(ROOT))
ALLOWED = (str(WORK).replace('\\', '/').casefold(), str(ROOT / 'backups/native_broadcast207_work/atomic_fixtures').replace('\\', '/').casefold())
# Dedicated, verified C-only synthetic Win32 sharing fixtures.
ALLOWED += (str(ROOT / 'backups/native_broadcast_preview209_work/ipc_hotfix209/fixtures').replace('\\', '/').casefold(),)
DENIED_NAMES = {'.env', 'stream_profiles.json', 'drip_ledger.json', 'crypto_ledger.json', 'broadcast_secondary_status.json', 'broadcast_secondary_command.json', 'broadcast_secondary.stop'}
denials = []

def normalize(path):
    if isinstance(path, int) or path is None:
        return ''
    try:
        return os.path.abspath(os.fsdecode(path)).replace('\\', '/').casefold().rstrip('/')
    except (ValueError, TypeError):
        return ''

def fixture(path):
    value = normalize(path)
    return any((value == root or value.startswith(root + '/') for root in ALLOWED))

def deny(kind, path=None):
    denials.append({'effect': kind, 'basename': Path(str(path)).name if path is not None else None})
    raise RuntimeError('OPERATIONAL_EFFECT_DENIED:' + kind)

def read_guard(path):
    value = normalize(path)
    if not value or fixture(path):
        return
    if value.startswith('e:') or value.endswith(('.db', '.sqlite', '.sqlite3')) or value.rsplit('/', 1)[-1] in DENIED_NAMES or value.startswith('c:/ai-bs/saved_data/') or value.startswith('c:/ai-bs/recordings/'):
        deny('operational_read', path)

def write_guard(path):
    if not fixture(path):
        deny('operational_write', path)

def audit(event, args):
    if allowed_stdlib_selfpipe(event, args):
        return
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec', 'os.startfile', 'socket.connect', 'socket.bind', 'socket.__new__', 'winreg.OpenKey', 'winreg.CreateKey', 'winreg.SetValue'}:
        deny(event)
    if event == 'open' and args:
        path = args[0]
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        writes = isinstance(mode, str) and any((c in mode for c in 'wax+'))
        writes = writes or (isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        write_guard(path) if writes else read_guard(path)
    elif event in {'os.remove', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.truncate', 'os.unlink'} and args:
        write_guard(args[0])
    elif event in {'os.rename', 'os.link', 'os.symlink'} and args:
        write_guard(args[0])
        write_guard(args[1])
sys.addaudithook(audit)
for name in ('stat', 'lstat'):
    original = getattr(os, name)

    def guarded(path, *args, _original=original, **kwargs):
        read_guard(path)
        return _original(path, *args, **kwargs)
    setattr(os, name, guarded)
import win32file, win32security, win32api, win32process, win32crypt

def wrap_path(module, name, write=False):
    if not hasattr(module, name):
        return
    original = getattr(module, name)

    def guarded(path, *args, **kwargs):
        write_guard(path) if write else read_guard(path)
        return original(path, *args, **kwargs)
    setattr(module, name, guarded)
for name in ('CreateDirectory', 'DeleteFile', 'RemoveDirectory', 'SetFileAttributes'):
    wrap_path(win32file, name, True)
_create = win32file.CreateFile

def create_file(path, *args, **kwargs):
    write_guard(path)
    return _create(path, *args, **kwargs)
win32file.CreateFile = create_file
wrap_path(win32security, 'GetNamedSecurityInfo')
wrap_path(win32security, 'SetNamedSecurityInfo', True)
for module, names in ((win32api, ('ShellExecute', 'TerminateProcess')), (win32process, ('CreateProcess', 'TerminateProcess'))):
    for name in names:
        if hasattr(module, name):
            setattr(module, name, lambda *a, _name=name, **kw: deny(_name))
_protect = win32crypt.CryptProtectData
_unprotect = win32crypt.CryptUnprotectData
_synthetic_blobs = set()

def protect_synthetic(data, *args, **kwargs):
    if type(data) is not bytes or data != b'synthetic-credential-only':
        deny('DPAPI.protect')
    result = _protect(data, *args, **kwargs)
    _synthetic_blobs.add(bytes(result))
    return result

def unprotect_synthetic(data, *args, **kwargs):
    if type(data) not in (bytes, bytearray) or bytes(data) not in _synthetic_blobs:
        deny('DPAPI.unprotect')
    return _unprotect(data, *args, **kwargs)
win32crypt.CryptProtectData = protect_synthetic
win32crypt.CryptUnprotectData = unprotect_synthetic
import psutil
for name in ('terminate', 'kill', 'send_signal'):
    setattr(psutil.Process, name, lambda *a, _name=name, **kw: deny('psutil.' + _name))
import ctypes
user32 = ctypes.windll.user32
for name in ('OpenInputDesktop', 'EnumWindows', 'EnumDesktopWindows', 'GetForegroundWindow', 'GetWindowTextW', 'GetWindowRect', 'PrintWindow', 'GetDC'):
    setattr(user32, name, lambda *a, _name=name, **kw: deny('user32.' + _name))
from PyQt6.QtGui import QScreen
QScreen.grabWindow = lambda *a, **kw: deny('QScreen.grabWindow')
from PyQt6.QtMultimedia import QMediaPlayer
QMediaPlayer.setSource = lambda *a, **kw: deny('QMediaPlayer.setSource')
QMediaPlayer.play = lambda *a, **kw: deny('QMediaPlayer.play')

from backend.core import native_window_capture
native_window_capture._capture_class = lambda: deny('WGC.capture')
# Old UI fixtures use a fake decoder; actual preview tests inject fake media.
# Keep the real preview module available for its independent contract tests.
from scripts.tests.test_preview_ui209 import FakeNativePreview
from native_studio import omni_broadcast_studio as preview_studio
preview_studio.NativeBroadcastPreview = FakeNativePreview
GROUPS = ('scripts.tests.test_native_broadcast_truth204', 'scripts.tests.test_native_broadcast_validation205', 'scripts.tests.test_native_broadcast_setup205', 'scripts.tests.test_native_broadcast_preview205', 'scripts.tests.test_broadcast_service205', 'scripts.tests.test_native_broadcast_coordinator207', 'scripts.tests.test_private_broadcast_ipc207', 'scripts.tests.test_broadcast_ipc_atomic207', 'scripts.tests.test_game_capture_selection206', 'scripts.tests.test_game_selection_sampler207', 'scripts.tests.test_game_follow_capture207', 'scripts.tests.test_secondary_control207', 'scripts.tests.test_broadcast_secondary206', 'scripts.tests.test_broadcast_relay206', 'scripts.tests.test_broadcast_daemon_integrity', 'scripts.tests.test_broadcast_capture_inputs205', 'scripts.tests.test_window_capture_pipe205', 'scripts.tests.test_native_window_capture205', 'scripts.tests.test_legacy_broadcast_guard207', 'scripts.tests.test_native_connection_diagnostics')

GROUPS += ('scripts.tests.test_preview_ui209',
           'scripts.tests.test_broadcast_preview209',
           'scripts.tests.test_native_broadcast_retirement209',
           'scripts.tests.test_native_executive_service',
           'scripts.tests.test_native_executive_view',
           'scripts.tests.test_native_telemetry_truth',
           'scripts.tests.test_native_window_shutdown',
           'scripts.tests.test_broadcast_ipc_sharing209')

GROUPS += ('scripts.tests.test_preview_ui210',)

def main():
    names = sys.argv[1:] or list(GROUPS)
    if any((not any((name == group or name.startswith(group + '.') for group in GROUPS)) for name in names)):
        raise ValueError('Only reviewed native fixture groups are permitted')
    stamp = str(time.time_ns())
    result = None
    error = None
    path = WORK / ('run_' + stamp)
    path.mkdir()
    try:
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        with (path / 'tests.log').open('w', encoding='utf-8') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    except Exception as failure:
        error = type(failure).__name__ + ': ' + str(failure)
    receipt = {'groups': names, 'tests': None if result is None else result.testsRun, 'failures': None if result is None else len(result.failures), 'errors': None if result is None else len(result.errors), 'guard_denials': denials, 'stdlib_local_self_pipe_events': _SELFPIPE_EVENTS, 'runner_error': error, 'passed': bool(result and result.wasSuccessful() and (not denials) and (error is None)), 'evidence': str(path), 'real_runtime_actions_authorized': False}
    (path / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
    return 0 if receipt['passed'] else 1
if __name__ == '__main__':
    sys.exit(main())
