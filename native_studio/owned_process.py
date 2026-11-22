"""Client-safe Windows process ownership, mechanically extracted from the reviewed worker.

Only stdlib imports and suspended-create/JobObject/pipe lifetime mechanics live
here. No provider, model catalog, private config, backend imports or import-time
I/O is present. This owns descendants, not filesystem or network isolation.

The legacy backend implementation remains untouched. Class-source equivalence
is pinned/tested so future divergence requires an explicit review.
"""
from __future__ import annotations
import ctypes
import os
import subprocess
import time

EXTRACTED_FROM = "backend/core/opencode_worker.py::_WinProcess"
BACKEND_SOURCE_SHA256 = '5e526213e3a5f9f801dd4f7147dbc93352411585b94e876181b179aa8fe2b234'
EXTRACTED_CLASS_SHA256 = '9d1aeaaaad7dd0fb90316b7bbf7971513e0ea42ab41733bacbc98c01cee6b99b'
EXTRACTION_BASIS = "UTF-8 class source with LF line endings; full backend file hash is byte-exact."

class OwnedProcessError(Exception):
    def __init__(self, code, status_code, public_message):
        super().__init__(public_message)
        self.code, self.status_code, self.public_message = code, status_code, public_message


# Keep the reviewed class body unchanged; only its local error alias is new.
WorkerError = OwnedProcessError

class _WinProcess:
    """Start suspended, assign exact JobObject, then resume; no descendant escape."""
    def __init__(self,argv,cwd,env):
        import _winapi
        import msvcrt
        from ctypes import wintypes as w
        k=ctypes.WinDLL("kernel32",use_last_error=True)
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
        k.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
        k.CloseHandle.argtypes=[w.HANDLE]
        k.ResumeThread.argtypes=[w.HANDLE];k.ResumeThread.restype=w.DWORD
        class BASIC(ctypes.Structure):
            _fields_=[("PerProcessUserTimeLimit",ctypes.c_int64),("PerJobUserTimeLimit",ctypes.c_int64),
              ("LimitFlags",w.DWORD),("MinimumWorkingSetSize",ctypes.c_size_t),("MaximumWorkingSetSize",ctypes.c_size_t),
              ("ActiveProcessLimit",w.DWORD),("Affinity",ctypes.c_size_t),("PriorityClass",w.DWORD),("SchedulingClass",w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(x,ctypes.c_uint64) for x in ("ReadOperationCount","WriteOperationCount","OtherOperationCount","ReadTransferCount","WriteTransferCount","OtherTransferCount")]
        class EXT(ctypes.Structure):
            _fields_=[("BasicLimitInformation",BASIC),("IoInfo",IO),("ProcessMemoryLimit",ctypes.c_size_t),
                      ("JobMemoryLimit",ctypes.c_size_t),("PeakProcessMemoryUsed",ctypes.c_size_t),("PeakJobMemoryUsed",ctypes.c_size_t)]
        self.k,self.api=k,_winapi
        self.job=k.CreateJobObjectW(None,None)
        self.hp=None
        self.pid=None
        self.stdout=self.stderr=self.stdin=None
        if not self.job:
            raise WorkerError("worker_job_unavailable",503,"Windows could not create an owned worker job.")
        limits=EXT();limits.BasicLimitInformation.LimitFlags=0x2000
        if not k.SetInformationJobObject(self.job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            self.close()
            raise WorkerError("worker_job_unavailable",503,"Windows could not enforce worker process cleanup.")
        fds=[]
        ht=None
        try:
            ir,iw=os.pipe();orr,ow=os.pipe();er,ew=os.pipe();fds=[ir,iw,orr,ow,er,ew]
            handles=[msvcrt.get_osfhandle(fd) for fd in (ir,ow,ew)]
            for h in handles:
                os.set_handle_inheritable(h,True)
            si=subprocess.STARTUPINFO()
            si.dwFlags|=subprocess.STARTF_USESTDHANDLES
            si.hStdInput,si.hStdOutput,si.hStdError=handles
            si.lpAttributeList={"handle_list":handles}
            flags=subprocess.CREATE_NO_WINDOW|0x00000004|0x00000400  # CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT
            self.hp,ht,self.pid,_=_winapi.CreateProcess(str(argv[0]),subprocess.list2cmdline(list(map(str,argv))),None,None,True,flags,env,str(cwd),si)
            if not k.AssignProcessToJobObject(self.job,self.hp):
                _winapi.TerminateProcess(self.hp,1)
                raise WorkerError("worker_job_unavailable",503,"Windows could not contain the worker process.")
            for fd in (ir,ow,ew):
                os.close(fd);fds.remove(fd)
            self.stdin=os.fdopen(iw,"wb",buffering=0);fds.remove(iw)
            self.stdout=os.fdopen(orr,"rb",buffering=0);fds.remove(orr)
            self.stderr=os.fdopen(er,"rb",buffering=0);fds.remove(er)
            if k.ResumeThread(ht)==0xffffffff:
                raise WorkerError("worker_launch_failed",503,"Windows could not start the contained worker.")
        except BaseException:
            self.close()
            raise
        finally:
            if ht is not None:
                _winapi.CloseHandle(ht)
            for fd in fds:
                os.close(fd)
    def poll(self):
        if self.hp is None:
            return None
        return None if self.api.WaitForSingleObject(self.hp,0)==258 else self.api.GetExitCodeProcess(self.hp)
    def close(self):
        drained=True
        if self.job:
            self.k.TerminateJobObject(self.job,1)
            from ctypes import wintypes as w
            class ACCOUNTING(ctypes.Structure):
                _fields_=[("user",ctypes.c_int64),("kernel",ctypes.c_int64),
                    ("period_user",ctypes.c_int64),("period_kernel",ctypes.c_int64),
                    ("faults",w.DWORD),("total",w.DWORD),("active",w.DWORD),("terminated",w.DWORD)]
            deadline=time.monotonic()+3
            while True:
                counts=ACCOUNTING()
                ok=self.k.QueryInformationJobObject(self.job,1,ctypes.byref(counts),ctypes.sizeof(counts),None)
                if ok and counts.active==0:
                    break
                if not ok or time.monotonic()>=deadline:
                    drained=False
                    break
                time.sleep(.01)
            self.k.CloseHandle(self.job)
            self.job=None
        if self.hp is not None:
            self.api.WaitForSingleObject(self.hp,3000)
            self.api.CloseHandle(self.hp)
            self.hp=None
        for name in ("stdin","stdout","stderr"):
            f=getattr(self,name,None)
            if f is not None:
                try:f.close()
                except OSError:pass
                setattr(self,name,None)
        return drained

OwnedProcess = _WinProcess
