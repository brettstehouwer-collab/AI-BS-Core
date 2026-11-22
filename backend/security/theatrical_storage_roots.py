"""New, protected Windows directory leases; deliberately not a storage factory.

Creates one ABSENT leaf only. Never adopts, repairs, deletes or opens existing
corpus contents. Caller and root owner/DACL are measured from real Windows
handles, not supplied metadata. All ancestors remain open without DELETE sharing;
child opens/creation are relative to held handles and refuse reparse traversal.

The process user, SYSTEM and Administrators are trusted. This does NOT isolate
other code running as that user, prove its runtime/dependency trust, exclude
privileged administrators, validate future descendants, reopen a prior store,
or grant worker/project execution. No production startup wiring is provided.
Ancestor ACL/effective-access admission is not implemented: held handles constrain
rename, not every metadata mutation. path is a diagnostic label, NOT an admitted
SQLite/Chroma locator. Future storage I/O requires a separately reviewed broker
and handle-relative descendant operations; verify() is only an observation.
"""
import ctypes
import os
import re
import threading

from .theatrical_corpus_boundary import CorpusBoundaryError

if os.name == 'nt':
    from ctypes import wintypes
    import pywintypes
    import win32api
    import win32con
    import win32file
    import win32security


def _fail(code):
    raise CorpusBoundaryError(code) from None


def _parts(path):
    if (type(path) is not str or not 1 <= len(path) <= 1024
            or not re.fullmatch(r'[A-Z]:\\[^/]+', path)):
        _fail('INVALID_CORPUS_STORAGE_PATH')
    parts = path[3:].split('\\')
    if not 2 <= len(parts) <= 16:
        _fail('INVALID_CORPUS_STORAGE_PATH')
    for part in parts:
        if (not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_. -]{0,95}', part)
                or part.endswith(('.', ' '))
                or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])', part.split('.')[0], re.I)):
            _fail('INVALID_CORPUS_STORAGE_PATH')
    return path[:3], parts


def _current_principal():
    """No impersonation or privilege adjustment; obtain process user's actual SID."""
    try:
        try:
            token = win32security.OpenThreadToken(win32api.GetCurrentThread(), win32con.TOKEN_QUERY, True)
        except pywintypes.error as exc:
            if exc.winerror != 1008:  # ERROR_NO_TOKEN only
                raise
        else:
            token.Close()
            _fail('CORPUS_STORAGE_IMPERSONATION_REFUSED')
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            sid = win32security.ConvertSidToStringSid(
                win32security.GetTokenInformation(token, win32security.TokenUser)[0])
        finally:
            token.Close()
        if not re.fullmatch(r'S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+', sid):
            _fail('CORPUS_STORAGE_PRINCIPAL_REFUSED')
        return sid
    except CorpusBoundaryError:
        raise
    except Exception:
        _fail('CORPUS_STORAGE_PRINCIPAL_UNAVAILABLE')


def _validate_descriptor(sd, sid):
    """Accept only the exact new-directory policy, no generic ACL inference."""
    try:
        owner = win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner())
        control, _ = sd.GetSecurityDescriptorControl()
        acl = sd.GetSecurityDescriptorDacl()
        expected = {sid, 'S-1-5-18', 'S-1-5-32-544'}
        if (owner != sid or not control & 0x1000 or not control & 4
                or acl is None or acl.GetAceCount() != len(expected)):
            _fail('CORPUS_STORAGE_ACL_REFUSED')
        actual = set()
        for index in range(acl.GetAceCount()):
            ace = acl.GetAce(index)
            if (len(ace) != 3 or ace[0] != (0, 3) or ace[1] != 0x1F01FF):
                _fail('CORPUS_STORAGE_ACL_REFUSED')
            trustee = win32security.ConvertSidToStringSid(ace[2])
            if trustee in actual:
                _fail('CORPUS_STORAGE_ACL_REFUSED')
            actual.add(trustee)
        if actual != expected:
            _fail('CORPUS_STORAGE_ACL_REFUSED')
    except CorpusBoundaryError:
        raise
    except Exception:
        _fail('CORPUS_STORAGE_ACL_REFUSED')


if os.name == 'nt':
    class _UnicodeString(ctypes.Structure):
        _fields_ = [('Length', wintypes.USHORT), ('MaximumLength', wintypes.USHORT),
                    ('Buffer', ctypes.c_void_p)]

    class _ObjectAttributes(ctypes.Structure):
        _fields_ = [('Length', wintypes.ULONG), ('RootDirectory', wintypes.HANDLE),
                    ('ObjectName', ctypes.POINTER(_UnicodeString)), ('Attributes', wintypes.ULONG),
                    ('SecurityDescriptor', ctypes.c_void_p), ('SecurityQualityOfService', ctypes.c_void_p)]

    class _IOStatus(ctypes.Structure):
        _fields_ = [('Status', ctypes.c_void_p), ('Information', ctypes.c_size_t)]

    _nt = ctypes.WinDLL('ntdll', use_last_error=True)
    _nt.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG,
        ctypes.POINTER(_ObjectAttributes), ctypes.POINTER(_IOStatus), ctypes.c_void_p,
        wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG]
    _nt.NtCreateFile.restype = wintypes.LONG
    _adv = ctypes.WinDLL('advapi32', use_last_error=True)
    _adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.ULONG)]
    _adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    _kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    _kernel.LocalFree.argtypes = [ctypes.c_void_p]
    _kernel.LocalFree.restype = ctypes.c_void_p
    _kernel.GetVolumeInformationByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR, wintypes.DWORD]
    _kernel.GetVolumeInformationByHandleW.restype = wintypes.BOOL


def _details(handle):
    info = win32file.GetFileInformationByHandle(handle)
    if info[0] & 0x400 or not info[0] & 0x10:  # reparse point / directory
        _fail('CORPUS_STORAGE_REPARSE_OR_TYPE_REFUSED')
    return info[4], f'{info[4]:08x}:{info[8]:08x}{info[9]:08x}'


def _child(parent, name, descriptor=None):
    buffer = ctypes.create_unicode_buffer(name)
    unicode = _UnicodeString(len(name) * 2, (len(name) + 1) * 2, ctypes.cast(buffer, ctypes.c_void_p))
    attributes = _ObjectAttributes(ctypes.sizeof(_ObjectAttributes), int(parent),
        ctypes.pointer(unicode), 0x40 | 0x1000, descriptor, None)  # CASE_INSENSITIVE | DONT_REPARSE
    io, raw = _IOStatus(), wintypes.HANDLE()
    # LIST_DIRECTORY establishes data-read sharing. Attribute-only opens do not
    # constrain rename/delete sharing on this Windows runtime (native regression).
    status = _nt.NtCreateFile(ctypes.byref(raw), 0x120081, ctypes.byref(attributes), ctypes.byref(io),
        None, 0x10, 3, 2 if descriptor is not None else 1,
        0x200000 | 0x20 | 1, None, 0)  # OPEN_REPARSE_POINT | SYNC_NONALERT | DIRECTORY
    if status < 0:
        _fail('CORPUS_STORAGE_CREATE_REFUSED' if descriptor is not None else 'CORPUS_STORAGE_OPEN_REFUSED')
    return pywintypes.HANDLE(raw.value)


class ProtectedCorpusRoot:
    """Trusted infrastructure primitive. Closing releases handles, retains ALL data."""
    def __init__(self):
        _fail('CORPUS_STORAGE_FACTORY_REQUIRED')

    @classmethod
    def create(cls, path):
        drive, parts = _parts(path)
        if os.name != 'nt':
            _fail('CORPUS_STORAGE_WINDOWS_REQUIRED')
        root = object.__new__(cls)
        root._handles = []
        root._identities = []
        root._lock = threading.RLock()
        root._path = path
        root._closed = False
        root._sid = _current_principal()
        descriptor = ctypes.c_void_p()
        try:
            if win32file.GetDriveType(drive) != 3:
                _fail('CORPUS_STORAGE_FIXED_VOLUME_REQUIRED')
            handle = win32file.CreateFile('\\\\?\\' + drive, 0x120081, 3, None, 3,
                                          0x02000000 | 0x00200000, None)
            root._handles.append(handle)
            volume, identity = _details(handle)
            root._identities.append(identity)
            fs = ctypes.create_unicode_buffer(32)
            serial, maximum, flags = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
            if (not _kernel.GetVolumeInformationByHandleW(int(handle), None, 0, ctypes.byref(serial),
                    ctypes.byref(maximum), ctypes.byref(flags), fs, len(fs)) or fs.value != 'NTFS'):
                _fail('CORPUS_STORAGE_NTFS_REQUIRED')
            for part in parts[:-1]:
                handle = _child(handle, part)
                root._handles.append(handle)
                actual_volume, identity = _details(handle)
                root._identities.append(identity)
                if actual_volume != volume:
                    _fail('CORPUS_STORAGE_VOLUME_CHANGED')
            sddl = f'O:{root._sid}D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{root._sid})'
            if not _adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1,
                    ctypes.byref(descriptor), None):
                _fail('CORPUS_STORAGE_DESCRIPTOR_UNAVAILABLE')
            handle = _child(handle, parts[-1], descriptor)
            root._handles.append(handle)
            actual_volume, root._identity = _details(handle)
            root._identities.append(root._identity)
            if actual_volume != volume:
                _fail('CORPUS_STORAGE_VOLUME_CHANGED')
            root.verify()
            return root
        except CorpusBoundaryError:
            root.close()
            raise
        except Exception:
            root.close()
            _fail('CORPUS_STORAGE_NATIVE_UNAVAILABLE')
        finally:
            if descriptor.value:
                _kernel.LocalFree(descriptor)

    @property
    def path(self):
        """Diagnostic label only; not authorization to open a database by pathname."""
        return self._path

    @property
    def broker_sid(self):
        return self._sid

    @property
    def identity(self):
        return self._identity

    def verify(self):
        with self._lock:
            if self._closed:
                _fail('CORPUS_STORAGE_CLOSED')
            if _current_principal() != self._sid:
                _fail('CORPUS_STORAGE_CALLER_CHANGED')
            try:
                for handle, identity in zip(self._handles, self._identities, strict=True):
                    if _details(handle)[1] != identity:
                        _fail('CORPUS_STORAGE_IDENTITY_CHANGED')
                descriptor = win32security.GetSecurityInfo(self._handles[-1], win32security.SE_FILE_OBJECT,
                    win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
                _validate_descriptor(descriptor, self._sid)
            except CorpusBoundaryError:
                raise
            except Exception:
                _fail('CORPUS_STORAGE_NATIVE_UNAVAILABLE')

    def close(self):
        with self._lock:
            self._closed = True
            handles, self._handles = self._handles, []
            for handle in reversed(handles):
                handle.Close()

    def __enter__(self):
        self.verify()
        return self

    def __exit__(self, *_):
        self.close()
