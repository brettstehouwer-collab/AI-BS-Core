"""Fresh Windows handle-relative immutable blob leases, not a database factory.

Only a NEW protected root can be created. Each leaf is an opaque SHA-256 name,
exclusively created relative to its retained root handle, explicitly protected,
and held with no sharing until close. Reads use that same file handle; no path
is reopened. Original bytes are never normalized, replaced, repaired or deleted.
Any native/policy/integrity failure taints the lease; partial evidence remains.
No-sharing blocks data opens/rename, not all metadata operations: native tests
show the trusted user CAN create a hardlink or change the DACL. Metadata/hash
checks reject observed changes; they are not atomic prevention across later I/O.

Limits are per-lease logical bytes/count, not physical disk/global quotas. Close
releases exclusivity and leaves data. Reopen/recovery, ancestor effective-access
admission, an exclusive persistent broker, SQLite/Chroma integration and runtime
trust remain separate work. Same-user code, SYSTEM and Administrators are trusted.
No production route/startup, corpus activation or project execution is provided.
"""
import ctypes
import hashlib
import os
import re
import threading

from .theatrical_corpus_boundary import CorpusBoundaryError
from . import theatrical_storage_roots as roots

if os.name == 'nt':
    from ctypes import wintypes
    import pywintypes
    import win32file
    import win32security

MAX_BLOB_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_BLOBS = 32


def _fail(code):
    raise CorpusBoundaryError(code) from None


def _blob_id(value):
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value):
        _fail('INVALID_CORPUS_BLOB_ID')
    return value


def _create_blob(parent, digest, sid):
    """FILE_CREATE exclusively; never open, truncate or follow an existing leaf."""
    descriptor = ctypes.c_void_p()
    try:
        sddl = f'O:{sid}D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;{sid})'
        if not roots._adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ctypes.byref(descriptor), None):
            _fail('CORPUS_BLOB_DESCRIPTOR_UNAVAILABLE')
        name = _blob_id(digest) + '.blob'
        buffer = ctypes.create_unicode_buffer(name)
        unicode = roots._UnicodeString(len(name)*2, (len(name)+1)*2,
                                       ctypes.cast(buffer, ctypes.c_void_p))
        attributes = roots._ObjectAttributes(ctypes.sizeof(roots._ObjectAttributes), int(parent),
            ctypes.pointer(unicode), 0x40 | 0x1000, descriptor, None)
        io, raw = roots._IOStatus(), wintypes.HANDLE()
        # Generic read/write mapped to file rights; no DELETE/execute/write-DACL.
        # No sharing. Synchronous, non-directory, open-reparse (never traverse).
        status = roots._nt.NtCreateFile(ctypes.byref(raw), 0x12019F, ctypes.byref(attributes),
            ctypes.byref(io), None, 0x80, 0, 2, 0x200000 | 0x20 | 0x40, None, 0)
        if status < 0:
            _fail('CORPUS_BLOB_CREATE_REFUSED')
        return pywintypes.HANDLE(raw.value)
    finally:
        if descriptor.value:
            roots._kernel.LocalFree(descriptor)


def _metadata(handle, sid, volume, length, identity=None):
    info = win32file.GetFileInformationByHandle(handle)
    actual_identity = (info[4], info[8], info[9])
    if (win32file.GetFileType(handle) != 1 or info[0] & (0x400 | 0x10)
            or info[7] != 1 or info[4] != volume
            or (info[5] << 32 | info[6]) != length
            or identity is not None and actual_identity != identity):
        _fail('CORPUS_BLOB_METADATA_CHANGED')
    sd = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
        win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
    owner = win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner())
    control, _ = sd.GetSecurityDescriptorControl()
    acl = sd.GetSecurityDescriptorDacl()
    if (owner != sid or not control & 4 or not control & 0x1000
            or acl is None or acl.GetAceCount() != 3):
        _fail('CORPUS_BLOB_ACL_REFUSED')
    trustees = set()
    for index in range(acl.GetAceCount()):
        ace = acl.GetAce(index)
        if len(ace) != 3 or ace[0] != (0, 0) or ace[1] != 0x1F01FF:
            _fail('CORPUS_BLOB_ACL_REFUSED')
        trustee = win32security.ConvertSidToStringSid(ace[2])
        if trustee in trustees:
            _fail('CORPUS_BLOB_ACL_REFUSED')
        trustees.add(trustee)
    if trustees != {sid, 'S-1-5-18', 'S-1-5-32-544'}:
        _fail('CORPUS_BLOB_ACL_REFUSED')
    return actual_identity


def _write_bytes(handle, data):
    win32file.SetFilePointer(handle, 0, 0)
    for offset in range(0, len(data), 64 * 1024):
        part = data[offset:offset + 64 * 1024]
        error, count = win32file.WriteFile(handle, part)
        if error != 0 or count != len(part):
            _fail('CORPUS_BLOB_SHORT_WRITE')
    win32file.FlushFileBuffers(handle)


def _read_bytes(handle, length):
    win32file.SetFilePointer(handle, 0, 0)
    parts, remaining = [], length
    while remaining:
        error, part = win32file.ReadFile(handle, min(remaining, 64 * 1024))
        if error != 0 or not part or len(part) > remaining:
            _fail('CORPUS_BLOB_SHORT_READ')
        parts.append(part)
        remaining -= len(part)
    return b''.join(parts)


class ImmutableCorpusBlobs:
    """One fresh root and retained file handles; close never removes any bytes."""
    def __init__(self):
        _fail('CORPUS_BLOB_FACTORY_REQUIRED')

    @classmethod
    def create(cls, path):
        lease = object.__new__(cls)
        lease._lock = threading.RLock()
        lease._closed = False
        lease._tainted = False
        lease._entries = {}
        lease._reserved_bytes = 0
        lease._root = roots.ProtectedCorpusRoot.create(path)
        lease._volume = int(lease._root.identity[:8], 16)
        return lease

    def _available(self):
        if self._closed:
            _fail('CORPUS_BLOB_CLOSED')
        if self._tainted:
            _fail('CORPUS_BLOB_TAINTED')

    def _read_entry(self, digest):
        entry = self._entries[digest]
        handle, length, identity = entry['handle'], entry['length'], entry['identity']
        _metadata(handle, self._root.broker_sid, self._volume, length, identity)
        data = _read_bytes(handle, length)
        _metadata(handle, self._root.broker_sid, self._volume, length, identity)
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            _fail('CORPUS_BLOB_HASH_CHANGED')
        return data

    def _native_failure(self, exc):
        self._tainted = True
        if not isinstance(exc, Exception):
            raise exc from None
        if isinstance(exc, CorpusBoundaryError):
            raise exc from None
        _fail('CORPUS_BLOB_IO_UNAVAILABLE')

    def put(self, data):
        if type(data) is not bytes or len(data) > MAX_BLOB_BYTES:
            _fail('INVALID_CORPUS_BLOB_BYTES')
        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            self._available()
            if digest not in self._entries and (len(self._entries) >= MAX_BLOBS
                    or self._reserved_bytes + len(data) > MAX_TOTAL_BYTES):
                _fail('CORPUS_BLOB_QUOTA')
            try:
                self._root.verify()
                if digest in self._entries:
                    if self._read_entry(digest) != data:
                        _fail('CORPUS_BLOB_HASH_CHANGED')
                else:
                    # Failures consume the lease: never delete partials/retry a
                    # path or release a handle behind a failed operation.
                    self._reserved_bytes += len(data)
                    handle = _create_blob(self._root._handles[-1], digest, self._root.broker_sid)
                    entry = dict(handle=handle, length=len(data), identity=None)
                    self._entries[digest] = entry
                    identity = _metadata(handle, self._root.broker_sid, self._volume, 0)
                    entry['identity'] = identity
                    _write_bytes(handle, data)
                    if self._read_entry(digest) != data:
                        _fail('CORPUS_BLOB_HASH_CHANGED')
                self._root.verify()
                return digest
            except BaseException as exc:
                self._native_failure(exc)

    def read(self, digest):
        _blob_id(digest)
        with self._lock:
            self._available()
            if digest not in self._entries:
                _fail('UNKNOWN_CORPUS_BLOB')
            try:
                self._root.verify()
                data = self._read_entry(digest)
                self._root.verify()
                return data
            except BaseException as exc:
                self._native_failure(exc)

    def verify(self):
        with self._lock:
            self._available()
            try:
                self._root.verify()
                for digest in self._entries:
                    self._read_entry(digest)
                self._root.verify()
            except BaseException as exc:
                self._native_failure(exc)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            failed = False
            for entry in self._entries.values():
                try:
                    entry['handle'].Close()
                except Exception:
                    failed = True
            try:
                self._root.close()
            except Exception:
                failed = True
            if failed:
                _fail('CORPUS_BLOB_CLOSE_UNAVAILABLE')

    def __enter__(self):
        self.verify()
        return self

    def __exit__(self, *_):
        self.close()
