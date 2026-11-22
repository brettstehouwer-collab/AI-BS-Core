"""Current Windows process profile metadata, independent of environment values.

No profile files, credentials, registry values or other users are enumerated.
This does not create/load a profile, choose a recovery directory, migrate old
recovery partitions, or confer Firebase authority. Callers retain their existing
partition algorithm and protected recovery-directory validation.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import ntpath
import os
from pathlib import Path
import re

_TOKEN_QUERY = 0x0008
_INSUFFICIENT_BUFFER = 122
_MAX_PROFILE_CHARS = 32768
_SYSTEM32 = 0x00000800


class WindowsProfileError(RuntimeError):
    def __init__(self):
        super().__init__('The current Windows profile directory could not be confirmed.')


class _WindowsAPI:
    def __init__(self):
        # Only OS DLLs from System32; candidate PATH/CWD cannot select these.
        kernel = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=_SYSTEM32)
        security = ctypes.WinDLL('advapi32.dll', use_last_error=True, winmode=_SYSTEM32)
        profiles = ctypes.WinDLL('userenv.dll', use_last_error=True, winmode=_SYSTEM32)
        self._dlls = (kernel, security, profiles)
        self.current_process = kernel.GetCurrentProcess
        self.current_process.argtypes = []
        self.current_process.restype = wintypes.HANDLE
        self.open_process_token = security.OpenProcessToken
        self.open_process_token.argtypes = [wintypes.HANDLE, wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE)]
        self.open_process_token.restype = wintypes.BOOL
        self.profile_directory = profiles.GetUserProfileDirectoryW
        self.profile_directory.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD)]
        self.profile_directory.restype = wintypes.BOOL
        self.close_handle = kernel.CloseHandle
        self.close_handle.argtypes = [wintypes.HANDLE]
        self.close_handle.restype = wintypes.BOOL
        self.last_error = ctypes.get_last_error
        self.clear_error = lambda: ctypes.set_last_error(0)


def _local_profile_path(value):
    # Validate metadata only: no resolve/stat/open or environment expansion.
    if (not value or not re.match(r'^[A-Za-z]:[\\/]', value)
            or not ntpath.isabs(value) or ':' in value[2:]
            or any(ord(character) < 32 or character in '<>"|?*' for character in value)
            or any(part in {'.', '..'} for part in re.split(r'[\\/]', value[3:]))):
        raise WindowsProfileError()
    return Path(value)


def current_user_profile_directory() -> Path:
    """Return only the current process token's local profile root or fail closed.

    GetUserProfileDirectoryW needs TOKEN_QUERY, not impersonation or an inherited
    USERPROFILE/HOME value. Its sizes count UTF-16 WCHARs including the terminator.
    No environment/CWD/default-user fallback is permitted on any failure.
    """
    if os.name != 'nt':
        raise WindowsProfileError()
    api = None
    token = wintypes.HANDLE()
    owned = False
    try:
        api = _WindowsAPI()
        process = api.current_process()  # Borrowed pseudo-handle: NEVER close it.
        if not process or not api.open_process_token(process, _TOKEN_QUERY, ctypes.byref(token)):
            raise WindowsProfileError()
        if not token.value or token.value == ctypes.c_void_p(-1).value:
            raise WindowsProfileError()
        owned = True
        size = wintypes.DWORD()
        api.clear_error()
        if (api.profile_directory(token, None, ctypes.byref(size))
                or api.last_error() != _INSUFFICIENT_BUFFER
                or not 2 <= size.value <= _MAX_PROFILE_CHARS):
            raise WindowsProfileError()
        capacity = size.value
        buffer = ctypes.create_unicode_buffer(capacity)
        if not api.profile_directory(token, buffer, ctypes.byref(size)):
            raise WindowsProfileError()
        if not 2 <= size.value <= capacity:
            raise WindowsProfileError()
        value = buffer.value
        # Python counts a supplementary character once; Win32 counts two WCHARs.
        if len(value.encode('utf-16-le')) // 2 + 1 != size.value:
            raise WindowsProfileError()
        return _local_profile_path(value)
    except Exception:
        raise WindowsProfileError() from None
    finally:
        if owned:
            try:
                closed = api.close_handle(token)
            except Exception:
                raise WindowsProfileError() from None
            if not closed:
                raise WindowsProfileError() from None
