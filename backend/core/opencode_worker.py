"""Bounded, additive OpenCode2.2.7 coding/review delegation.

No import-time IO, provider configuration reuse, shell invocation, or model calls.
Only explicit current-prompt context is supplied to the genuine pinned CLI.
"""
from __future__ import annotations
import asyncio
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

VERSION = "2.2.7"
BINARY_SHA256 = "e06a04f8ec2cbaab32262e9af1474975228a5e8d9ae516da67ac4d1cf0bade8a"
PROMPT_LIMIT = 32768
OUTPUT_LIMIT = 131072
CONTENT_LIMIT = 65536
LINE_LIMIT = 65536
DEADLINE_SECONDS = 60
MAX_GLOBAL = 2
MAX_CACHE_OWNERS = 8
MAX_CACHE_BYTES = 128 * 1024 * 1024
MAX_RETAINED_REQUESTS = 4
NATIVE_DLL_NAME = ".bun-3859825750-eb880eeb01e175aa.dll"
NATIVE_DLL_BYTES = 8886664
NATIVE_DLL_SHA256 = "18b068e3745133329eb811956b48f098e6d389d49d89d1fff3f4ba8ef8e26689"
NATIVE_DLL_OFFSET = 194031092  # Exact embedded bytes in the pinned vendor executable.
_CACHE_LOCK = threading.Lock()
DENY = {"action": "*", "resource": "*", "effect": "deny"}
_MODEL_ROWS = (
 ("beam-free","Beam Free","30-day safety retention; no training.","Regional exclusions apply.",False),
 ("big-pickle","Big Pickle","Data may improve the model.","",False),
 ("deepseek-v4.1-flash-free","DeepSeek V4.1 Flash Free","Zero retention; no training.","",False),
 ("flint-40b-free","Flint 40B Free","30-day retention; data may improve the model.","",False),
 ("glm-5.3-flash-free","GLM-5.3-Flash Free","Zero retention; no training.","",False),
 ("iceman-free","Iceman Free","Retained and used for improvement.","",False),
 ("inkling-2-small-free","Inkling 2 Small Free","Retained; may be used for monitoring/training.","Unavailable in EU and other listed regions.",False),
 ("longcat-2.5-free","LongCat 2.5 Free","Zero retention; no training.","China hosting; 100 requests/day.",False),
 ("mimo-v2.6-flash-free","MiMo-V2.6-Flash Free","Data may improve the model.","",False),
 ("minimax-m3.1-flash-free","MiniMax M3.1 Flash Free","Zero retention; no training.","",False),
 ("nemotron-3.5-lightning-free","Nemotron 3.5 Lightning Free","NVIDIA trial logging/improvement.","Do not submit personal or confidential input.",True),
 ("nemotron-3.5-super-vl-free","Nemotron 3.5 Super VL Free","NVIDIA trial logging/improvement.","Do not submit personal or confidential input.",True),
)
_MODELS = frozenset(row[0] for row in _MODEL_ROWS)

class WorkerError(Exception):
    def __init__(self, code: str, status_code: int, public_message: str, *, receipt=None):
        super().__init__(public_message)
        self.code, self.status_code, self.public_message = code, status_code, public_message
        self.receipt = receipt or {}

def list_worker_models() -> list[dict]:
    """Static metadata only; this does not assert account/region/quota eligibility."""
    return [{"id":r[0], "name":r[1], "model":"opencode/"+r[0],
             "free_limited_time":True, "privacy":r[2], "limits":r[3],
             "public_nonconfidential_input_only":r[4],
             "source":"https://opencode.ai/docs/console/models/",
             "verified_date":"2026-11-10", "availability":"not_model_tested"}
            for r in _MODEL_ROWS]

class _Gate:
    def __init__(self):
        self.lock, self.owners = threading.Lock(), set()
    def acquire(self, owner):
        with self.lock:
            if owner in self.owners or len(self.owners) >= MAX_GLOBAL:
                raise WorkerError("worker_busy",429,"An OpenCode worker is already busy. Try later.")
            self.owners.add(owner)
    def release(self, owner):
        with self.lock:
            self.owners.discard(owner)
_GATE = _Gate()

def _validate(owner, model, prompt, public_input_only=False):
    if not isinstance(owner,str) or not owner.strip() or len(owner)>512:
        raise WorkerError("owner_required",403,"An authenticated owner is required.")
    if not isinstance(model,str) or model not in _MODELS:
        raise WorkerError("unknown_worker_model",400,"Choose a documented OpenCode worker model.")
    if type(public_input_only) is not bool:
        raise WorkerError("invalid_public_input_flag",400,"The public-input declaration must be a boolean.")
    if model.startswith("nemotron-") and not public_input_only:
        raise WorkerError("public_input_required",400,"This NVIDIA trial model requires an explicit declaration of public, nonconfidential input.")
    if not isinstance(prompt,str) or not prompt.strip():
        raise WorkerError("prompt_required",400,"Provide an explicit coding or review task.")
    try:
        data = prompt.encode("utf-8",errors="strict")
    except UnicodeError:
        raise WorkerError("invalid_prompt",400,"The task must be valid UTF-8.") from None
    if len(data)>PROMPT_LIMIT:
        raise WorkerError("prompt_too_large",413,"The OpenCode task exceeds 32 KiB.")
    return data

def _sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _no_reparse(path):
    for p in (path,*path.parents):
        try:
            s=p.lstat()
        except FileNotFoundError:
            continue
        if getattr(s,"st_file_attributes",0)&0x400 or p.is_symlink():
            raise WorkerError("unsafe_runtime_path",503,"The worker runtime path is not eligible.")

def _binary_path():
    local=os.environ.get("LOCALAPPDATA")
    if not local:
        raise WorkerError("worker_not_installed",503,"The user-local OpenCode CLI is unavailable.")
    return Path(local)/"AI-BS/cli/node_modules/@opencode/cli/bin/opencode.exe"

def _preflight():
    if os.name!="nt":
        raise WorkerError("unsupported_worker_platform",503,"This worker requires its verified Windows runtime.")
    exe=_binary_path()
    _no_reparse(exe)
    if not exe.is_file() or _sha(exe)!=BINARY_SHA256:
        raise WorkerError("worker_binary_unqualified",503,"The pinned OpenCode 2.2.7 binary is unavailable or changed.")
    return exe

def _worker_config(model):
    agent={"description":"Explicit bounded coding/review proposal only",
           "mode":"primary","system":"Review or propose code using only the supplied task. Do not use tools.",
           "permissions":[dict(DENY)],"steps":1}
    agents={x:{"disabled":True} for x in ("build","plan","general","explore","title","summary","compaction")}
    agents["aibs-worker"]=agent
    return {"$schema":"https://opencode.ai/config.json","update":"disable",
        "model":"opencode/"+model,"permissions":[dict(DENY)],
        "policies":[{"action":"tool.use","resource":"*","effect":"deny"}],
        "agents":agents,"instructions":[],"skills":[],"plugins":[],"mcp":{},
        "snapshots":False,"formatter":False,"warming":False,"compaction":{"auto":False},
        "experimental":{"all_flags":False,"background_compaction":False},
        "providers":{"opencode":{"settings":{"cache":{"warming":False}},
            "models":{model:{"settings":{"cache":{"warming":False}}}}}}}

def _environment(root, model, runtime_temp=None):
    # An allowlist, not a copy of the backend's environment or account settings.
    names=("SystemRoot","WINDIR","ComSpec","PROCESSOR_ARCHITECTURE",
           "PROCESSOR_IDENTIFIER","NUMBER_OF_PROCESSORS","OS")
    env={k:os.environ[k] for k in names if k in os.environ}
    system=os.environ.get("SystemRoot",r"C:\Windows")
    env["PATH"]=str(Path(system)/"System32")+";"+system
    env.update({"NO_COLOR":"1","CI":"1","OPENCODE_CONFIG_PROJECT_DISABLE":"1",
        "OPENCODE_DISABLE_CLAUDE_CODE":"1","OPENCODE_DISABLE_FILEWATCHER":"1",
        "OPENCODE_DISABLE_FFF":"1","OPENCODE_DISABLE_MODELS_FETCH":"1",
        "OPENCODE_CONFIG_CONTENT":json.dumps(_worker_config(model),separators=(",",":"))})
    paths={"USERPROFILE":"home","HOME":"home","APPDATA":"home/roaming",
        "LOCALAPPDATA":"home/local","ProgramData":"system","TEMP":"tmp","TMP":"tmp",
        "XDG_CONFIG_HOME":"home/config","XDG_DATA_HOME":"home/data",
        "XDG_CACHE_HOME":"home/cache","XDG_STATE_HOME":"home/state",
        "OPENCODE_CONFIG_DIR":"home/config/opencode","OPENCODE_TEST_HOME":"home"}
    for key,rel in paths.items():
        p=root/rel
        p.mkdir(parents=True,exist_ok=True)
        env[key]=str(p)
    if runtime_temp is not None:
        # Generic runtime TEMP is PRIVATE to this verified owner, never called public.
        # Owner context/auth/session data still has fresh request-scoped XDG/home roots.
        env["TEMP"]=env["TMP"]=str(runtime_temp)
    return env

def _cache_marker(owner):
    return {"schema":"aibs.opencode.private-runtime-cache.v1",
        "owner_sha256":hashlib.sha256(owner.encode("utf-8")).hexdigest(),
        "binary_sha256":BINARY_SHA256}

def _quarantine_cache(bucket, reason):
    # In-place quarantine: no new bucket, unknown-content read, move, delete or ACL change.
    marker=bucket/".aibs-quarantined"
    if not marker.exists():
        with open(marker,"x",encoding="ascii") as f:
            json.dump({"reason":reason},f)
    raise WorkerError("worker_cache_quarantined",503,
        "The private OpenCode runtime cache requires inspection.",
        receipt={"runtime_cache_status":"quarantined","private_cache_path":str(bucket),"cache_reason":reason})

def _check_cache(bucket, expected):
    _no_reparse(bucket)
    marker=bucket/".aibs-cache.json"
    _no_reparse(marker)
    if not marker.is_file() or marker.stat().st_size>1024:
        raise WorkerError("worker_cache_unqualified",503,"The private runtime cache ownership marker is invalid.")
    try:
        actual=json.loads(marker.read_text(encoding="ascii"))
    except (OSError,ValueError):
        raise WorkerError("worker_cache_unqualified",503,"The private runtime cache ownership marker is invalid.") from None
    if actual!=expected:
        raise WorkerError("worker_cache_unqualified",503,"The private runtime cache owner does not match.")
    if (bucket/".aibs-quarantined").exists():
        raise WorkerError("worker_cache_quarantined",503,"The private runtime cache is quarantined.")
    total=0
    count=0
    for p in bucket.iterdir():
        count+=1
        if count>4:
            _quarantine_cache(bucket,"unexpected_entry_count")
        _no_reparse(p)
        if p.name==".aibs-cache.json":
            total+=p.stat().st_size
        elif p.name==NATIVE_DLL_NAME and p.is_file():
            if p.stat().st_size!=NATIVE_DLL_BYTES or _sha(p)!=NATIVE_DLL_SHA256:
                _quarantine_cache(bucket,"native_binary_mismatch")
            total+=NATIVE_DLL_BYTES
        elif p.name=="opencode" and p.is_dir() and not any(p.iterdir()):
            pass
        else:
            _quarantine_cache(bucket,"unexpected_private_runtime_entry")
    return total

def _cache_budget(pinroot):
    owners=0
    total=0
    for bucket in pinroot.iterdir():
        _no_reparse(bucket)
        if not bucket.is_dir() or len(bucket.name)!=64 or any(c not in "0123456789abcdef" for c in bucket.name):
            raise WorkerError("worker_cache_unqualified",503,"The runtime cache contains an unrecognized entry.")
        owners+=1
        if owners>MAX_CACHE_OWNERS:
            raise WorkerError("worker_cache_capacity",503,"The local runtime cache admission limit was reached.")
        # Metadata-only cap; unexpected data is never read or reused across owners.
        entries=0
        for directory,dirs,files in os.walk(bucket,followlinks=False):
            for name in dirs+files:
                p=Path(directory)/name
                _no_reparse(p)
                entries+=1
                if entries>16:
                    raise WorkerError("worker_cache_capacity",503,"The local runtime cache admission limit was reached.")
                if p.is_file():
                    total+=p.stat().st_size
            if total>MAX_CACHE_BYTES:
                raise WorkerError("worker_cache_capacity",503,"The local runtime cache byte limit was reached.")
    return owners,total

def _prepare_cache(exe,owner):
    expected=_cache_marker(owner)
    pinroot=Path(os.environ["LOCALAPPDATA"])/"AI-BS/opencode-runtime"/BINARY_SHA256
    _no_reparse(pinroot)
    with _CACHE_LOCK:
        pinroot.mkdir(parents=True,exist_ok=True)
        owners,total=_cache_budget(pinroot)
        bucket=pinroot/expected["owner_sha256"]
        if not bucket.exists():
            if owners>=MAX_CACHE_OWNERS or total+NATIVE_DLL_BYTES+1024>MAX_CACHE_BYTES:
                raise WorkerError("worker_cache_capacity",503,"The local runtime cache admission limit was reached.")
            if shutil.disk_usage(pinroot).free<NATIVE_DLL_BYTES+64*1024*1024:
                raise WorkerError("worker_cache_capacity",503,"Insufficient free space for the bounded runtime cache.")
            bucket.mkdir()
            with open(bucket/".aibs-cache.json","x",encoding="ascii") as f:
                json.dump(expected,f)
        _check_cache(bucket,expected)
        dll=bucket/NATIVE_DLL_NAME
        if not dll.exists():
            # Seed only byte-for-byte public runtime material from the verified executable.
            with open(exe,"rb") as f:
                f.seek(NATIVE_DLL_OFFSET)
                payload=f.read(NATIVE_DLL_BYTES)
            if len(payload)!=NATIVE_DLL_BYTES or hashlib.sha256(payload).hexdigest()!=NATIVE_DLL_SHA256:
                _quarantine_cache(bucket,"embedded_native_binary_mismatch")
            with open(dll,"xb") as f:
                f.write(payload)
        _check_cache(bucket,expected)
        _cache_budget(pinroot)
        return bucket,expected

class _NDJSON:
    """Validate vendor events; never regard a step_finish alone as completion."""
    def __init__(self):
        self.pending=b""
        self.bytes=0
        self.session=None
        self.parts={}
        self.messages=set()
        self.finishes=0
        self.retries=0
        self.tokens=None
        self.cost=None
    def feed(self,data):
        self.bytes+=len(data)
        if self.bytes>OUTPUT_LIMIT:
            raise WorkerError("worker_output_limit",502,"The worker output limit was reached.")
        self.pending+=data
        while b"\n" in self.pending:
            line,self.pending=self.pending.split(b"\n",1)
            self._line(line)
        if len(self.pending)>LINE_LIMIT:
            raise WorkerError("worker_output_limit",502,"A worker output event exceeded its limit.")
    def _line(self,line):
        if not line.strip():
            return
        if len(line)>LINE_LIMIT:
            raise WorkerError("worker_output_limit",502,"A worker output event exceeded its limit.")
        try:
            obj=json.loads(line.decode("utf-8","strict"),parse_constant=lambda x:(_ for _ in ()).throw(ValueError()))
            if not isinstance(obj,dict):
                raise ValueError()
            kind=obj["type"]
            sid=obj["sessionID"]
            # The vendor emits an empty session ID for startup/target errors.
            # Error events fail closed and may be empty-or-current; content may not.
            if not isinstance(sid,str) or len(sid)>128 or (not sid and kind!="error"):
                raise ValueError()
            if self.session is not None and sid!=self.session and not (kind=="error" and sid==""):
                raise ValueError()
            if sid:
                self.session=sid
            if kind=="error":
                native=obj.get("error",{})
                message=str(native.get("message","")) if isinstance(native,dict) else ""
                lower=message.lower()
                status=next((native[k] for k in ("status","statusCode","httpStatus")
                    if isinstance(native,dict) and type(native.get(k)) is int and 100<=native[k]<=599),None)
                category="native_error"
                if status in (401,403) or any(x in lower for x in ("unauthorized","api key","credential","authentication")):
                    category="authentication"
                elif "model" in lower and any(x in lower for x in ("not found","not available","unknown","not supported")):
                    category="model_unavailable"
                elif status==429 or "rate limit" in lower or "quota" in lower:
                    category="quota_or_rate_limit"
                elif status in (503,529) or "capacity" in lower or "overloaded" in lower:
                    category="capacity"
                elif any(x in lower for x in ("enotfound","econn","network","fetch failed","transport")):
                    category="network"
                elif "config" in lower or "schema" in lower:
                    category="configuration"
                code="worker_rate_limited" if status==429 or category=="quota_or_rate_limit" else "worker_failed"
                public="OpenCode is rate limited. No fallback was used." if code=="worker_rate_limited" else "OpenCode reported an unsuccessful task."
                raise WorkerError(code,429 if code=="worker_rate_limited" else 502,public,
                    receipt={"native_error_class":category,"native_http_status":status,
                             "native_error_type":native.get("type") if isinstance(native,dict) and native.get("type") in ("unknown","aborted","provider.authentication","provider.model_not_found","provider.rate_limit","provider.transport","provider.overloaded") else "other",
                             "native_message_sha256":hashlib.sha256(message.encode("utf-8","replace")).hexdigest()})
            if kind in ("tool_use","background_wait"):
                raise WorkerError("worker_tool_event",502,"The worker attempted an operation outside its text-only boundary.")
            if kind=="retry":
                self.retries+=1
                return
            if kind not in ("step_start","step_finish","text"):
                raise ValueError()
            part=obj["part"]
            if not isinstance(part,dict) or part.get("sessionID")!=sid:
                raise ValueError()
            mid=part["messageID"]
            if not isinstance(mid,str) or not mid:
                raise ValueError()
            self.messages.add(mid)
            if len(self.messages)>1:
                raise WorkerError("worker_extra_step",502,"OpenCode produced more than the bounded worker step.")
            if kind=="step_finish":
                if part.get("reason")!="stop":
                    raise WorkerError("worker_incomplete",502,"OpenCode did not finish the task normally.")
                self.finishes+=1
                if self.finishes>1:
                    raise ValueError()
                self.tokens=part.get("tokens")
                cost=part.get("cost")
                if cost is not None and (not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(cost) or cost<0):
                    raise ValueError()
                # A supposedly free task must never silently report paid use.
                if cost is not None and cost>0:
                    raise WorkerError("worker_cost_rejected",502,"OpenCode reported a nonzero cost; no paid fallback is allowed.")
                self.cost=cost
            elif kind=="text":
                pid=part["id"]
                text=part["text"]
                if not isinstance(pid,str) or not pid or not isinstance(text,str):
                    raise ValueError()
                self.parts[pid]=self.parts.get(pid,"")+text
                if sum(len(t.encode("utf-8","strict")) for t in self.parts.values())>CONTENT_LIMIT:
                    raise WorkerError("worker_output_limit",502,"The worker answer exceeded its limit.")
        except WorkerError:
            raise
        except (KeyError,TypeError,ValueError,UnicodeError):
            raise WorkerError("worker_protocol_error",502,"OpenCode returned an invalid or unexpected event.") from None
    def finish(self,exit_code):
        if self.pending.strip():
            raise WorkerError("worker_protocol_error",502,"OpenCode ended with an incomplete event.")
        content="".join(self.parts.values())
        if exit_code!=0 or self.finishes!=1 or not content.strip():
            raise WorkerError("worker_incomplete",502,"OpenCode did not produce a complete answer.")
        return content

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

def _remove_request(root,parent,marker):
    # Check the exact absolute target before any Windows recursive deletion.
    base=parent.resolve(strict=True)
    target=root.resolve(strict=True)
    if target.parent!=base or not root.name.startswith("request-"):
        raise WorkerError("worker_cleanup_failed",503,"Worker cleanup containment failed.")
    _no_reparse(root)
    if (root/".aibs-owned").read_text(encoding="ascii")!=marker:
        raise WorkerError("worker_cleanup_failed",503,"Worker cleanup ownership failed.")
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            _no_reparse(Path(directory)/name)
    if os.name=="nt":
        # Probe delete access to every owned file before deleting any tree member.
        from ctypes import wintypes as w
        k=ctypes.WinDLL("kernel32",use_last_error=True)
        k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
        k.CreateFileW.restype=w.HANDLE
        k.CloseHandle.argtypes=[w.HANDLE]
        for directory,dirs,files in os.walk(root,followlinks=False):
            for name in files:
                h=k.CreateFileW(str(Path(directory)/name),0x10000,7,None,3,0,None)
                if h==ctypes.c_void_p(-1).value:
                    raise WorkerError("worker_cleanup_failed",503,"The owned request profile is still locked.",
                        receipt={"cleanup_winerror":ctypes.get_last_error(),"retained_profile":str(root)})
                k.CloseHandle(h)
    shutil.rmtree(root)

def _admit_request(base):
    _no_reparse(base)
    # One transaction for all owners: no stale count may admit another profile.
    with _CACHE_LOCK:
        base.mkdir(parents=True,exist_ok=True)
        if sum(1 for p in base.iterdir() if p.is_dir() and p.name.startswith("request-"))>=MAX_RETAINED_REQUESTS:
            raise WorkerError("worker_cleanup_admission_limit",503,"Retained private worker profiles require inspection before another task.")
        root=Path(tempfile.mkdtemp(prefix="request-",dir=base))
        marker=uuid.uuid4().hex
        (root/".aibs-owned").write_text(marker,encoding="ascii")
        return root,marker

def _execute(exe,owner,model,data,cancel):
    cache,cache_owner=_prepare_cache(exe,owner)
    base=Path(os.environ["LOCALAPPDATA"])/"AI-BS/opencode-workers"
    root,marker=_admit_request(base)
    proc=None
    stop=threading.Event()
    threads=[]
    request_id=uuid.uuid4().hex
    started=time.monotonic()
    parser=_NDJSON()
    stderr_bytes=0
    failure=None
    try:
        env=_environment(root,model,cache)
        workspace=root/"home/workspace";workspace.mkdir()
        argv=[str(exe),"run","--standalone","--model","opencode/"+model,
              "--agent","aibs-worker","--format","json","--archived","--title","AI-BS bounded code review"]
        proc=_WinProcess(argv,workspace,env)
        events=queue.Queue(maxsize=32)
        def read(kind,stream):
            try:
                while not stop.is_set():
                    chunk=stream.read(4096)
                    if not chunk:break
                    while not stop.is_set():
                        try:events.put((kind,chunk),timeout=.1);break
                        except queue.Full:pass
            except (OSError,ValueError):
                pass
            finally:
                while not stop.is_set():
                    try:events.put((kind,None),timeout=.1);break
                    except queue.Full:pass
        def write():
            try:
                view=memoryview(data)
                while view and not stop.is_set():
                    n=proc.stdin.write(view)
                    if not n:break
                    view=view[n:]
            except (OSError,ValueError):
                pass
            finally:
                try:proc.stdin.close()
                except (OSError,ValueError):pass
        for target,args in ((read,("stdout",proc.stdout)),(read,("stderr",proc.stderr)),(write,())):
            t=threading.Thread(target=target,args=args,daemon=True);t.start();threads.append(t)
        ends=set()
        exit_code=None
        while True:
            if cancel.is_set():
                raise WorkerError("worker_cancelled",499,"The owned OpenCode worker was terminated.")
            if time.monotonic()-started>DEADLINE_SECONDS:
                raise WorkerError("worker_timeout",504,"The owned OpenCode worker reached its deadline.")
            try:
                kind,chunk=events.get(timeout=.05)
                if chunk is None:ends.add(kind)
                elif kind=="stdout":parser.feed(chunk)
                else:
                    stderr_bytes+=len(chunk)
                    if stderr_bytes>OUTPUT_LIMIT:
                        raise WorkerError("worker_output_limit",502,"The worker diagnostic output exceeded its limit.")
            except queue.Empty:
                pass
            exit_code=proc.poll()
            if exit_code is not None and len(ends)==2 and events.empty():
                break
        content=parser.finish(exit_code)
        return {"content":content,"model":model,"status":"completed",
            "receipt":{"request_id":request_id,"worker":"OpenCode","version":VERSION,
                "binary_sha256":BINARY_SHA256,"proposal_only":True,"user_files_modified":False,
                "requested_model":"opencode/"+model,"actual_model":None,
                "model_identity_basis":"Explicit genuine CLI model pin; vendor NDJSON does not expose actual provider/model.",
                "session_id":parser.session,"exit_code":exit_code,"retry_events":parser.retries,
                "application_retries":0,"fallback_used":False,"tokens":parser.tokens,
                "reported_cost":parser.cost,"stderr_bytes":stderr_bytes,"output_bytes":parser.bytes,
                "runtime_cache":{"owner_partitioned":True,"binary_sha256":BINARY_SHA256,
                    "native_dll_sha256":NATIVE_DLL_SHA256,"retained":True},
                "elapsed_seconds":round(time.monotonic()-started,3),
                "cleanup":"Owned JobObject terminated/closed; fresh request profile removed.",
                "cancellation_semantics":"Windows termination; no claim of graceful remote-provider cancellation."}}
    except WorkerError as exc:
        failure=exc
        raise
    except Exception:
        failure=WorkerError("worker_runtime_error",503,"The isolated OpenCode worker could not complete.")
        raise failure from None
    finally:
        stop.set()
        drained=True
        if proc is not None:
            try:
                drained=proc.close()
            except Exception:
                drained=False
        for t in threads:
            t.join(timeout=1)
        details={"request_id":request_id,"requested_model":"opencode/"+model,
            "actual_model":None,"session_id":parser.session,"retry_events":parser.retries,
            "stderr_bytes":stderr_bytes,"output_bytes":parser.bytes,"job_drained":drained}
        if failure is not None:
            failure.receipt.update(details)
        try:
            if not drained:
                raise WorkerError("worker_cleanup_failed",503,"The owned worker job did not drain.")
            with _CACHE_LOCK:
                _check_cache(cache,cache_owner)
                _cache_budget(cache.parent)
            _remove_request(root,base,marker)
            if failure is not None:
                failure.receipt["cleanup_status"]="complete"
        except Exception as cleanup:
            details.update({"cleanup_status":"failed_preserved","retained_profile":str(root),
                "cleanup_error_type":type(cleanup).__name__,"cleanup_winerror":getattr(cleanup,"winerror",None)})
            if isinstance(cleanup,WorkerError):
                details.update(cleanup.receipt)
            if failure is not None:
                failure.receipt.update(details)
                # Do not overwrite a provider/runtime failure with a secondary cleanup failure.
            else:
                raise WorkerError("worker_cleanup_failed",503,"The owned request profile could not be fully cleaned.",receipt=details) from None

async def run_worker(*,owner:str,model:str,prompt:str,public_input_only:bool=False) -> dict:
    """Delegate the explicit current coding/review prompt; no history or RAG."""
    data=_validate(owner,model,prompt,public_input_only)
    exe=await asyncio.to_thread(_preflight)
    _GATE.acquire(owner)
    cancel=threading.Event()
    task=asyncio.create_task(asyncio.to_thread(_execute,exe,owner,model,data,cancel))
    # A disconnected caller must not free a concurrency slot while cleanup still runs.
    def released(completed):
        _GATE.release(owner)
        if not completed.cancelled():
            completed.exception()  # Consume late cleanup failures after a disconnected caller.
    task.add_done_callback(released)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancel.set()
        try:await asyncio.wait_for(asyncio.shield(task),8)
        except (WorkerError,asyncio.TimeoutError):pass
        raise

