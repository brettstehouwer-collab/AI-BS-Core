"""Current-user/SYSTEM-only broadcast IPC. Import performs no OS or file I/O."""
from __future__ import annotations
import json
import os
from pathlib import Path
import uuid
import time

_FULL = 0x1f01ff
_PROTECTED = 0x1000


def private_profile_root():
    from win32com.shell import shell, shellcon
    profile = Path(shell.SHGetFolderPath(0,shellcon.CSIDL_PROFILE,0,0))
    if not profile.is_absolute(): raise ValueError('IPC_LOCATION_UNAVAILABLE')
    # LocalAppData is virtualized by packaged hosts such as Codex. Profile
    # storage is shared physically with an ordinary Windows desktop launch.
    return profile/'.aibs-private'


def ipc_paths():
    root = private_profile_root()/'BroadcastIPC'
    return {'status':root/'broadcast_secondary_status.json',
            'command':root/'broadcast_secondary_command.json',
            'stop':root/'broadcast_secondary.stop'}


def _identities():
    import win32api,win32con,win32security
    token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
    try: current=win32security.GetTokenInformation(token,win32security.TokenUser)[0]
    finally: token.Close()
    system=win32security.CreateWellKnownSid(win32security.WinLocalSystemSid,None)
    return current,system


def _validate_descriptor(sd,current,system,*,sid_text=None):
    if sid_text is None:
        import win32security
        sid_text=win32security.ConvertSidToStringSid
    if sid_text(sd.GetSecurityDescriptorOwner()) != sid_text(current): raise ValueError('IPC_OWNER_MISMATCH')
    if not sd.GetSecurityDescriptorControl()[0] & _PROTECTED: raise ValueError('IPC_ACL_NOT_PROTECTED')
    acl=sd.GetSecurityDescriptorDacl(); expected={sid_text(current),sid_text(system)}; found=set()
    if acl is None or acl.GetAceCount()!=len(expected): raise ValueError('IPC_ACL_UNSAFE')
    for index in range(acl.GetAceCount()):
        ace=acl.GetAce(index)
        if len(ace)!=3 or ace[0][0]!=0 or ace[0][1] not in (0,3) or ace[1]!=_FULL:
            raise ValueError('IPC_ACL_UNSAFE')
        identity=sid_text(ace[2])
        if identity not in expected or identity in found: raise ValueError('IPC_ACL_UNSAFE')
        found.add(identity)
    if found!=expected: raise ValueError('IPC_ACL_UNSAFE')


def _not_redirected(path):
    if any(part.is_symlink() or part.is_junction() for part in (path,*path.parents)):
        raise ValueError('IPC_STORAGE_REDIRECTED')


def _descriptor(path):
    import win32security
    return win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION)


def _security_attributes(directory):
    import pywintypes,win32security
    current,system=_identities();acl=win32security.ACL()
    identities=[current] if current==system else [current,system]
    for identity in identities: acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,3 if directory else 0,_FULL,identity)
    sd=win32security.SECURITY_DESCRIPTOR();sd.SetSecurityDescriptorOwner(current,False)
    sd.SetSecurityDescriptorDacl(1,acl,0);sd.SetSecurityDescriptorControl(_PROTECTED,_PROTECTED)
    attributes=pywintypes.SECURITY_ATTRIBUTES();attributes.SECURITY_DESCRIPTOR=sd
    return attributes,acl,current


def _secure_directory(path):
    import win32file,win32security
    _not_redirected(path)
    attributes,acl,current=_security_attributes(True)
    if not path.exists():
        win32file.CreateDirectory(str(path),attributes)
    else:
        if not path.is_dir(): raise ValueError('IPC_DIRECTORY_UNAVAILABLE')
        if _descriptor(path).GetSecurityDescriptorOwner()!=current: raise ValueError('IPC_OWNER_MISMATCH')
        # Explicit initialization may secure an existing current-user-owned
        # directory. Reads never change ACLs or take over a foreign directory.
        win32security.SetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION|win32security.PROTECTED_DACL_SECURITY_INFORMATION,
            None,None,acl,None)
    _validate_descriptor(_descriptor(path),*_identities())


def ensure_private_ipc():
    paths=ipc_paths();root=paths['status'].parent
    _secure_directory(root.parent);_secure_directory(root)
    for path in paths.values(): validate_private_path(path,allow_missing=True)
    return paths


def validate_private_path(path,allow_missing=True):
    path=Path(path);root=ipc_paths()['status'].parent
    if path not in (root,root.parent) and path.parent!=root: raise ValueError('IPC_PATH_UNEXPECTED')
    _not_redirected(path)
    for directory in (root.parent,root):
        if directory.exists():
            if not directory.is_dir(): raise ValueError('IPC_DIRECTORY_UNAVAILABLE')
            _validate_descriptor(_descriptor(directory),*_identities())
        elif not allow_missing: raise FileNotFoundError(str(directory))
    if path.exists():
        _validate_descriptor(_descriptor(path),*_identities())
    elif not allow_missing: raise FileNotFoundError(str(path))


def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('IPC_DUPLICATE_PROPERTY')
        result[key]=value
    return result


def _decode_json(raw,max_bytes):
    if len(raw)>max_bytes: raise ValueError('IPC_TOO_LARGE')
    try:
        value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError): raise ValueError('IPC_JSON_INVALID') from None
    if type(value) is not dict: raise ValueError('IPC_JSON_INVALID')
    return value


def read_shared_bytes(path,max_bytes=65536):
    """Bounded read that permits a producer's atomic replacement on Windows.

    Callers enforce their own path/ACL policy before this generic file reader.
    An opened handle continues reading its original file after replacement.
    """
    if type(max_bytes) is not int or not 1<=max_bytes<=65536: raise ValueError('IPC_LIMIT_INVALID')
    import win32file,win32con,pywintypes
    try:
        handle=win32file.CreateFile(str(path),win32con.GENERIC_READ,
            win32con.FILE_SHARE_READ|win32con.FILE_SHARE_WRITE|win32con.FILE_SHARE_DELETE,
            None,win32con.OPEN_EXISTING,win32con.FILE_ATTRIBUTE_NORMAL,None)
        try:
            status,raw=win32file.ReadFile(handle,max_bytes+1)
            if status!=0: raise OSError('IPC_READ_UNAVAILABLE')
            if len(raw)>max_bytes: raise ValueError('IPC_TOO_LARGE')
            return raw
        finally:handle.Close()
    except pywintypes.error as error:
        translated=OSError('SHARED_READ_UNAVAILABLE');translated.winerror=error.winerror
        raise translated from None


def _replace_shared(source,target):
    # Windows readers outside our control may briefly deny rename/delete.
    # Limit both attempts and the total planned delay; permanent errors fail.
    deadline=time.monotonic()+.2
    delays=(.005,.01,.02,.03,.04)
    for attempt in range(len(delays)+1):
        try:return os.replace(source,target)
        except OSError as error:
            if (getattr(error,'winerror',None) not in (5,32,33) or attempt>=len(delays)
                    or time.monotonic()+delays[attempt]>deadline):raise
            time.sleep(delays[attempt])


def read_private_json(path,max_bytes=16384):
    if type(max_bytes) is not int or not 1<=max_bytes<=16384: raise ValueError('IPC_LIMIT_INVALID')
    path=Path(path);validate_private_path(path,allow_missing=False)
    raw=read_shared_bytes(path,max_bytes)
    return _decode_json(raw,max_bytes)


def write_private_json(path,data,max_bytes=16384):
    if type(data) is not dict or type(max_bytes) is not int or not 1<=max_bytes<=16384: raise ValueError('IPC_JSON_INVALID')
    raw=json.dumps(data,allow_nan=False,separators=(',',':')).encode('utf-8')
    if len(raw)>max_bytes: raise ValueError('IPC_TOO_LARGE')
    path=Path(path);paths=ensure_private_ipc()
    if path not in paths.values(): raise ValueError('IPC_PATH_UNEXPECTED')
    validate_private_path(path,allow_missing=True)
    import win32file,win32con
    temporary=path.parent/('.broadcast-'+uuid.uuid4().hex+'.tmp')
    attributes,_,_=_security_attributes(False)
    try:
        handle=win32file.CreateFile(str(temporary),win32con.GENERIC_WRITE,0,attributes,
                                   win32con.CREATE_NEW,win32con.FILE_ATTRIBUTE_NORMAL,None)
        try:
            validate_private_path(temporary,allow_missing=False)
            result=win32file.WriteFile(handle,raw)
            if result!=(0,len(raw)): raise ValueError('IPC_WRITE_INCOMPLETE')
            win32file.FlushFileBuffers(handle)
        finally: handle.Close()
        validate_private_path(path,allow_missing=True)
        _replace_shared(temporary,path)
        validate_private_path(path,allow_missing=False)
    finally: temporary.unlink(missing_ok=True)
