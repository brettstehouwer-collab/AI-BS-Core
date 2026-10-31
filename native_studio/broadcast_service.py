"""Legacy local control-service management and shared safe child environment.

Importing this module does no I/O. Service readiness proves a matching local
control endpoint, never a running encoder, accepted ingest, or finalized file.
Native broadcast actions use broadcast_secondary_control; they do not invoke
this legacy 8005 startup path. Importing this module starts neither service.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import subprocess
import time
import urllib.request

import psutil

ROOT=Path(r'C:\AI-BS')
PYTHON=ROOT/'pyppeteer_env/Scripts/python.exe'
BACKEND=ROOT/'backend'
DAEMON=BACKEND/'aibs_broadcast_daemon.py'
LOG_FILE=ROOT/'logs/broadcast_8005_service.log'
SERVICE_ID='ai-bs.broadcast-daemon'


def service_command() -> list[str]:
    return [str(PYTHON),'-B','-m','uvicorn','aibs_broadcast_daemon:app',
            '--app-dir',str(BACKEND),'--host','127.0.0.1','--port','8005',
            '--workers','1','--no-access-log']


def service_environment() -> dict[str,str]:
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','TEMP','TMP',
             'USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMDATA','PROGRAMFILES',
             'PROGRAMFILES(X86)','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}
    env={key:value for key,value in os.environ.items() if key.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',DRY_RUN='true',HOLD_DISPATCH='true',
               LIVE_TRADING_ENABLED='false',AIBS_PAYMENT_MODE='disabled')
    for key in ['AI_BS_BACKEND_MANAGE_DAEMONS','AI_BS_BACKEND_BACKGROUND_ENABLED',
                'AI_BS_NATIVE_MANAGE_DAEMONS','AI_BS_NATIVE_EXIT_PROCESS_CLEANUP',
                'AI_BS_NATIVE_BACKGROUND_UPDATES','AI_BS_RECDEBUT_OUTBOUND_ENABLED',
                'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED','AI_BS_DISCORD_NOTIFICATIONS_ENABLED',
                'RECDEBUT_SENDING_ENABLED','RECDEBUT_REPLY_FORWARDING_ENABLED']:
        env[key]='false'
    return env


def _error(code: str) -> dict:
    return {'status':'error','code':code,'started':False}


def _normalized_path(value: str) -> str:
    return os.path.normcase(os.path.abspath(value))


def _declared_base_python() -> str | None:
    """Trust only the base executable declared by this fixed virtual environment."""
    try:
        with (PYTHON.parent.parent/'pyvenv.cfg').open(encoding='utf-8') as config:
            text=config.read(8193)
        if len(text)>8192:
            return None
        fields=dict(line.split(' = ',1) for line in text.splitlines() if ' = ' in line)
        home=Path(fields['home'])
        declared=Path(fields['executable'])
        if (not home.is_absolute() or not declared.is_absolute()
                or declared.name.lower()!='python.exe'
                or _normalized_path(str(declared.parent))!=_normalized_path(str(home))
                or not declared.is_file()):
            return None
        return _normalized_path(str(declared))
    except (OSError,ValueError,KeyError):
        return None


def _fixed_command(process, expected, executable) -> bool:
    command=process.cmdline()
    return (len(command)==len(expected) and command[1:]==expected[1:]
            and _normalized_path(command[0])==executable
            and _normalized_path(process.exe())==executable)


def _listener_owner() -> dict:
    try:
        listeners=[entry for entry in psutil.net_connections(kind='tcp')
                   if entry.status==psutil.CONN_LISTEN and entry.laddr.port==8005]
        if not listeners:
            return {'status':'offline'}
        pids={entry.pid for entry in listeners}
        if (len(pids)!=1 or any(entry.laddr.ip!='127.0.0.1' for entry in listeners)
                or type(next(iter(pids))) is not int):
            return _error('PORT_CONFLICT')
        pid=next(iter(pids))
        process=psutil.Process(pid)
        expected=service_command()
        fixed_python=_normalized_path(str(PYTHON))
        if _fixed_command(process,expected,fixed_python):
            return {'status':'owned','pid':pid}
        # Windows virtual environments run a redirector executable which owns a
        # base-Python child. Admit that exact child only through its still-live,
        # fixed-venv parent with identical approved arguments.
        base_python=_declared_base_python()
        if base_python is not None and _fixed_command(process,expected,base_python):
            parent_pid=process.ppid()
            if type(parent_pid) is int and parent_pid!=pid:
                parent=psutil.Process(parent_pid)
                if _fixed_command(parent,expected,fixed_python):
                    return {'status':'owned','pid':pid,'launcher_pid':parent_pid}
        return _error('PORT_CONFLICT')
    except (OSError,psutil.Error,ValueError,TypeError):
        return _error('OWNER_UNVERIFIED')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def _read_health() -> dict:
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    with opener.open('http://127.0.0.1:8005/health',timeout=0.75) as response:
        if response.status!=200:
            raise ValueError('Control service health unavailable')
        raw=response.read(8193)
    if len(raw)>8192:
        raise ValueError('Control service health oversized')
    data=json.loads(raw)
    if type(data) is not dict:
        raise ValueError('Control service health invalid')
    return data


def probe_broadcast_service() -> dict:
    owner=_listener_owner()
    if owner['status']!='owned':
        return owner
    try:
        health=_read_health()
        if (health.get('service_id')!=SERVICE_ID
                or type(health.get('protocol_version')) is not int or health['protocol_version']!=1
                or type(health.get('pid')) is not int or health['pid']!=owner['pid']):
            return _error('PORT_CONFLICT')
        return {**owner,'status':'ready','started':False,
                'verification_scope':'local_control_service_only'}
    except (OSError,ValueError,TypeError):
        return _error('HEALTH_UNVERIFIED')


@contextmanager
def _startup_lock():
    """Serialize independent native clients through a bounded Windows mutex."""
    if os.name!='nt':
        raise OSError('Windows service control unavailable')
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.ReleaseMutex.argtypes=[wintypes.HANDLE]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,r'Local\AI_BS_Broadcast8005_Startup')
    if not handle:
        raise OSError('Service startup lock unavailable')
    acquired=False
    try:
        acquired=kernel.WaitForSingleObject(handle,2500) in (0,0x80)
        if not acquired:
            raise OSError('Another client is starting the service')
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def _paths_ready() -> bool:
    return os.name=='nt' and PYTHON.is_file() and DAEMON.is_file() and BACKEND.is_dir()


def _spawn_service():
    LOG_FILE.parent.mkdir(parents=True,exist_ok=True)
    with LOG_FILE.open('ab') as log:
        return subprocess.Popen(service_command(),cwd=str(BACKEND),env=service_environment(),
                                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP,
                                close_fds=True)


def _terminate_and_wait(process) -> bool:
    try:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except (subprocess.TimeoutExpired,psutil.TimeoutExpired):
            process.kill()
            process.wait(timeout=1.0)
        return True
    except psutil.NoSuchProcess:
        return True
    except (OSError,psutil.Error,subprocess.TimeoutExpired,AttributeError):
        return False


def _cleanup_owned_start(process) -> bool:
    """Bounded cleanup of this attempt's captured launcher and proven base child.

    Never terminate an unrelated listener, descendant with other arguments, or
    an interpreter whose identity is not declared by the fixed virtualenv.
    """
    children=[];enumerated=False
    try:
        parent=psutil.Process(process.pid)
        if _fixed_command(parent,service_command(),_normalized_path(str(PYTHON))):
            base=_declared_base_python()
            descendants=parent.children()
            enumerated=len(descendants)<=8
            for child in descendants[:8]:
                if (base is not None and child.ppid()==process.pid
                        and _fixed_command(child,service_command(),base)):
                    children.append(child)
    except psutil.NoSuchProcess:
        # A naturally exited redirector does not prove an unknown orphan exited.
        enumerated=False
    except (OSError,psutil.Error,ValueError):
        enumerated=False
    exited=[_terminate_and_wait(child) for child in children]
    launcher_exited=_terminate_and_wait(process)
    return enumerated and all(exited) and launcher_exited


def _startup_failure(code,process) -> dict:
    return {**_error(code),'started':True,'launcher_pid':process.pid,
            'cleanup_confirmed':_cleanup_owned_start(process),
            'cleanup_scope':'captured_control_launcher_and_verified_base_child_only'}


def ensure_broadcast_service_online(*, timeout_s: float=12.0) -> dict:
    """Call only after validating configured destinations and explicit Start intent.

    No broadcast is submitted, no other daemon is started, and no conflicting
    listener is terminated. Readiness requires matching health and socket PID.
    """
    process=None
    try:
        timeout=float(timeout_s)
        if not math.isfinite(timeout) or not 1<=timeout<=20:
            return _error('INVALID_TIMEOUT')
    except (ValueError,TypeError):
        return _error('INVALID_TIMEOUT')
    observed=probe_broadcast_service()
    if observed['status']=='ready' or observed['status']=='error':
        return observed
    try:
        with _startup_lock():
            observed=probe_broadcast_service()
            if observed['status']=='ready' or observed['status']=='error':
                return observed
            if not _paths_ready():
                return _error('RUNTIME_UNAVAILABLE')
            process=_spawn_service()
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    return _startup_failure('START_FAILED',process)
                observed=probe_broadcast_service()
                if observed['status']=='ready':
                    if observed['pid']!=process.pid and observed.get('launcher_pid')!=process.pid:
                        return _startup_failure('PORT_CONFLICT',process)
                    return {**observed,'started':True}
                if observed.get('code')=='PORT_CONFLICT':
                    return _startup_failure('PORT_CONFLICT',process)
                time.sleep(0.2)
            return _startup_failure('START_TIMEOUT',process)
    except (OSError,ValueError,psutil.Error):
        return _startup_failure('START_UNAVAILABLE',process) if process is not None else _error('START_UNAVAILABLE')
