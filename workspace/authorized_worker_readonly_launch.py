"""Bounded delegation to the operator-authenticated standard worker, not an API executor.

Only the fixed read-only inspection script is admitted. No passwords, token
serialization, group/policy changes, elevated worker or VM execution is involved.
"""
from pathlib import Path
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes as W
import hashlib
import json
import os
import subprocess
import psutil

ROOT=Path(r'C:\AI-BS')
SID='S-1-5-21-2133766663-4066672948-2456486318-1005'
SOURCE_PID=291912
SOURCE_CREATED=1792856848.810399
EXE=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
SCRIPT=str(ROOT/'isolated_workers/windows/control/Read-CurrentVMState.ps1')
SCRIPT_SHA='4e89b6e16f656ac82b975e14c12c5490fc5ded7603ec1d033f4d4cb77935e3c4'
SOURCE_ARGV=['powershell.exe','-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-File',SCRIPT]

def validate_source(info):
    valid=(type(info) is dict and info.get('pid')==SOURCE_PID and info.get('created')==SOURCE_CREATED
           and info.get('sid')==SID and info.get('elevated') is False and info.get('integrity')==8192
           and os.path.normcase(info.get('exe',''))==os.path.normcase(EXE)
           and info.get('argv')==SOURCE_ARGV)
    if not valid:raise ValueError('Only the verified authenticated nonadmin worker source is admitted')

class Startup(ctypes.Structure):
    _fields_=[('cb',W.DWORD),('lpReserved',W.LPWSTR),('lpDesktop',W.LPWSTR),('lpTitle',W.LPWSTR),
              ('dwX',W.DWORD),('dwY',W.DWORD),('dwXSize',W.DWORD),('dwYSize',W.DWORD),
              ('dwXCountChars',W.DWORD),('dwYCountChars',W.DWORD),('dwFillAttribute',W.DWORD),
              ('dwFlags',W.DWORD),('wShowWindow',W.WORD),('cbReserved2',W.WORD),
              ('lpReserved2',ctypes.POINTER(W.BYTE)),('hStdInput',W.HANDLE),('hStdOutput',W.HANDLE),('hStdError',W.HANDLE)]

class ProcessInfo(ctypes.Structure):
    _fields_=[('hProcess',W.HANDLE),('hThread',W.HANDLE),('dwProcessId',W.DWORD),('dwThreadId',W.DWORD)]

def main():
    out=ROOT/'snapshots'/('authorized_worker_readonly_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir()
    record={'status':'preflight','at_utc':datetime.now(timezone.utc).isoformat(),'fixed_script':SCRIPT,
            'password_used_or_stored':False,'privilege_or_account_policy_changed':False,'guest_started':False}
    handles=[]; envptr=W.LPVOID(); child_resumed=False; pi=ProcessInfo()
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    a=ctypes.WinDLL('advapi32',use_last_error=True)
    u=ctypes.WinDLL('userenv',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
    k.LocalFree.argtypes=[W.LPVOID];k.LocalFree.restype=W.LPVOID
    a.OpenProcessToken.argtypes=[W.HANDLE,W.DWORD,ctypes.POINTER(W.HANDLE)];a.OpenProcessToken.restype=W.BOOL
    a.GetTokenInformation.argtypes=[W.HANDLE,ctypes.c_int,W.LPVOID,W.DWORD,ctypes.POINTER(W.DWORD)];a.GetTokenInformation.restype=W.BOOL
    a.ConvertSidToStringSidW.argtypes=[W.LPVOID,ctypes.POINTER(W.LPWSTR)];a.ConvertSidToStringSidW.restype=W.BOOL
    a.GetSidSubAuthorityCount.argtypes=[W.LPVOID];a.GetSidSubAuthorityCount.restype=ctypes.POINTER(W.BYTE)
    a.GetSidSubAuthority.argtypes=[W.LPVOID,W.DWORD];a.GetSidSubAuthority.restype=ctypes.POINTER(W.DWORD)
    a.DuplicateTokenEx.argtypes=[W.HANDLE,W.DWORD,W.LPVOID,ctypes.c_int,ctypes.c_int,ctypes.POINTER(W.HANDLE)];a.DuplicateTokenEx.restype=W.BOOL
    u.CreateEnvironmentBlock.argtypes=[ctypes.POINTER(W.LPVOID),W.HANDLE,W.BOOL];u.CreateEnvironmentBlock.restype=W.BOOL
    u.DestroyEnvironmentBlock.argtypes=[W.LPVOID];u.DestroyEnvironmentBlock.restype=W.BOOL
    a.CreateProcessWithTokenW.argtypes=[W.HANDLE,W.DWORD,W.LPCWSTR,W.LPWSTR,W.DWORD,W.LPVOID,W.LPCWSTR,ctypes.POINTER(Startup),ctypes.POINTER(ProcessInfo)];a.CreateProcessWithTokenW.restype=W.BOOL
    k.ResumeThread.argtypes=[W.HANDLE];k.ResumeThread.restype=W.DWORD
    k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD
    k.GetExitCodeProcess.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)];k.GetExitCodeProcess.restype=W.BOOL
    k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.TerminateProcess.restype=W.BOOL

    def required(result):
        if not result:raise ctypes.WinError(ctypes.get_last_error())
        return result

    def token_metadata(token):
        def get(kind):
            size=W.DWORD()
            a.GetTokenInformation(token,kind,None,0,ctypes.byref(size))
            buf=ctypes.create_string_buffer(size.value)
            required(a.GetTokenInformation(token,kind,buf,len(buf),ctypes.byref(size)))
            return buf
        raw=get(1); sidptr=ctypes.cast(raw,ctypes.POINTER(W.LPVOID)).contents.value
        text=W.LPWSTR();required(a.ConvertSidToStringSidW(sidptr,ctypes.byref(text)))
        try:sid=text.value
        finally:k.LocalFree(ctypes.cast(text,W.LPVOID))
        elevated=bool(ctypes.cast(get(20),ctypes.POINTER(W.DWORD)).contents.value)
        integrity_raw=get(25); iptr=ctypes.cast(integrity_raw,ctypes.POINTER(W.LPVOID)).contents.value
        count=a.GetSidSubAuthorityCount(iptr).contents.value
        integrity=a.GetSidSubAuthority(iptr,count-1).contents.value
        return {'sid':sid,'elevated':elevated,'integrity':integrity}

    try:
        source=psutil.Process(SOURCE_PID)
        source_info={'pid':source.pid,'created':source.create_time(),'exe':source.exe(),'argv':source.cmdline()}
        source_handle=required(k.OpenProcess(0x1000,False,SOURCE_PID));handles.append(source_handle)
        token=W.HANDLE();required(a.OpenProcessToken(source_handle,0x000A,ctypes.byref(token)));handles.append(token)
        source_info.update(token_metadata(token));validate_source(source_info)
        record['source']=source_info
        assert hashlib.sha256(Path(SCRIPT).read_bytes()).hexdigest()==SCRIPT_SHA
        for p in (Path(SCRIPT),*Path(SCRIPT).parents):assert not p.is_symlink() and not p.is_junction()
        primary=W.HANDLE();required(a.DuplicateTokenEx(token,0x000B,None,2,1,ctypes.byref(primary)));handles.append(primary)
        required(u.CreateEnvironmentBlock(ctypes.byref(envptr),primary,False))
        environment={};offset=0
        allowed={'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TEMP','TMP','USERPROFILE','USERNAME','USERDOMAIN','APPDATA','LOCALAPPDATA','PROGRAMDATA','PROGRAMFILES','PROGRAMFILES(X86)'}
        while True:
            value=ctypes.wstring_at(envptr.value+offset)
            if not value:break
            offset+=(len(value)+1)*ctypes.sizeof(ctypes.c_wchar)
            key,_,v=value.partition('=')
            if key.upper() in allowed:environment[key]=v
        for key in ['AI_BS_RECDEBUT_OUTBOUND_ENABLED','AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED','AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED','AI_BS_ALLOW_DESTRUCTIVE_ACTIONS']:environment[key]='false'
        block=ctypes.create_unicode_buffer('\0'.join(k+'='+v for k,v in sorted(environment.items(),key=lambda x:x[0].casefold()))+'\0\0')
        argv=[EXE,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',SCRIPT]
        command=ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        assert len(command.value)<1024 and source.create_time()==SOURCE_CREATED
        startup=Startup();startup.cb=ctypes.sizeof(startup);startup.lpDesktop='winsta0\\default';startup.dwFlags=1;startup.wShowWindow=0
        required(a.CreateProcessWithTokenW(primary,1,EXE,command,0x08000404,ctypes.cast(block,W.LPVOID),str(Path(SCRIPT).parent),ctypes.byref(startup),ctypes.byref(pi)))
        handles.extend([pi.hThread,pi.hProcess])
        child_token=W.HANDLE();required(a.OpenProcessToken(pi.hProcess,0x0008,ctypes.byref(child_token)));handles.append(child_token)
        metadata=token_metadata(child_token)
        assert metadata=={'sid':SID,'elevated':False,'integrity':8192}, 'Suspended child identity differs; no code may run'
        child=psutil.Process(pi.dwProcessId)
        record.update(status='verified_suspended_child',child={'pid':child.pid,'created':child.create_time(),'exe':child.exe(),**metadata})
        assert os.path.normcase(child.exe())==os.path.normcase(EXE)
        (out/'before_resume.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        if k.ResumeThread(pi.hThread)==0xFFFFFFFF:raise ctypes.WinError(ctypes.get_last_error())
        child_resumed=True
        result=k.WaitForSingleObject(pi.hProcess,45000)
        if result==258:
            record.update(status='still_running_after_observation',process_handle_terminal=False)
        else:
            assert result==0
            code=W.DWORD();required(k.GetExitCodeProcess(pi.hProcess,ctypes.byref(code)))
            record.update(status='completed' if code.value==0 else 'failed',returncode=code.value,process_handle_terminal=True)
    except BaseException as error:
        record.update(status='failed',error_type=type(error).__name__,error_code=getattr(error,'winerror',None),
                      reason=str(error) if isinstance(error,(AssertionError,ValueError)) else 'Inspect local native process evidence; no fallback attempted')
        if pi.hProcess and not child_resumed:k.TerminateProcess(pi.hProcess,1)
        raise
    finally:
        if envptr:u.DestroyEnvironmentBlock(envptr)
        for h in reversed(handles):k.CloseHandle(h)
        (out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps({'status':record['status'],'evidence':str(out/'result.json'),'returncode':record.get('returncode'),'error_code':record.get('error_code')}),flush=True)
    return 0 if record['status']=='completed' else 1

if __name__=='__main__':raise SystemExit(main())
