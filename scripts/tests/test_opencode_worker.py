"""Offline boundaries; only disposable Python children, never OpenCode/model calls."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch

MODULE=Path(__file__).resolve().parents[2]/"backend/core/opencode_worker.py"
spec=importlib.util.spec_from_file_location("aibs_opencode_worker",MODULE)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

def event(kind,**part):
    return (json.dumps({"type":kind,"timestamp":1,"sessionID":"ses_fixture",
        "part":{"sessionID":"ses_fixture","messageID":"msg_fixture","id":"part_fixture",**part}})+"\n").encode()
def complete():
    return event("step_start")+event("text",text="Proposal only.")+event("step_finish",reason="stop",cost=0,tokens={"input":1,"output":2})

class Contracts(unittest.TestCase):
    def test_catalog_is_pure_and_does_not_expose_mutable_state(self):
        rows=worker.list_worker_models()
        self.assertEqual(len(rows),12)
        self.assertEqual(len({r["id"] for r in rows}),12)
        self.assertTrue(all(r["free_limited_time"] for r in rows))
        self.assertTrue(next(r for r in rows if "lightning" in r["id"])["public_nonconfidential_input_only"])
        rows[0]["id"]="changed"
        self.assertNotEqual(worker.list_worker_models()[0]["id"],"changed")

    def test_input_boundaries(self):
        for args,code in [(("", "big-pickle","task"),"owner_required"),
                          (("owner","paid-model","task"),"unknown_worker_model"),
                          (("owner","big-pickle",""),"prompt_required"),
                          (("owner","big-pickle","\ud800"),"invalid_prompt"),
                          (("owner","big-pickle","x"*32769),"prompt_too_large")]:
            with self.subTest(code=code),self.assertRaises(worker.WorkerError) as raised:
                worker._validate(*args)
            self.assertEqual(raised.exception.code,code)

    def test_owner_and_global_concurrency(self):
        gate=worker._Gate()
        gate.acquire("a")
        with self.assertRaises(worker.WorkerError):gate.acquire("a")
        gate.acquire("b")
        with self.assertRaises(worker.WorkerError):gate.acquire("c")
        gate.release("a");gate.acquire("c")
        gate.release("b");gate.release("c")

    def test_nvidia_requires_explicit_boolean_public_input_declaration(self):
        for model in ("nemotron-3.5-lightning-free","nemotron-3.5-super-vl-free"):
            with self.assertRaises(worker.WorkerError) as raised:
                worker._validate("owner",model,"Review a fictional public fixture")
            self.assertEqual(raised.exception.code,"public_input_required")
            self.assertEqual(worker._validate("owner",model,"Public fixture",True),b"Public fixture")
            with self.assertRaises(worker.WorkerError):
                worker._validate("owner",model,"Public fixture","true")

    def test_native_error_metadata_excludes_plaintext_and_keeps_class_status(self):
        data=(json.dumps({"type":"error","sessionID":"ses_fixture",
            "error":{"type":"provider.authentication","statusCode":401,
                     "message":"Invalid API key fixture-secret-not-for-output"}})+"\n").encode()
        with self.assertRaises(worker.WorkerError) as raised:worker._NDJSON().feed(data)
        receipt=raised.exception.receipt
        self.assertEqual(receipt["native_error_class"],"authentication")
        self.assertEqual(receipt["native_http_status"],401)
        self.assertEqual(receipt["native_error_type"],"provider.authentication")
        self.assertNotIn("fixture-secret",json.dumps(receipt))

    def test_captured_429_has_fixed_public_rate_limit_contract(self):
        data=(json.dumps({"type":"error","timestamp":1,"sessionID":"ses_fixture",
            "error":{"type":"other","statusCode":429,"message":"private fixture provider details"}})+"\n").encode()
        with self.assertRaises(worker.WorkerError) as raised:worker._NDJSON().feed(data)
        err=raised.exception
        self.assertEqual((err.code,err.status_code),("worker_rate_limited",429))
        self.assertEqual(err.public_message,"OpenCode is rate limited. No fallback was used.")
        self.assertNotIn("private fixture",json.dumps(err.receipt))

    def test_startup_error_without_session_retains_safe_classification(self):
        for message,category in (("Authentication required","authentication"),
                                 ("Invalid configuration schema","configuration"),
                                 ("Model opencode/fixture not found","model_unavailable")):
            data=(json.dumps({"type":"error","timestamp":1,"sessionID":"",
                "error":{"type":"unknown","message":message}})+"\n").encode()
            with self.subTest(category=category),self.assertRaises(worker.WorkerError) as raised:
                worker._NDJSON().feed(data)
            self.assertEqual(raised.exception.code,"worker_failed")
            self.assertEqual(raised.exception.receipt["native_error_class"],category)

    def test_error_cannot_claim_a_different_existing_session(self):
        p=worker._NDJSON();p.feed(event("step_start"))
        data=b'{"type":"error","timestamp":1,"sessionID":"ses_other","error":{"message":"Authentication required"}}\n'
        with self.assertRaises(worker.WorkerError) as raised:p.feed(data)
        self.assertEqual(raised.exception.code,"worker_protocol_error")

    def test_private_environment_discards_provider_and_user_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.dict(os.environ,{"OPENAI_API_KEY":"fixture-secret","OPENCODE_CONFIG":"original",
                                        "OPENCODE_PASSWORD":"original","NODE_OPTIONS":"original",
                                        "PATH":"untrusted"},clear=False):
                env=worker._environment(root,"big-pickle")
            for name in ("OPENAI_API_KEY","OPENCODE_PASSWORD","OPENCODE_CONFIG","NODE_OPTIONS"):
                self.assertNotIn(name,env)
            for key in ("USERPROFILE","HOME","APPDATA","LOCALAPPDATA","ProgramData","TEMP","TMP",
                        "XDG_CONFIG_HOME","XDG_DATA_HOME","XDG_CACHE_HOME","XDG_STATE_HOME",
                        "OPENCODE_CONFIG_DIR","OPENCODE_TEST_HOME"):
                self.assertTrue(Path(env[key]).resolve().is_relative_to(root.resolve()),key)
            self.assertEqual(env["OPENCODE_CONFIG_PROJECT_DISABLE"],"1")
            config=json.loads(env["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(config["permissions"],[worker.DENY])
            self.assertEqual(config["policies"],[{"action":"tool.use","resource":"*","effect":"deny"}])
            self.assertFalse(config["warming"])
            self.assertFalse(config["compaction"]["auto"])
            self.assertEqual(config["plugins"],[])
            self.assertEqual(config["instructions"],[])
            self.assertEqual(config["skills"],[])
            self.assertEqual(config["agents"]["aibs-worker"]["permissions"],[worker.DENY])
            self.assertEqual(config["agents"]["aibs-worker"]["steps"],1)
            self.assertEqual(config["model"],"opencode/big-pickle")

    def test_parser_chunked_unicode_and_text_deltas(self):
        p=worker._NDJSON()
        data=event("step_start")+event("text",text="A ")+event("text",text="Δ")+event("step_finish",reason="stop",cost=0)
        for i in range(0,len(data),3):p.feed(data[i:i+3])
        self.assertEqual(p.finish(0),"A Δ")

    def test_step_finish_is_not_process_success(self):
        p=worker._NDJSON();p.feed(complete())
        with self.assertRaises(worker.WorkerError):p.finish(1)
        p=worker._NDJSON();p.feed(event("step_finish",reason="stop",cost=0))
        with self.assertRaises(worker.WorkerError):p.finish(0)

    def test_parser_rejects_protocol_leaks_and_tool_events(self):
        bad=[b"not json\n",b'{"type":"text","sessionID":"a","part":null}\n',
             b'{"type":"error","sessionID":"ses_fixture","error":{"message":"not returned"}}\n',
             b'{"type":"tool_use","sessionID":"ses_fixture","part":{}}\n',
             b'{"type":"background_wait","sessionID":"ses_fixture","jobs":[]}\n',
             event("text",text="\ud800"),event("step_finish",reason="length"),
             event("step_finish",reason="stop",cost=1),event("step_finish",reason="stop",cost=float("nan"))]
        for data in bad:
            with self.subTest(data=data[:45]),self.assertRaises(worker.WorkerError):
                worker._NDJSON().feed(data)

    def test_parser_rejects_cross_session_and_multiple_steps(self):
        p=worker._NDJSON();p.feed(event("step_start"))
        with self.assertRaises(worker.WorkerError):p.feed(event("text",text="x").replace(b"ses_fixture",b"ses_other"))
        p=worker._NDJSON();p.feed(event("step_start"))
        with self.assertRaises(worker.WorkerError):p.feed(event("text",text="x").replace(b"msg_fixture",b"msg_other"))

    def test_parser_caps_and_incomplete_lines(self):
        with self.assertRaises(worker.WorkerError):worker._NDJSON().feed(b"x"*(worker.LINE_LIMIT+1))
        p=worker._NDJSON();p.feed(event("step_start")+event("text",text="answer"))
        with self.assertRaises(worker.WorkerError):p.finish(0)
        p=worker._NDJSON();p.feed(complete()+b"{")
        with self.assertRaises(worker.WorkerError):p.finish(0)
        p=worker._NDJSON()
        with self.assertRaises(worker.WorkerError):
            for _ in range(20):p.feed(event("text",text="x"*6000))

    def test_native_retry_is_visible_metadata(self):
        p=worker._NDJSON();p.feed(b'{"type":"retry","sessionID":"ses_fixture","attempt":1}\n'+complete())
        self.assertEqual(p.retries,1)
        self.assertEqual(p.finish(0),"Proposal only.")

    def test_cleanup_refuses_wrong_root_and_owner_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/"request-fixture";root.mkdir()
            (root/".aibs-owned").write_text("right",encoding="ascii")
            with self.assertRaises(worker.WorkerError):worker._remove_request(root,base,"wrong")
            self.assertTrue(root.exists())
            worker._remove_request(root,base,"right")
            self.assertFalse(root.exists())

class AsyncContract(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_failure_never_spawns(self):
        error=worker.WorkerError("worker_binary_unqualified",503,"Unqualified")
        with patch.object(worker,"_preflight",side_effect=error),patch.object(worker,"_execute") as execute:
            with self.assertRaises(worker.WorkerError):
                await worker.run_worker(owner="owner",model="big-pickle",prompt="Review a synthetic function")
            execute.assert_not_called()

    async def test_disconnect_waits_for_cleanup_and_releases_owner(self):
        ended=threading.Event();started=threading.Event()
        def fake(exe,owner,model,data,cancel):
            started.set()
            if not cancel.wait(2):raise RuntimeError("test did not cancel")
            time.sleep(.05);ended.set()
            raise worker.WorkerError("worker_cancelled",499,"Cancelled")
        with patch.object(worker,"_preflight",return_value=Path("fixture")),patch.object(worker,"_execute",side_effect=fake):
            task=asyncio.create_task(worker.run_worker(owner="cancel-owner",model="big-pickle",prompt="Review"))
            await asyncio.to_thread(started.wait,1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertTrue(ended.is_set())
            await asyncio.sleep(0)
            self.assertNotIn("cancel-owner",worker._GATE.owners)

class PrivateCache(unittest.TestCase):
    def test_concurrent_request_admission_is_atomic_at_retained_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/"requests";base.mkdir()
            for i in range(3):(base/("request-retained-"+str(i))).mkdir()
            start=threading.Barrier(3)
            entered=threading.Event();release=threading.Event()
            real=tempfile.mkdtemp
            calls=[];results=[]
            def held_mkdtemp(*args,**kwargs):
                calls.append(True)
                if len(calls)==1:
                    entered.set()
                    if not release.wait(2):raise RuntimeError("Fixture release missing")
                return real(*args,**kwargs)
            def admit():
                start.wait()
                try:results.append(("admitted",worker._admit_request(base)))
                except worker.WorkerError as exc:results.append((exc.code,None))
            with patch.object(worker.tempfile,"mkdtemp",side_effect=held_mkdtemp):
                threads=[threading.Thread(target=admit) for _ in range(2)]
                for t in threads:t.start()
                try:
                    start.wait();self.assertTrue(entered.wait(1))
                    time.sleep(.03)
                    self.assertEqual(len(calls),1)
                finally:
                    release.set()
                    for t in threads:t.join(timeout=2)
            self.assertCountEqual([r[0] for r in results],["admitted","worker_cleanup_admission_limit"])
            self.assertEqual(sum(p.is_dir() for p in base.iterdir()),4)
            for status,value in results:
                if status=="admitted":worker._remove_request(value[0],base,value[1])

    def fixture(self,temp,stack):
        payload=b"public native fixture"
        exe=Path(temp)/"vendor.bin";exe.write_bytes(b"prefix"+payload+b"suffix")
        stack.enter_context(patch.dict(os.environ,{"LOCALAPPDATA":temp}))
        for key,value in {"NATIVE_DLL_NAME":"fixture.dll","NATIVE_DLL_BYTES":len(payload),
                          "NATIVE_DLL_SHA256":__import__("hashlib").sha256(payload).hexdigest(),
                          "NATIVE_DLL_OFFSET":6}.items():
            stack.enter_context(patch.object(worker,key,value))
        return exe,payload

    def test_cache_is_owner_partitioned_and_reuses_only_pinned_binary(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            exe,payload=self.fixture(temp,stack)
            a,am=worker._prepare_cache(exe,"owner-a")
            b,bm=worker._prepare_cache(exe,"owner-b")
            again,_=worker._prepare_cache(exe,"owner-a")
            self.assertNotEqual(a,b);self.assertEqual(a,again)
            self.assertEqual((a/"fixture.dll").read_bytes(),payload)
            self.assertNotEqual(am["owner_sha256"],bm["owner_sha256"])
            self.assertNotIn("owner-a",str(a))
            root=Path(temp)/"request";root.mkdir()
            env=worker._environment(root,"big-pickle",a)
            self.assertEqual(env["TEMP"],str(a));self.assertEqual(env["TMP"],str(a))
            self.assertTrue(Path(env["XDG_DATA_HOME"]).is_relative_to(root))
            self.assertTrue(Path(env["USERPROFILE"]).is_relative_to(root))

    def test_wrong_same_size_dll_is_quarantined_without_replacement(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            exe,payload=self.fixture(temp,stack)
            bucket,_=worker._prepare_cache(exe,"owner")
            dll=bucket/"fixture.dll";dll.write_bytes(b"x"*len(payload))
            with self.assertRaises(worker.WorkerError) as raised:worker._prepare_cache(exe,"owner")
            self.assertEqual(raised.exception.code,"worker_cache_quarantined")
            self.assertEqual(dll.read_bytes(),b"x"*len(payload))
            with self.assertRaises(worker.WorkerError):worker._prepare_cache(exe,"owner")

    def test_unknown_content_is_preserved_and_owner_admission_stops(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            exe,_=self.fixture(temp,stack)
            bucket,_=worker._prepare_cache(exe,"owner")
            unknown=bucket/"unexpected.txt";unknown.write_text("synthetic private fixture")
            with self.assertRaises(worker.WorkerError) as raised:worker._prepare_cache(exe,"owner")
            self.assertEqual(raised.exception.code,"worker_cache_quarantined")
            self.assertTrue(unknown.exists());self.assertTrue((bucket/".aibs-quarantined").exists())

    def test_owner_and_byte_caps_do_not_create_extra_buckets(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            exe,_=self.fixture(temp,stack)
            bucket,_=worker._prepare_cache(exe,"owner-a")
            with patch.object(worker,"MAX_CACHE_OWNERS",1):
                with self.assertRaises(worker.WorkerError):worker._prepare_cache(exe,"owner-b")
            self.assertEqual(sum(p.is_dir() for p in bucket.parent.iterdir()),1)
            with patch.object(worker,"MAX_CACHE_BYTES",1):
                with self.assertRaises(worker.WorkerError):worker._prepare_cache(exe,"owner-a")

    def test_seed_cannot_be_taken_from_unpinned_embedded_bytes(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            exe,payload=self.fixture(temp,stack)
            exe.write_bytes(b"prefix"+b"x"*len(payload)+b"suffix")
            with self.assertRaises(worker.WorkerError) as raised:worker._prepare_cache(exe,"owner")
            self.assertEqual(raised.exception.code,"worker_cache_quarantined")

@unittest.skipUnless(os.name=="nt","Actual Windows owned-process checks")
class WindowsJob(unittest.TestCase):
    def test_locked_profile_preflight_preserves_other_files(self):
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/"request-locked";root.mkdir()
            (root/".aibs-owned").write_text("owner",encoding="ascii")
            locked=root/"locked.dll";locked.write_bytes(b"synthetic")
            other=root/"evidence.txt";other.write_text("synthetic metadata")
            kernel=ctypes.WinDLL("kernel32",use_last_error=True)
            kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
            kernel.CreateFileW.restype=wintypes.HANDLE
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            handle=kernel.CreateFileW(str(locked),0x80000000,1,None,3,0,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            try:
                with self.assertRaises(worker.WorkerError) as raised:worker._remove_request(root,base,"owner")
                self.assertEqual(raised.exception.code,"worker_cleanup_failed")
                self.assertTrue(other.exists())
                self.assertTrue((root/".aibs-owned").exists())
            finally:kernel.CloseHandle(handle)
            worker._remove_request(root,base,"owner")
            self.assertFalse(root.exists())

    def test_failed_native_cause_survives_secondary_cleanup_failure(self):
        real_process=worker._WinProcess
        vendor_exe=worker._binary_path()
        script="import sys;sys.stdin.buffer.read();print('{\"type\":\"error\",\"sessionID\":\"ses_fixture\",\"error\":{\"type\":\"provider.authentication\",\"statusCode\":401,\"message\":\"authentication required\"}}',flush=True)"
        roots=[]
        def fake_process(argv,cwd,env):
            roots.append(cwd.parents[1])
            return real_process([sys.executable,"-I","-c",script],cwd,env)
        cleanup=worker.WorkerError("worker_cleanup_failed",503,"Fixture lock",receipt={"cleanup_winerror":32})
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{"LOCALAPPDATA":temp}),patch.object(worker,"_WinProcess",side_effect=fake_process):
            with patch.object(worker,"_remove_request",side_effect=cleanup):
                with self.assertRaises(worker.WorkerError) as raised:
                    worker._execute(vendor_exe,"owner","big-pickle",b"public synthetic",threading.Event())
            err=raised.exception
            self.assertEqual(err.code,"worker_failed")
            self.assertEqual(err.receipt["native_error_class"],"authentication")
            self.assertEqual(err.receipt["native_http_status"],401)
            self.assertEqual(err.receipt["cleanup_status"],"failed_preserved")
            self.assertTrue(err.receipt["job_drained"])
            self.assertEqual(err.receipt["cleanup_winerror"],32)
            for root in roots:worker._remove_request(root,root.parent,(root/".aibs-owned").read_text())

    def test_mapped_public_runtime_dll_does_not_block_private_profile_cleanup(self):
        import ctypes
        from ctypes import wintypes as w
        vendor_exe=worker._binary_path()
        if not vendor_exe.is_file():self.skipTest("Pinned vendor executable unavailable")
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{"LOCALAPPDATA":temp}):
            cache,expected=worker._prepare_cache(vendor_exe,"mapped-fixture-owner")
            dll=cache/worker.NATIVE_DLL_NAME
            kernel=ctypes.WinDLL("kernel32",use_last_error=True)
            kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
            kernel.CreateFileW.restype=w.HANDLE
            kernel.CreateFileMappingW.argtypes=[w.HANDLE,ctypes.c_void_p,w.DWORD,w.DWORD,w.DWORD,w.LPCWSTR]
            kernel.CreateFileMappingW.restype=w.HANDLE
            kernel.MapViewOfFile.argtypes=[w.HANDLE,w.DWORD,w.DWORD,w.DWORD,ctypes.c_size_t]
            kernel.MapViewOfFile.restype=ctypes.c_void_p
            kernel.UnmapViewOfFile.argtypes=[ctypes.c_void_p]
            kernel.CloseHandle.argtypes=[w.HANDLE]
            kernel.DeleteFileW.argtypes=[w.LPCWSTR]
            handle=kernel.CreateFileW(str(dll),0x80000000,7,None,3,0,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            mapping=kernel.CreateFileMappingW(handle,None,0x11000002,0,0,None)  # SEC_IMAGE_NO_EXECUTE|PAGE_READONLY
            self.assertTrue(mapping,ctypes.get_last_error())
            view=kernel.MapViewOfFile(mapping,4,0,0,0)
            self.assertTrue(view,ctypes.get_last_error())
            try:
                probe=kernel.CreateFileW(str(dll),0x10000,7,None,3,0,None)
                self.assertNotEqual(probe,ctypes.c_void_p(-1).value)
                kernel.CloseHandle(probe)
                self.assertFalse(kernel.DeleteFileW(str(dll)))
                self.assertEqual(ctypes.get_last_error(),5)
                base=Path(temp)/"requests";base.mkdir()
                request=base/"request-fixture";request.mkdir()
                (request/".aibs-owned").write_text("owned",encoding="ascii")
                (request/"context.txt").write_text("synthetic private fixture")
                worker._remove_request(request,base,"owned")
                self.assertFalse(request.exists());self.assertTrue(dll.exists())
                worker._check_cache(cache,expected)
                reused,_=worker._prepare_cache(vendor_exe,"mapped-fixture-owner")
                self.assertEqual(reused,cache)
            finally:
                kernel.UnmapViewOfFile(view);kernel.CloseHandle(mapping);kernel.CloseHandle(handle)

    def test_suspended_assigned_process_stdin_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            env={k:v for k,v in os.environ.items() if k in ("SystemRoot","WINDIR","PATH")}
            p=worker._WinProcess([sys.executable,"-I","-c",
                "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stdout.flush()"],Path(temp),env)
            try:
                p.stdin.write(b"synthetic stdin only");p.stdin.close()
                limit=time.monotonic()+5
                while p.poll() is None and time.monotonic()<limit:time.sleep(.02)
                self.assertEqual(p.poll(),0)
                self.assertEqual(p.stdout.read(),b"synthetic stdin only")
            finally:p.close()

    def test_job_close_kills_owned_descendant(self):
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as temp:
            env={k:v for k,v in os.environ.items() if k in ("SystemRoot","WINDIR","PATH")}
            script="import subprocess,sys,time; c=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']); print(c.pid,flush=True);time.sleep(30)"
            p=worker._WinProcess([sys.executable,"-I","-c",script],Path(temp),env)
            try:
                line=p.stdout.readline()
                child=int(line)
                kernel=ctypes.WinDLL("kernel32",use_last_error=True)
                kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
                kernel.OpenProcess.restype=wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
                kernel.CloseHandle.argtypes=[wintypes.HANDLE]
                handle=kernel.OpenProcess(0x100000,False,child)
                self.assertTrue(handle)
                p.close()
                try:self.assertEqual(kernel.WaitForSingleObject(handle,3000),0)
                finally:kernel.CloseHandle(handle)
            finally:p.close()

if __name__=="__main__":unittest.main(verbosity=2)

