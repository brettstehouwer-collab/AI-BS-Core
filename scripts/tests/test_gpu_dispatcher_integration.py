"""Offline integration coverage; all inference, inventory and coding dependencies are fake."""
import asyncio
import copy
from contextlib import asynccontextmanager
import importlib
import math
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from gpu.compute_scheduler import GPUAdmissionError
from orchestrator.gpu_task_dispatcher import OllamaDispatcher
from orchestrator import gpu_task_dispatcher as dispatcher_module


HOST = "http://127.0.0.1:11434"
SECONDARY = "http://127.0.0.1:11435"
MIB = 1024 ** 2
MODEL = {"name": "fixture:latest", "size": 4096 * MIB}


def response(payload, status=200):
    return httpx.Response(status, json=payload, request=httpx.Request("GET", HOST))


class FakeClients:
    """Record transport configuration and payload bytes without opening any socket."""
    def __init__(self, handler=None, stream_response=None):
        self.handler = handler
        self.stream_response = stream_response
        self.created = []
        self.calls = []
        self.open_clients = 0
        self.open_streams = 0

    def __call__(self, **kwargs):
        self.created.append(kwargs)
        return FakeClient(self)


class FakeClient:
    def __init__(self, owner):
        self.owner = owner

    async def __aenter__(self):
        self.owner.open_clients += 1
        return self

    async def __aexit__(self, *exc):
        self.owner.open_clients -= 1

    async def request(self, method, url, **kwargs):
        self.owner.calls.append((method, url, copy.deepcopy(kwargs)))
        if self.owner.handler is None:
            raise AssertionError("unexpected fake HTTP request")
        return self.owner.handler(method, url, kwargs)

    async def get(self, url, **kwargs):
        return await self.request("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self.request("POST", url, **kwargs)

    @asynccontextmanager
    async def stream(self, method, url, **kwargs):
        self.owner.calls.append((method, url, copy.deepcopy(kwargs)))
        self.owner.open_streams += 1
        try:
            yield self.owner.stream_response
        finally:
            self.owner.open_streams -= 1


class FakeStream:
    def __init__(self, lines=(), *, block=False, status=200):
        self.status_code = status
        self.lines = lines
        self.block = block
        self.waiting = asyncio.Event()

    async def aread(self):
        return b"synthetic upstream error"

    async def aiter_lines(self):
        for line in self.lines:
            yield line
        if self.block:
            self.waiting.set()
            await asyncio.Event().wait()


class FakeAdmission:
    def __init__(self, *, error=None, keep_alive_s=120):
        self.error = error
        self.keep_alive_s = keep_alive_s
        self.calls = []
        self.active = 0
        self.released = 0
        self.residency = []
        self.controller = self
        self.profile = {"keep_alive_s": keep_alive_s}
        self.snapshot_calls = 0
        self.enabled = True

    async def snapshot(self):
        self.snapshot_calls += 1
        return {"available_budget_mib": 10000}

    @asynccontextmanager
    async def lease(self, *args, **kwargs):
        self.calls.append((args, copy.deepcopy(kwargs)))
        if self.error:
            raise self.error
        self.active += 1
        try:
            yield {"gpu_admitted": True, "keep_alive_s": self.keep_alive_s, "host": HOST,
                   "num_ctx": 4096, "num_batch": 512}
        finally:
            self.active -= 1
            self.released += 1

    def update_residency(self, resident):
        self.residency.append(copy.deepcopy(resident))


class DispatcherIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def make_dispatcher(self, residency=(), *, refresh=None, controller=None):
        ps_reads = 0
        def handler(method, url, kwargs):
            nonlocal ps_reads
            self.assertEqual(method, "GET")
            if url.endswith("/api/tags"):
                return response({"models": [MODEL]})
            self.assertTrue(url.endswith("/api/ps"))
            ps_reads += 1
            models = residency if ps_reads == 1 or refresh is None else refresh
            return response({"models": models})
        clients = FakeClients(handler)
        admission = controller or FakeAdmission()
        return OllamaDispatcher(admission, clients), clients, admission

    async def test_cold_load_uses_weight_budget_and_profile_keepalive(self):
        dispatcher, clients, controller = self.make_dispatcher()
        async with dispatcher.lease("fixture", HOST, workload="agent", priority=15) as token:
            self.assertTrue(token["gpu_admitted"])
            desired = math.ceil(4096 * 1.10) + 1024 + 4 * 512
            self.assertEqual(token["estimated_incremental_mib"], desired)
            self.assertEqual(token["desired_allocation_mib"], desired)
            self.assertEqual(token["num_ctx"], 4096)
            self.assertEqual(token["num_batch"], 512)
            self.assertEqual(token["keep_alive_s"], 120)
            self.assertEqual(controller.active, 1)
        self.assertEqual(controller.released, 1)
        self.assertEqual(controller.calls[0][1]["workload"], "agent")
        self.assertEqual(controller.calls[0][1]["priority"], 15)
        self.assertTrue(all(c.get("trust_env") is False for c in clients.created))
        self.assertTrue(all(c[0] == "GET" for c in clients.calls))

    async def test_resident_model_has_positive_budget_and_fresh_metadata(self):
        resident = [{**MODEL, "size_vram": MODEL["size"]}]
        dispatcher, clients, controller = self.make_dispatcher(resident)
        async with dispatcher.lease("fixture", HOST) as token:
            self.assertEqual(token["estimated_incremental_mib"],
                             token["desired_allocation_mib"] - 4096)
            self.assertEqual(controller.residency[-1], resident)
        self.assertGreaterEqual(sum(url.endswith("/api/ps") for _, url, _ in clients.calls), 2)
        self.assertEqual(controller.active, 0)

    async def test_partial_residency_with_layer_option_reserves_full_load(self):
        resident = [{**MODEL, "size_vram": 128 * MIB}]
        dispatcher, _, controller = self.make_dispatcher(resident)
        async with dispatcher.lease("fixture", HOST, options={"num_gpu": 99, "num_ctx": 8192}) as token:
            # A nonzero residency value cannot prove requested layers/context match.
            self.assertEqual(token["estimated_incremental_mib"],
                             math.ceil(4096 * 1.10) + 1024 + 8 * 512 - 128)
            self.assertEqual(token["num_ctx"], 8192)
        self.assertGreaterEqual(controller.calls[-1][1]["estimated_vram_mib"], 4096)

    async def test_evicted_resident_reacquires_cold_budget_before_yield(self):
        resident = [{**MODEL, "size_vram": MODEL["size"]}]
        dispatcher, _, controller = self.make_dispatcher(resident, refresh=[])
        async with dispatcher.lease("fixture", HOST) as token:
            self.assertGreaterEqual(token["estimated_incremental_mib"], 4096)
            self.assertEqual(controller.active, 1)
        self.assertEqual(controller.active, 0)
        self.assertGreaterEqual(controller.calls[-1][1]["estimated_vram_mib"], 4096)
        self.assertEqual(len(controller.calls), 2)
        self.assertEqual(controller.released, 2)

    async def test_context_and_layer_bounds_fail_before_inventory_or_admission(self):
        dispatcher, clients, controller = self.make_dispatcher()
        invalid = ({"num_ctx": 0}, {"num_ctx": 8193}, {"num_ctx": True}, {"num_ctx": "4096"},
                   {"num_batch": 513}, {"num_batch": 0}, {"num_batch": False},
                   {"num_gpu": 1.0}, {"num_gpu": True}, {"num_gpu": -2}, {"num_gpu": 100},
                   {"main_gpu": 1}, {"tensor_split": []})
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(GPUAdmissionError) as caught:
                async with dispatcher.lease("fixture", HOST, options=options):
                    self.fail("unsupported resource options admitted")
            self.assertEqual(caught.exception.reason, "unsupported_gpu_options")
        self.assertFalse(clients.created)
        self.assertFalse(controller.calls)

    async def test_continually_evicted_model_stops_after_three_released_grants(self):
        residencies = iter((4096, 3500, 3000, 2500))
        def handler(method, url, kwargs):
            return response({"models": [MODEL] if url.endswith("/api/tags") else
                             [{**MODEL, "size_vram": next(residencies) * MIB}]})
        clients, controller = FakeClients(handler), FakeAdmission()
        dispatcher = OllamaDispatcher(controller, clients)
        with self.assertRaises(GPUAdmissionError) as caught:
            async with dispatcher.lease("fixture", HOST):
                self.fail("unstable residency admitted")
        self.assertEqual(caught.exception.reason, "model_residency_unstable")
        self.assertEqual(len(controller.calls), 3)
        self.assertEqual(controller.released, 3)
        self.assertEqual(controller.active, 0)

    async def test_invalid_residency_bytes_are_not_subtracted_from_cold_budget(self):
        for value in (-1, True, "4096", None):
            with self.subTest(size_vram=value):
                dispatcher, _, _ = self.make_dispatcher([{**MODEL, "size_vram": value}])
                async with dispatcher.lease("fixture", HOST) as token:
                    self.assertEqual(token["estimated_incremental_mib"], token["desired_allocation_mib"])

    async def test_keepalive_is_capped_by_profile_and_bad_bound_releases_lease(self):
        controller = FakeAdmission(keep_alive_s=900)
        dispatcher, _, _ = self.make_dispatcher(controller=controller)
        async with dispatcher.lease("fixture", HOST) as token:
            self.assertEqual(token["keep_alive_s"], 300)
        controller.keep_alive_s = -1
        with self.assertRaises(GPUAdmissionError) as caught:
            async with dispatcher.lease("fixture", HOST):
                self.fail("invalid retention bound admitted")
        self.assertEqual(caught.exception.reason, "invalid_keep_alive_bound")
        self.assertEqual(controller.active, 0)
        self.assertEqual(controller.released, 2)

    async def test_explicit_cpu_needs_no_inventory_or_gpu_admission(self):
        dispatcher, clients, controller = self.make_dispatcher()
        async with dispatcher.lease("fixture", SECONDARY, options={"num_gpu": 0}) as token:
            self.assertFalse(token["gpu_admitted"])
            self.assertEqual(token["execution"], "explicit_cpu")
            self.assertEqual(token["num_ctx"], 4096)
            self.assertEqual(token["num_batch"], 512)
        self.assertFalse(clients.calls)
        self.assertFalse(controller.calls)

    async def test_disabled_controller_preserves_legacy_options_without_gpu_reads(self):
        clients, controller = FakeClients(), FakeAdmission()
        dispatcher = OllamaDispatcher(controller, clients, enabled=False)
        async with dispatcher.lease("fixture", HOST) as token:
            self.assertFalse(token["gpu_admitted"])
            self.assertEqual(token["execution"], "controller_disabled")
            self.assertEqual(token["keep_alive_s"], 300)
            self.assertIsNone(token.get("num_ctx"))
            self.assertIsNone(token.get("num_batch"))
        async with dispatcher.lease("fixture", HOST, options={"num_ctx": 16384, "num_batch": 1024}) as token:
            self.assertEqual(token["num_ctx"], 16384)
            self.assertEqual(token["num_batch"], 1024)
        with self.assertRaises(GPUAdmissionError) as caught:
            async with dispatcher.lease("fixture", "http://example.test:11434"):
                self.fail("disabled gate admitted nonlocal inference")
        self.assertEqual(caught.exception.reason, "local_ollama_endpoint_required")
        self.assertFalse(clients.created)
        self.assertFalse(controller.calls)
        self.assertEqual(controller.snapshot_calls, 0)

    async def test_production_singleton_requires_exact_true_opt_in(self):
        for setting in (None, "false", "TRUE", "true"):
            with self.subTest(setting=setting), patch.dict(os.environ), \
                    patch.object(dispatcher_module, "_dispatcher", None), \
                    patch.object(dispatcher_module, "OllamaDispatcher") as constructor:
                if setting is None:
                    os.environ.pop("AIBS_ADAPTIVE_GPU_ENABLED", None)
                else:
                    os.environ["AIBS_ADAPTIVE_GPU_ENABLED"] = setting
                self.assertIs(dispatcher_module.get_dispatcher(), constructor.return_value)
                self.assertEqual(constructor.call_args.kwargs["enabled"], setting == "true")

    async def test_port_number_alone_does_not_bypass_gpu_admission(self):
        dispatcher, _, controller = self.make_dispatcher()
        async with dispatcher.lease("fixture", SECONDARY) as token:
            self.assertTrue(token["gpu_admitted"])
        self.assertEqual(len(controller.calls), 1)

    async def test_nonlocal_or_credentialed_endpoints_fail_before_any_io(self):
        dispatcher, clients, controller = self.make_dispatcher()
        for host in ("https://127.0.0.1:11434", "http://example.test:11434",
                     "http://user:pass@127.0.0.1:11434", HOST + "/other", HOST + "?q=1"):
            with self.subTest(host=host), self.assertRaises(GPUAdmissionError) as caught:
                async with dispatcher.lease("fixture", host, options={"num_gpu": 0}):
                    self.fail("invalid endpoint admitted")
            self.assertEqual(caught.exception.reason, "local_ollama_endpoint_required")
        self.assertFalse(clients.created)
        self.assertFalse(controller.calls)

    async def test_missing_model_and_denied_admission_do_not_fallback_to_cpu(self):
        dispatcher, _, controller = self.make_dispatcher()
        with self.assertRaises(GPUAdmissionError) as caught:
            async with dispatcher.lease("missing", HOST):
                self.fail("missing model admitted")
        self.assertEqual(caught.exception.reason, "model_not_installed")
        self.assertFalse(controller.calls)
        controller.error = GPUAdmissionError("thermal_limit", retryable=True)
        with self.assertRaises(GPUAdmissionError) as caught:
            async with dispatcher.lease("fixture", HOST):
                self.fail("denied admission bypassed")
        self.assertEqual(caught.exception.reason, "thermal_limit")
        self.assertEqual(len(controller.calls), 1)

    async def test_residency_is_never_reused_across_servers(self):
        def handler(method, url, kwargs):
            return response({"models": [MODEL] if url.endswith("/api/tags") else
                [{**MODEL, "size_vram": MODEL["size"]}] if url.startswith(HOST + "/") else []})
        clients, controller = FakeClients(handler), FakeAdmission()
        dispatcher = OllamaDispatcher(controller, clients)
        async with dispatcher.lease("fixture", HOST):
            pass
        async with dispatcher.lease("fixture", SECONDARY) as token:
            self.assertGreaterEqual(token["estimated_incremental_mib"], 4096)
        self.assertTrue(any(url == SECONDARY + "/api/tags" for _, url, _ in clients.calls))


class RouterIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # The real coding module imports execution/storage dependencies. Never load it here.
        self.coding_module = types.ModuleType("core.coding_chat")
        self.coding_module.coding_request = Mock(return_value=None)
        self.module_patch = patch.dict(sys.modules, {"core.coding_chat": self.coding_module})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.chat = importlib.import_module("routers.chat_router")
        self.real_resolve_model_host = self.chat.resolve_model_host
        self.agent = importlib.import_module("routers.agent_routing")
        self.admission = FakeAdmission()
        for target, value in (("arbitrate_workload", None), ("OLLAMA_HOST_PRIMARY", HOST),
                              ("OLLAMA_HOST_SECONDARY", SECONDARY), ("get_dispatcher", lambda: self.admission),
                              ("resolve_model_host", AsyncMock(return_value=HOST))):
            p = patch.object(self.chat, target, value)
            p.start()
            self.addCleanup(p.stop)

    def patch_clients(self, clients):
        p = patch.object(self.chat.httpx, "AsyncClient", clients)
        p.start()
        self.addCleanup(p.stop)

    def request(self, **kwargs):
        return self.chat.ChatRequest(model="fixture", messages=[self.chat.ChatMessage(role="user", content="synthetic")], **kwargs)

    async def test_coding_short_circuit_keeps_windows_vm_before_gpu_or_http(self):
        expected = {"status": "isolation_unavailable", "execution_backend": "windows_vm"}
        self.coding_module.coding_request.return_value = expected
        clients = FakeClients()
        self.patch_clients(clients)
        request = self.request(mode="coding", execution_backend="windows_vm", plan_only=True)
        result = await self.chat.generate_chat_completion(request)
        self.assertIs(result, expected)
        body = self.coding_module.coding_request.call_args.args[0]
        self.assertEqual(body["execution_backend"], "windows_vm")
        self.assertTrue(body["plan_only"])
        self.chat.resolve_model_host.assert_not_awaited()
        self.assertFalse(self.admission.calls)
        self.assertFalse(clients.created)

    async def test_chat_nonstream_uses_profile_and_direct_loopback_transport(self):
        clients = FakeClients(lambda *args: response({"message": {"content": "ok"}}))
        self.patch_clients(clients)
        result = await self.chat.generate_chat_completion(self.request(stream=False))
        self.assertEqual(result["response"], "ok")
        self.assertEqual(clients.calls[0][2]["json"]["keep_alive"], 120)
        self.assertEqual(clients.calls[0][2]["json"]["options"]["num_ctx"], 4096)
        self.assertEqual(clients.calls[0][2]["json"]["options"]["num_batch"], 512)
        self.assertTrue(all(c.get("trust_env") is False for c in clients.created))
        self.assertEqual(self.admission.released, 1)

    async def test_disabled_chat_preserves_legacy_options_without_inventory_or_telemetry(self):
        inventory = FakeClients()
        disabled = OllamaDispatcher(self.admission, inventory, enabled=False)
        clients = FakeClients(lambda *args: response({"message": {"content": "ok"}}))
        self.patch_clients(clients)
        with patch.object(self.chat, "get_dispatcher", return_value=disabled):
            result = await self.chat.generate_chat_completion(self.request(stream=False))
        self.assertEqual(result["response"], "ok")
        payload = clients.calls[0][2]["json"]
        self.assertEqual(payload["keep_alive"], 300)
        self.assertNotIn("num_ctx", payload["options"])
        self.assertNotIn("num_batch", payload["options"])
        self.assertFalse(inventory.created)
        self.assertFalse(self.admission.calls)
        self.assertEqual(self.admission.snapshot_calls, 0)

    async def test_chat_http_admission_error_is_503_without_inference(self):
        self.admission.error = GPUAdmissionError("vram_pressure", retryable=True)
        clients = FakeClients()
        self.patch_clients(clients)
        with self.assertRaises(HTTPException) as caught:
            await self.chat.generate_chat_completion(self.request(stream=False))
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.detail, {"code": "vram_pressure"})
        self.assertFalse(clients.calls)

    async def test_chat_stream_reports_denial_and_releases_nothing_unacquired(self):
        self.admission.error = GPUAdmissionError("thermal_limit")
        clients = FakeClients()
        self.patch_clients(clients)
        result = await self.chat.generate_chat_completion(self.request(stream=True))
        chunks = [chunk async for chunk in result.body_iterator]
        self.assertEqual(len(chunks), 1)
        self.assertIn('"code": "GPU_ADMISSION_DENIED"', chunks[0])
        self.assertIn("thermal_limit", chunks[0])
        self.assertEqual(self.admission.active, 0)
        self.assertEqual(self.admission.released, 0)
        self.assertFalse(clients.calls)

    async def test_sse_cancel_closes_client_stream_and_lease(self):
        stream = FakeStream(['{"message":{"content":"first"},"done":false}'], block=True)
        clients = FakeClients(stream_response=stream)
        self.patch_clients(clients)
        result = await self.chat.generate_chat_completion(self.request(stream=True))
        iterator = result.body_iterator
        self.assertIn("first", await anext(iterator))
        self.assertEqual(self.admission.active, 1)
        waiting = asyncio.create_task(anext(iterator))
        await asyncio.wait_for(stream.waiting.wait(), timeout=1)
        waiting.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiting
        self.assertEqual(self.admission.active, 0)
        self.assertEqual(self.admission.released, 1)
        self.assertEqual(clients.open_clients, 0)
        self.assertEqual(clients.open_streams, 0)
        self.assertEqual(clients.calls[0][2]["json"]["keep_alive"], 120)
        self.assertEqual(clients.calls[0][2]["json"]["options"]["num_ctx"], 4096)
        self.assertEqual(clients.calls[0][2]["json"]["options"]["num_batch"], 512)
        self.assertTrue(all(c.get("trust_env") is False for c in clients.created))

    async def test_sse_done_and_early_close_both_release_lease(self):
        for early in (False, True):
            with self.subTest(early_close=early):
                stream = FakeStream(['{"message":{"content":"first"},"done":false}',
                                     '{"message":{"content":""},"done":true}'])
                clients = FakeClients(stream_response=stream)
                self.patch_clients(clients)
                result = await self.chat.generate_chat_completion(self.request(stream=True))
                if early:
                    await anext(result.body_iterator)
                    await result.body_iterator.aclose()
                else:
                    chunks = [chunk async for chunk in result.body_iterator]
                    self.assertIn('"done": true', chunks[-1])
                self.assertEqual(self.admission.active, 0)
                self.assertEqual(clients.open_clients, 0)
                self.assertEqual(clients.open_streams, 0)
        self.assertEqual(self.admission.released, 2)

    async def test_embeddings_preserve_order_with_cpu_then_admitted_gpu_fallback(self):
        documents = ["doc-" + str(index) for index in range(10)]
        def handler(method, url, kwargs):
            payload = kwargs["json"]
            if url.startswith(SECONDARY):
                self.assertEqual(payload["options"]["num_gpu"], 0)
                if payload["input"][0] == "doc-0":
                    raise httpx.ConnectError("synthetic CPU unavailable")
            else:
                self.assertEqual(self.admission.active, 1)
                self.assertNotEqual(payload.get("options", {}).get("num_gpu"), 0)
                self.assertEqual(payload["keep_alive"], 120)
                self.assertEqual(payload["options"]["num_ctx"], 4096)
                self.assertEqual(payload["options"]["num_batch"], 512)
            return response({"embeddings": [[int(doc.split("-")[1])] for doc in payload["input"]],
                             "total_duration": len(payload["input"]), "prompt_eval_count": len(payload["input"])})
        clients = FakeClients(handler)
        self.patch_clients(clients)
        result = await self.chat.generate_embedding(self.chat.EmbedRequest(model="fixture", input=documents))
        self.assertEqual(result["embeddings"], [[index] for index in range(10)])
        self.assertEqual(result["prompt_eval_count"], 10)
        self.assertEqual(len(self.admission.calls), 1)
        self.assertEqual(self.admission.calls[0][1]["workload"], "embeddings")
        self.assertEqual([len(call[2]["json"]["input"]) for call in clients.calls], [8, 8, 2])
        self.assertTrue(all(c.get("trust_env") is False for c in clients.created))
        self.assertEqual(self.admission.active, 0)

    async def test_metadata_and_cpu_embeddings_refuse_invalid_configured_hosts_before_io(self):
        clients = FakeClients()
        self.patch_clients(clients)
        for setting in ("OLLAMA_HOST_PRIMARY", "OLLAMA_HOST_SECONDARY"):
            for endpoint in ("http://example.test:11434", "https://127.0.0.1:11434",
                             "http://user:secret@127.0.0.1:11434"):
                for enabled in (False, True):
                    with self.subTest(setting=setting, endpoint=endpoint, enabled=enabled):
                        self.admission.enabled = enabled
                        with patch.object(self.chat, setting, endpoint):
                            operations = [lambda: self.real_resolve_model_host("fixture"),
                                          self.chat.get_available_models,
                                          lambda: self.chat.generate_embedding(
                                              self.chat.EmbedRequest(input=["synthetic private input"]))]
                            for operation in operations:
                                with self.assertRaises(HTTPException) as caught:
                                    await operation()
                                self.assertEqual(caught.exception.status_code, 503)
                                self.assertEqual(caught.exception.detail,
                                                 {"code": "local_ollama_endpoint_required"})
                        self.assertFalse(clients.created)
                        self.assertFalse(clients.calls)
                        self.assertFalse(self.admission.calls)
                        self.assertEqual(self.admission.snapshot_calls, 0)

    async def test_embedding_count_mismatch_fails_without_partial_success(self):
        clients = FakeClients(lambda *args: response({"embeddings": []}))
        self.patch_clients(clients)
        with self.assertRaises(HTTPException) as caught:
            await self.chat.generate_embedding(self.chat.EmbedRequest(model="fixture", input=["one", "two"]))
        self.assertEqual(caught.exception.status_code, 502)
        self.assertFalse(self.admission.calls)

    async def test_disabled_embedding_route_uses_fixed_batches_without_telemetry(self):
        inventory = FakeClients()
        disabled = OllamaDispatcher(self.admission, inventory, enabled=False)
        clients = FakeClients(lambda method, url, kwargs: response({
            "embeddings": [[value] for value in kwargs["json"]["input"]]}))
        self.patch_clients(clients)
        documents = [str(index) for index in range(10)]
        with patch.object(self.chat, "get_dispatcher", return_value=disabled):
            result = await self.chat.generate_embedding(self.chat.EmbedRequest(model="fixture", input=documents))
        self.assertEqual(result["embeddings"], [[value] for value in documents])
        self.assertEqual([len(call[2]["json"]["input"]) for call in clients.calls], [8, 2])
        self.assertTrue(all(call[1].startswith(SECONDARY) for call in clients.calls))
        self.assertFalse(inventory.created)
        self.assertFalse(self.admission.calls)
        self.assertEqual(self.admission.snapshot_calls, 0)

    async def test_agent_fallback_has_its_own_admission_and_profile_keepalive(self):
        def handler(method, url, kwargs):
            self.assertEqual(self.admission.active, 1)
            return response({"message": {"content": "fallback"}}, 500 if kwargs["json"]["model"] == "first" else 200)
        clients = FakeClients(handler)
        self.patch_clients(clients)
        with patch.object(self.agent, "get_dispatcher", return_value=self.admission), patch.object(self.agent, "OLLAMA_URL", HOST):
            result = await self.agent.call_ollama("first", "second", "system", "synthetic", .5, .9)
        self.assertEqual(result["model_used"], "second")
        self.assertEqual([args[0] for args, _ in self.admission.calls], ["first", "second"])
        self.assertEqual(self.admission.released, 2)
        self.assertTrue(all(c.get("trust_env") is False for c in clients.created))
        self.assertTrue(all(call[2]["json"]["keep_alive"] == 120 for call in clients.calls))
        self.assertTrue(all(call[2]["json"]["options"]["num_ctx"] == 4096 for call in clients.calls))
        self.assertTrue(all(call[2]["json"]["options"]["num_batch"] == 512 for call in clients.calls))


if __name__ == "__main__":
    unittest.main()
