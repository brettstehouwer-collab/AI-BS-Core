"""Bounded Windows check processes. This is containment, not a VM sandbox.

Commands retain host filesystem/network privileges. Expanded untrusted execution
still requires the separately verified Windows VM worker.
"""
import os
import subprocess
import threading
import time

import psutil


def run_bounded_check(argv, cwd, env, timeout_seconds=30, output_limit=262144, cancelled=None,
                      cpu_rate_percent=None, memory_limit_bytes=None, below_normal=False):
    started=time.monotonic()
    result={'argv':argv,'returncode':None,'stdout':'','stderr':''}
    if os.name!='nt':
        return {**result,'error':'Windows process containment unavailable'}
    if cancelled and cancelled():
        return {**result,'error':'cancelled'}
    output_limit=min(max(int(output_limit),1024),1048576)
    deadline=started+max(float(timeout_seconds),.01)
    chunks={'stdout':bytearray(),'stderr':bytearray()}
    limit_hit=threading.Event()
    buffer_lock=threading.Lock()
    process=None;job=None;readers=[]
    def consume(pipe,name):
        try:
            while True:
                block=pipe.read(4096)
                if not block:break
                with buffer_lock:
                    used=sum(map(len,chunks.values()))
                    remaining=output_limit-used
                    chunks[name].extend(block[:max(remaining,0)])
                    if len(block)>remaining:limit_hit.set()
        finally:
            pipe.close()
    try:
        import win32api
        import win32job
        import win32process
        job=win32job.CreateJobObject(None,'')
        limits=win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags']=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if memory_limit_bytes is not None:
            if type(memory_limit_bytes) is not int or not 64*1024*1024 <= memory_limit_bytes <= 4*1024*1024*1024:
                raise ValueError('Invalid owned-job memory limit')
            limits['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
            limits['JobMemoryLimit'] = memory_limit_bytes
        win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,limits)
        if cpu_rate_percent is not None:
            if type(cpu_rate_percent) is not int or not 1 <= cpu_rate_percent <= 100:
                raise ValueError('Invalid owned-job CPU limit')
            import ctypes
            from ctypes import wintypes
            class CpuRate(ctypes.Structure):
                _fields_ = [('ControlFlags', wintypes.DWORD), ('CpuRate', wintypes.DWORD)]
            cap = CpuRate(0x1 | 0x4, cpu_rate_percent*100)
            set_job = ctypes.WinDLL('kernel32', use_last_error=True).SetInformationJobObject
            set_job.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
            set_job.restype = wintypes.BOOL
            if not set_job(int(job), 15, ctypes.byref(cap), ctypes.sizeof(cap)):
                raise ctypes.WinError(ctypes.get_last_error())
        process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 creationflags=win32process.CREATE_SUSPENDED | subprocess.CREATE_NO_WINDOW |
                                 (subprocess.BELOW_NORMAL_PRIORITY_CLASS if below_normal else 0))
        handle=win32api.OpenProcess(0x0100 | 0x0001 | 0x0400,False,process.pid)
        try:
            win32job.AssignProcessToJobObject(job,handle)
            if not win32job.IsProcessInJob(handle,job):
                raise RuntimeError('Command was not assigned to its process job')
        finally:
            handle.Close()
        for name in chunks:
            thread=threading.Thread(target=consume,args=(getattr(process,name),name),daemon=True)
            thread.start();readers.append(thread)
        psutil.Process(process.pid).resume()
        while process.poll() is None:
            if cancelled and cancelled():
                result['error']='cancelled';break
            if limit_hit.is_set():
                result['error']='output_limit';break
            if time.monotonic()>=deadline:
                result['error']='timeout';break
            time.sleep(.02)
        # Close kills ordinary descendants even if the immediate parent exited.
        job.Close();job=None
        process.wait(timeout=5)
        for thread in readers:thread.join(timeout=5)
        if any(thread.is_alive() for thread in readers):
            result['error']='output_reader_did_not_finish'
        if limit_hit.is_set() and 'error' not in result:
            result['error']='output_limit'
        result['returncode']=process.returncode
    except Exception as exc:
        result['error']='process_control: '+str(exc)
    finally:
        if job is not None:job.Close()
        if process is not None:
            if process.poll() is None:process.kill()
            process.wait(timeout=5)
            if result['returncode'] is None:result['returncode']=process.returncode
            for thread in readers:thread.join(timeout=2)
            for name in chunks:
                pipe=getattr(process,name)
                if pipe and not pipe.closed:pipe.close()
        with buffer_lock:
            result.update({name:bytes(value).decode('utf-8','replace') for name,value in chunks.items()})
        result['execution_time_ms']=round((time.monotonic()-started)*1000)
    return result
