"""Inert-by-default, local reviewed manifest for the scoped creative writer.

This module neither starts a process nor configures a router. Enabling this
manifest only returns the fixed reviewed specification to the trusted backend
lifecycle. Its listed files are a limited source/executable snapshot, not an
attestation of all Python packages, Qt plugins or Windows DLLs.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import ntpath
import os
from pathlib import Path
import sys

from security.native_creative_controller import (
    PIPE_BOOTSTRAP_CONTRACT, ReviewedCandidate, ReviewedFile, _PinnedFiles, NativeControllerError,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / 'state/native_creative_candidate.json'
MAX_CONFIG_BYTES = 65536
SOURCE_RELATIVE_PATHS = (
    'native_studio/native_creative_entry.py',
    'native_studio/creative_session.py',
    'native_studio/creative_pipe_bootstrap.py',
    'native_studio/creative_pipe_transport.py',
    'native_studio/creative_pipe_io.py',
    'native_studio/creative_wire.py',
    'native_studio/screenplay_client.py',
    'native_studio/rich_screenplay_draft.py',
    'native_studio/local_connection.py',
    'native_studio/windows_profile.py',
    'native_studio/screenwriting_view.py',
    'native_studio/engine.py',
    'native_studio/theme.py',
)


class NativeCreativeConfigError(ValueError):
    def __init__(self):
        super().__init__('The reviewed native creative configuration is unavailable or invalid.')


def candidate_layout():
    """Return fixed noncredential paths/arguments; never generate or enable pins."""
    launcher = str(ROOT / 'runtime/devtools/native_creative_writer.py')
    system_root = str(Path(os.environ.get('SYSTEMROOT', r'C:\Windows')).resolve())
    qt_bin = str(ROOT / 'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin')
    dependencies = [launcher, *(str(ROOT / name) for name in SOURCE_RELATIVE_PATHS)]
    initializer = ROOT / 'native_studio/__init__.py'
    if initializer.is_file():
        dependencies.append(str(initializer))
    return {
        'executable_path': str(Path(sys._base_executable).resolve()),
        'arguments': ['-I', '-B', launcher, '--native-creative-pipe-bootstrap'],
        'cwd': str(ROOT),
        'environment': [['SYSTEMROOT', system_root],
                        ['PATH', qt_bin + ';' + str(Path(system_root) / 'System32')]],
        'dependency_paths': dependencies,
        'contract': PIPE_BOOTSTRAP_CONTRACT,
        'capacity': 1,
    }


def _no_redirects(path):
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if (component.is_symlink() or getattr(component, 'is_junction', lambda: False)()
                or getattr(info, 'st_file_attributes', 0) & 0x400):
            raise NativeCreativeConfigError()


def _read_manifest(path):
    path = Path(path).absolute()
    _no_redirects(path)
    try:
        expected_path = str(path.resolve(strict=True))
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_CONFIG_BYTES or before.st_nlink != 1:
                raise NativeCreativeConfigError()
            if os.name == 'nt':
                import msvcrt
                api = ctypes.WinDLL('kernel32', use_last_error=True)
                api.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                                        wintypes.DWORD, wintypes.DWORD]
                final = ctypes.create_unicode_buffer(32768)
                count = api.GetFinalPathNameByHandleW(msvcrt.get_osfhandle(stream.fileno()),
                                                     final, len(final), 0)
                actual = final.value.removeprefix('\\\\?\\')
                if (not 0 < count < len(final)
                        or ntpath.normcase(actual) != ntpath.normcase(expected_path)):
                    raise NativeCreativeConfigError()
            raw = stream.read(MAX_CONFIG_BYTES + 1)
            after = os.fstat(stream.fileno())
        _no_redirects(path)
        current = path.stat(follow_symlinks=False)
        if (len(raw) > MAX_CONFIG_BYTES or len(raw) != before.st_size
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)):
            raise NativeCreativeConfigError()
        return raw
    except FileNotFoundError:
        # A missing file disables the lane; this never creates a template.
        return None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NativeCreativeConfigError()
        result[key] = value
    return result


def _no_constant(value):
    raise NativeCreativeConfigError()


def _pin(value, expected_path):
    if (type(value) is not dict or set(value) != {'path', 'sha256'}
            or value['path'] != expected_path):
        raise NativeCreativeConfigError()
    return ReviewedFile(value['path'], value['sha256'])


def _verify_pins(candidate):
    pins = _PinnedFiles(candidate)
    pins.close()


def load_reviewed_candidate(path=DEFAULT_CONFIG_PATH):
    """Return one fixed v2 candidate or None; never launch, import Qt or activate.

    Both a minimal disabled record and a complete disabled review manifest are
    supported. A complete disabled manifest has its schema/self-hash checked but
    does not open candidate files. Enabled manifests also verify current listed
    bytes; the controller independently retains/rechecks file pins at each launch.
    """
    try:
        raw = _read_manifest(path)
        if raw is None:
            return None
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                           parse_constant=_no_constant)
        if (type(value) is not dict or type(value.get('schema')) is not int
                or value['schema'] != 1 or type(value.get('enabled')) is not bool):
            raise NativeCreativeConfigError()
        if value['enabled'] is False and set(value) == {'schema', 'enabled'}:
            return None
        if set(value) != {'schema', 'enabled', 'contract', 'capacity', 'candidate', 'candidate_sha256'}:
            raise NativeCreativeConfigError()
        layout = candidate_layout()
        if (value['contract'] != layout['contract'] or type(value['capacity']) is not int
                or value['capacity'] != 1):
            raise NativeCreativeConfigError()
        spec = value['candidate']
        if (type(spec) is not dict
                or set(spec) != {'executable', 'arguments', 'cwd', 'environment', 'dependencies'}
                or spec['arguments'] != layout['arguments'] or spec['cwd'] != layout['cwd']
                or spec['environment'] != layout['environment']
                or type(spec['dependencies']) is not list
                or len(spec['dependencies']) != len(layout['dependency_paths'])):
            raise NativeCreativeConfigError()
        candidate = ReviewedCandidate(
            _pin(spec['executable'], layout['executable_path']),
            tuple(spec['arguments']), spec['cwd'],
            tuple(tuple(pair) for pair in spec['environment']),
            tuple(_pin(pin, expected) for pin, expected in
                  zip(spec['dependencies'], layout['dependency_paths'])),
            value['contract'],
        )
        if type(value['candidate_sha256']) is not str or value['candidate_sha256'] != candidate.sha256:
            raise NativeCreativeConfigError()
        if value['enabled'] is False:
            return None
        _verify_pins(candidate)
        return candidate
    except NativeCreativeConfigError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, NativeControllerError):
        raise NativeCreativeConfigError() from None
