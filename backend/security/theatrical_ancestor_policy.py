"""Conservative Windows ancestor ACL admission for a fresh blob lease.

Dormant infrastructure only. This is an allow-list of descriptor shapes, NOT
Windows AccessCheck, worker-token admission, a persistent broker, or atomic
protection against trusted-user metadata changes. The broker user, SYSTEM,
Administrators and TrustedInstaller are trusted ancestor owners/trustees.
Untrusted effective grants may read/traverse or create NEW children, but may not
change existing ancestor metadata, delete children, or change security. Denies
never cancel an unsafe allow. Unknown ACE types/flags fail closed.

Ancestors are opened without delete sharing BEFORE creating the absent leaf.
Both handle chains must identify the same objects. Every operation checks the
retained ancestors before and after I/O; observed failures taint the lease.
No existing ACL or bytes are repaired, adopted, overwritten, or deleted. No
production storage locator, API wiring, reopen/recovery or execution grant.
"""
import os
import threading

from .theatrical_corpus_boundary import CorpusBoundaryError
from . import theatrical_storage_blobs as blobs
from . import theatrical_storage_roots as roots

if os.name == 'nt':
    import win32file
    import win32security

TRUSTED_INSTALLER = 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464'
_SAFE_UNTRUSTED = (0x1 | 0x2 | 0x4 | 0x8 | 0x20 | 0x80 | 0x20000 | 0x100000
                   | 0x80000000 | 0x20000000)


def _fail(code):
    raise CorpusBoundaryError(code) from None


def validate_ancestor_descriptor(sd, broker_sid):
    """Trusted-infrastructure helper; evaluates actual descriptors, not access."""
    try:
        trusted = {broker_sid, 'S-1-5-18', 'S-1-5-32-544', TRUSTED_INSTALLER}
        owner = win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner())
        control, _ = sd.GetSecurityDescriptorControl()
        acl = sd.GetSecurityDescriptorDacl()
        if owner not in trusted or not control & 4 or acl is None:
            _fail('CORPUS_ANCESTOR_ACL_REFUSED')
        for index in range(acl.GetAceCount()):
            ace = acl.GetAce(index)
            if (len(ace) != 3 or len(ace[0]) != 2 or ace[0][0] not in (0, 1)
                    or ace[0][1] & ~0x1f):
                _fail('CORPUS_ANCESTOR_ACL_REFUSED')
            trustee = win32security.ConvertSidToStringSid(ace[2])
            mask = int(ace[1]) & 0xffffffff
            if ace[0][1] & 8 or ace[0][0] == 1:  # inherit-only or deny
                continue
            if trustee not in trusted and mask & ~_SAFE_UNTRUSTED:
                _fail('CORPUS_ANCESTOR_ACL_REFUSED')
    except CorpusBoundaryError:
        raise
    except Exception:
        _fail('CORPUS_ANCESTOR_ACL_REFUSED')


def _check_ancestors(handles, sid):
    for handle in handles:
        sd = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
        validate_ancestor_descriptor(sd, sid)


class AncestorGuardedBlobs:
    """Fresh lease only, with serialized ancestor observations around blob I/O."""
    def __init__(self):
        _fail('CORPUS_ANCESTOR_FACTORY_REQUIRED')

    @classmethod
    def create(cls, path):
        drive, parts = roots._parts(path)
        if os.name != 'nt':
            _fail('CORPUS_STORAGE_WINDOWS_REQUIRED')
        handles, identities, store = [], [], None
        try:
            sid = roots._current_principal()
            if win32file.GetDriveType(drive) != 3:
                _fail('CORPUS_STORAGE_FIXED_VOLUME_REQUIRED')
            handle = win32file.CreateFile('\\\\?\\' + drive, 0x120081, 3, None, 3,
                                          0x02000000 | 0x00200000, None)
            handles.append(handle)
            volume, identity = roots._details(handle)
            identities.append(identity)
            _check_ancestors([handle], sid)
            for part in parts[:-1]:
                handle = roots._child(handle, part)
                handles.append(handle)
                actual_volume, identity = roots._details(handle)
                if actual_volume != volume:
                    _fail('CORPUS_STORAGE_VOLUME_CHANGED')
                identities.append(identity)
                _check_ancestors([handle], sid)
            # Recheck the full retained chain before the only filesystem creation.
            _check_ancestors(handles, sid)
            store = blobs.ImmutableCorpusBlobs.create(path)
            if store._root._identities[:-1] != identities or store._root.broker_sid != sid:
                _fail('CORPUS_STORAGE_IDENTITY_CHANGED')
            lease = object.__new__(cls)
            lease._store = store
            lease._lock = threading.RLock()
            lease._closed = False
            lease._tainted = False
            lease._check()
            return lease
        except BaseException as exc:
            if store is not None:
                store.close()
            if not isinstance(exc, Exception) or isinstance(exc, CorpusBoundaryError):
                raise
            _fail('CORPUS_ANCESTOR_NATIVE_UNAVAILABLE')
        finally:
            for handle in reversed(handles):
                handle.Close()

    def _check(self):
        root = self._store._root
        if roots._current_principal() != root.broker_sid:
            _fail('CORPUS_STORAGE_CALLER_CHANGED')
        _check_ancestors(root._handles[:-1], root.broker_sid)
        root.verify()

    def _operation(self, call):
        with self._lock:
            if self._closed:
                _fail('CORPUS_ANCESTOR_CLOSED')
            if self._tainted:
                _fail('CORPUS_ANCESTOR_TAINTED')
            try:
                self._check()
                result = call()
                self._check()
                return result
            except BaseException as exc:
                self._tainted = True
                if not isinstance(exc, Exception) or isinstance(exc, CorpusBoundaryError):
                    raise
                _fail('CORPUS_ANCESTOR_NATIVE_UNAVAILABLE')

    def put(self, data):
        return self._operation(lambda: self._store.put(data))

    def read(self, digest):
        return self._operation(lambda: self._store.read(digest))

    def verify(self):
        self._operation(self._store.verify)

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._store.close()

    def __enter__(self):
        self.verify()
        return self

    def __exit__(self, *_):
        self.close()
