"""Protected Windows root/file leases, not an account or storage factory.

Reuses the frozen corpus-root handle walk and exact directory ACL policy.
Directories require the measured current-SID owner. Files allow current SID or
BUILTIN Administrators ownership (the measured elevated creator default), with
the same exact three full-access trustees; validation never repairs a DACL.
Current user, SYSTEM and Administrators remain trusted; ancestor ACL admission,
hostile same-user isolation, account identity and SQLite durability are NOT proved.
Closing retains every file. No ACL repair or existing-directory adoption occurs.
"""
import ctypes
import os
from pathlib import Path
import re
import struct
import tempfile
import threading

from . import theatrical_storage_roots as native
from .theatrical_corpus_boundary import CorpusBoundaryError


class TrialRootError(ValueError):
    """Sanitized root admission failure; never includes private path contents."""


def _fail(code):
    raise TrialRootError(code) from None


def _name(value):
    if (type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,95}',value)
            or value.endswith('.') or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])',value.split('.')[0],re.I)):
        _fail('TRIAL_ROOT_SIMPLE_NAME_REQUIRED')
    return value


def _path(value):
    if os.name != 'nt':
        _fail('TRIAL_ROOT_WINDOWS_REQUIRED')
    try:
        path=Path(value)
        if not path.is_absolute():
            _fail('TRIAL_ROOT_ABSOLUTE_PATH_REQUIRED')
        # Preserve original components for the no-reparse handle walk.
        native._parts(str(path))
        temp=Path(tempfile.gettempdir()).absolute()
        if path.is_relative_to(temp) or path.resolve(strict=False).is_relative_to(temp.resolve()):
            _fail('TRIAL_ROOT_OS_TEMP_REFUSED')
        return path
    except TrialRootError:
        raise
    except Exception:
        _fail('TRIAL_ROOT_PATH_REFUSED')


def _identity(value):
    if (type(value) is not list or len(value)!=2
            or any(type(n) is not int or n<0 for n in value)
            or value[0]>0xffffffff or value[1]>0xffffffffffffffff):
        _fail('TRIAL_ROOT_EXPLICIT_IDENTITY_REQUIRED')
    return value


def _file_info(handle, *, directory=False):
    info=native.win32file.GetFileInformationByHandle(handle)
    if bool(info[0]&0x10)!=directory or info[0]&0x400 or (not directory and info[7]!=1):
        _fail('TRIAL_ROOT_FILE_TYPE_REPARSE_OR_LINK_REFUSED')
    return [info[4],(info[8]<<32)|info[9]]


def _streams(handle):
    """Handle-based bounded NTFS stream inventory; no alternate data streams."""
    kernel=native._kernel
    function=kernel.GetFileInformationByHandleEx
    function.argtypes=[native.wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,native.wintypes.DWORD]
    function.restype=native.wintypes.BOOL
    buffer=ctypes.create_string_buffer(65536)
    if not function(int(handle),7,buffer,len(buffer)):  # FileStreamInfo
        if ctypes.get_last_error()==38:  # directory without a stream
            return
        _fail('TRIAL_ROOT_STREAM_INVENTORY_UNAVAILABLE')
    offset=0
    for _ in range(256):
        if offset+24>len(buffer):
            _fail('TRIAL_ROOT_STREAM_INVENTORY_INVALID')
        next_offset,length,_,_=struct.unpack_from('<IIqq',buffer.raw,offset)
        if length%2 or offset+24+length>len(buffer):
            _fail('TRIAL_ROOT_STREAM_INVENTORY_INVALID')
        stream=buffer.raw[offset+24:offset+24+length].decode('utf-16-le')
        if stream!='::$DATA':
            _fail('TRIAL_ROOT_ALTERNATE_STREAM_REFUSED')
        if next_offset==0:
            return
        if next_offset<24 or offset+next_offset>=len(buffer):
            _fail('TRIAL_ROOT_STREAM_INVENTORY_INVALID')
        offset+=next_offset
    _fail('TRIAL_ROOT_STREAM_INVENTORY_BOUND_EXCEEDED')


def _file_acl(handle,sid):
    sd=native.win32security.GetSecurityInfo(handle,native.win32security.SE_FILE_OBJECT,
        native.win32security.OWNER_SECURITY_INFORMATION|native.win32security.DACL_SECURITY_INFORMATION)
    owner=native.win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner())
    acl=sd.GetSecurityDescriptorDacl()
    expected={sid,'S-1-5-18','S-1-5-32-544'}
    if owner not in (sid,'S-1-5-32-544') or acl is None or acl.GetAceCount()!=3:
        _fail('TRIAL_ROOT_FILE_ACL_REFUSED')
    seen=set()
    for index in range(acl.GetAceCount()):
        ace=acl.GetAce(index)
        trustee=native.win32security.ConvertSidToStringSid(ace[2])
        # Exact full-access trustee set; ordinary inherited file ACEs carry ID.
        if (len(ace)!=3 or ace[0][0]!=0 or ace[0][1] not in (0,0x10)
                or ace[1]!=0x1f01ff or trustee in seen):
            _fail('TRIAL_ROOT_FILE_ACL_REFUSED')
        seen.add(trustee)
    if seen!=expected:
        _fail('TRIAL_ROOT_FILE_ACL_REFUSED')


def _open_file(root_handle,name,*,missing=False):
    buffer=ctypes.create_unicode_buffer(name)
    string=native._UnicodeString(len(name)*2,(len(name)+1)*2,ctypes.cast(buffer,ctypes.c_void_p))
    attrs=native._ObjectAttributes(ctypes.sizeof(native._ObjectAttributes),int(root_handle),
        ctypes.pointer(string),0x40|0x1000,None,None)
    io,raw=native._IOStatus(),native.wintypes.HANDLE()
    status=native._nt.NtCreateFile(ctypes.byref(raw),0x120081,ctypes.byref(attrs),ctypes.byref(io),
        None,0,3,1,0x200000|0x20|0x40,None,0)
    if status<0:
        if missing and status&0xffffffff in (0xc0000034,0xc000003a):
            return None
        _fail('TRIAL_ROOT_FILE_OPEN_REFUSED')
    return native.pywintypes.HANDLE(raw.value)


class TrialRootLease:
    """Held directory chain plus optional file pins; no creation/recovery of a DB."""
    def __init__(self):
        _fail('TRIAL_ROOT_FACTORY_REQUIRED')

    @classmethod
    def _wrap(cls,root,path):
        value=object.__new__(cls)
        value._root=root;value._path=path;value._lock=threading.RLock();value._pins={};value._closed=False
        value._identity=_file_info(root._handles[-1],directory=True)
        value.validate()
        return value

    @classmethod
    def create(cls,parent_path,name):
        name=_name(name);path=_path(Path(parent_path)/name)
        root=None
        try:
            root=native.ProtectedCorpusRoot.create(str(path))
            return cls._wrap(root,path)
        except Exception as error:
            if root is not None:root.close()
            if isinstance(error,TrialRootError):raise
            _fail('TRIAL_ROOT_CREATE_REFUSED')

    @classmethod
    def open(cls,path,*,expected_identity):
        return cls._open(path,expected_identity=expected_identity,locator_bootstrap=False)

    @classmethod
    def open_for_locator(cls,path):
        """Hold a private root before reading its locator, without identity trust.

        This measures the directory identity but does NOT bind an expected store.
        Caller must pin/read the private locator and compare its root identity,
        external expected store UUID/account and database binding separately.
        """
        return cls._open(path,expected_identity=None,locator_bootstrap=True)

    @classmethod
    def _open(cls,path,*,expected_identity,locator_bootstrap):
        path=_path(path)
        if not locator_bootstrap:expected_identity=_identity(expected_identity)
        # Initialize the frozen lease's existing verify/close mechanism with a
        # handle-relative OPEN chain; no directory creation or DACL mutation.
        root=object.__new__(native.ProtectedCorpusRoot)
        root._handles=[];root._identities=[];root._lock=threading.RLock()
        root._path=str(path);root._closed=False
        try:
            root._sid=native._current_principal()
            drive,parts=native._parts(str(path))
            if native.win32file.GetDriveType(drive)!=3:
                _fail('TRIAL_ROOT_FIXED_NTFS_REQUIRED')
            handle=native.win32file.CreateFile('\\\\?\\'+drive,0x120081,3,None,3,0x02000000|0x00200000,None)
            root._handles.append(handle);volume,identity=native._details(handle);root._identities.append(identity)
            fs=ctypes.create_unicode_buffer(32);serial=native.wintypes.DWORD();maximum=native.wintypes.DWORD();flags=native.wintypes.DWORD()
            if (not native._kernel.GetVolumeInformationByHandleW(int(handle),None,0,ctypes.byref(serial),
                    ctypes.byref(maximum),ctypes.byref(flags),fs,len(fs)) or fs.value!='NTFS'):
                _fail('TRIAL_ROOT_FIXED_NTFS_REQUIRED')
            for part in parts:
                handle=native._child(handle,part);root._handles.append(handle)
                actual,identity=native._details(handle);root._identities.append(identity)
                if actual!=volume:_fail('TRIAL_ROOT_VOLUME_CHANGED')
            root._identity=identity;root.verify()
            if not locator_bootstrap and _file_info(handle,directory=True)!=expected_identity:
                _fail('TRIAL_ROOT_IDENTITY_CHANGED')
            return cls._wrap(root,path)
        except Exception as error:
            root.close()
            if isinstance(error,TrialRootError):raise
            _fail('TRIAL_ROOT_REOPEN_REFUSED')

    @property
    def path(self):return self._path

    @property
    def identity(self):return list(self._identity)

    @property
    def broker_sid(self):return self._root.broker_sid

    def _check_file(self,handle):
        identity=_file_info(handle);_file_acl(handle,self.broker_sid);_streams(handle)
        return identity

    def validate(self):
        with self._lock:
            if self._closed:_fail('TRIAL_ROOT_CLOSED')
            try:
                self._root.verify()
                if _file_info(self._root._handles[-1],directory=True)!=self._identity:
                    _fail('TRIAL_ROOT_IDENTITY_CHANGED')
                _streams(self._root._handles[-1])
                for handle,identity in self._pins.values():
                    if self._check_file(handle)!=identity:_fail('TRIAL_ROOT_FILE_IDENTITY_CHANGED')
            except TrialRootError:raise
            except Exception:_fail('TRIAL_ROOT_VALIDATION_REFUSED')

    def pin_file(self,name):
        name=_name(name)
        with self._lock:
            self.validate()
            if name in self._pins:return list(self._pins[name][1])
            handle=None
            try:
                handle=_open_file(self._root._handles[-1],name)
                identity=self._check_file(handle);self._pins[name]=(handle,identity)
                return list(identity)
            except Exception as error:
                if handle is not None:handle.Close()
                if isinstance(error,TrialRootError):raise
                _fail('TRIAL_ROOT_FILE_PIN_REFUSED')

    def validate_file(self,name,expected_identity,exists=True):
        name=_name(name)
        if type(exists) is not bool:_fail('TRIAL_ROOT_EXPLICIT_FILE_STATE_REQUIRED')
        if exists:_identity(expected_identity)
        elif expected_identity is not None:_fail('TRIAL_ROOT_ABSENT_FILE_HAS_IDENTITY')
        with self._lock:
            self.validate();handle=None
            try:
                handle=_open_file(self._root._handles[-1],name,missing=not exists)
                if not exists:
                    if handle is not None:_fail('TRIAL_ROOT_EXPECTED_ABSENT_FILE_EXISTS')
                    return
                if self._check_file(handle)!=expected_identity:_fail('TRIAL_ROOT_FILE_IDENTITY_CHANGED')
            except TrialRootError:raise
            except Exception:_fail('TRIAL_ROOT_FILE_VALIDATION_REFUSED')
            finally:
                if handle is not None:handle.Close()

    def close(self):
        with self._lock:
            if self._closed:return
            self._closed=True
            for handle,_ in self._pins.values():handle.Close()
            self._pins.clear();self._root.close()

    def __enter__(self):self.validate();return self

    def __exit__(self,*_):self.close()
