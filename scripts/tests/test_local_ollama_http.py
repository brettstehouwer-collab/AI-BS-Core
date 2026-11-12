"""Offline loopback client contracts; no GPU, model, or network execution."""
import asyncio
import importlib
from pathlib import Path
import ssl
import sys
import threading
import unittest
from unittest.mock import Mock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from gpu.compute_scheduler import GPUAdmissionError


class LocalOllamaHTTPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = importlib.import_module("core.local_ollama_http")

    def test_invalid_origin_fails_before_client_construction(self):
        invalid = (None, 123, "http://example.test:11434", "https://127.0.0.1:11434",
                   "http://127.0.0.1.example.test:11434", "http://127.0.0.2:11434",
                   "http://user:secret@127.0.0.1:11434", "http://@localhost:11434",
                   "http://:@localhost:11434", "http://localhost:99999",
                   "http://localhost:not-a-port", "http://localhost/api/chat",
                   "http://localhost?query=1", "http://localhost#fragment")
        constructor = Mock()
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(GPUAdmissionError) as caught:
                    self.module.local_ollama_client(endpoint, timeout=3, client_factory=constructor)
                self.assertEqual(caught.exception.reason, "local_ollama_endpoint_required")
        with self.assertRaises(GPUAdmissionError):
            self.module.local_ollama_client("http://127.0.0.1:11434", invalid[2],
                                            timeout=3, client_factory=constructor)
        with self.assertRaises(GPUAdmissionError):
            self.module.local_ollama_client(timeout=3, client_factory=constructor)
        constructor.assert_not_called()

    def test_local_origins_share_checked_tls_context_and_preserve_timeouts(self):
        constructor = Mock()
        timeout = httpx.Timeout(5400, connect=15, read=5400, write=30)
        contexts = []
        for endpoint in ("http://127.0.0.1:11434", "http://localhost:11435/", "http://[::1]:11434"):
            result = self.module.local_ollama_client(endpoint, timeout=timeout, client_factory=constructor)
            self.assertIs(result, constructor.return_value)
            kwargs = constructor.call_args.kwargs
            self.assertIs(kwargs["timeout"], timeout)
            self.assertIs(kwargs["trust_env"], False)
            context = kwargs["verify"]
            self.assertIsInstance(context, ssl.SSLContext)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            contexts.append(context)
        self.assertTrue(all(context is contexts[0] for context in contexts))

    async def test_real_clients_do_not_load_default_ca_store(self):
        # HTTPX construction alone must not incur the Windows CA-store scan.
        with patch.object(ssl, "create_default_context", side_effect=AssertionError("unexpected CA load")):
            async with self.module.local_ollama_client("http://127.0.0.1:11434", timeout=3):
                pass

    async def test_request_guard_rejects_remote_https_and_credentials_before_transport(self):
        requests = []
        async def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"models": []})
        def constructor(**kwargs):
            return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)
        async with self.module.local_ollama_client("http://127.0.0.1:11434", timeout=3,
                                                   client_factory=constructor) as client:
            for endpoint in ("http://example.test/api/tags", "https://127.0.0.1/api/tags",
                             "http://user:secret@localhost/api/tags"):
                with self.subTest(endpoint=endpoint), self.assertRaises(GPUAdmissionError):
                    await client.get(endpoint)
            result = await client.get("http://127.0.0.1:11434/api/tags")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(requests), 1)

    def test_dispatcher_validator_export_preserves_shared_contract(self):
        from orchestrator.gpu_task_dispatcher import _LOCAL_HTTP_CONTEXT, local_ollama_host
        self.assertIs(local_ollama_host, self.module.local_ollama_host)
        self.assertIs(_LOCAL_HTTP_CONTEXT, self.module._LOCAL_HTTP_CONTEXT)


class LocalOllamaRouterTests(unittest.IsolatedAsyncioTestCase):
    # Reuse only the offline setup helpers, not their already-covered test cases.
    from scripts.tests import test_gpu_dispatcher_integration as fixtures
    setUp = fixtures.RouterIntegrationTests.setUp
    patch_clients = fixtures.RouterIntegrationTests.patch_clients
    request = fixtures.RouterIntegrationTests.request

    async def test_metadata_embedding_chat_and_agent_clients_use_shared_context(self):
        fixture = self.fixtures
        local = importlib.import_module("core.local_ollama_http")
        def handler(method, url, kwargs):
            if url.endswith("/api/tags"):
                return fixture.response({"models": [fixture.MODEL]})
            if url.endswith("/api/embed"):
                return fixture.response({"embeddings": [[1] for _ in kwargs["json"]["input"]]})
            return fixture.response({"message": {"content": "ok"}})
        operations = (
            (lambda: self.real_resolve_model_host("fixture"), (2, 1, 2, 2)),
            (self.chat.get_available_models, (2, 1, 2, 2)),
            (lambda: self.chat.generate_embedding(self.chat.EmbedRequest(input=["synthetic"])), (60, 5, 60, 60)),
            (lambda: self.chat.generate_chat_completion(self.request(stream=False)), (5400, 15, 5400, 30)),
            (lambda: self.chat.generate_chat_completion(self.request(stream=True)), (5400, 15, 5400, 30)),
            (lambda: self.agent.call_ollama("fixture", "fallback", "system", "synthetic", .5, .9), (60, 60, 60, 60)),
        )
        with patch.object(self.agent, "get_dispatcher", return_value=self.admission), \
                patch.object(self.agent, "OLLAMA_URL", fixture.HOST):
            for operation, expected in operations:
                clients = fixture.FakeClients(handler, fixture.FakeStream(['{"done":true}']))
                with patch.object(httpx, "AsyncClient", clients):
                    result = await operation()
                    if hasattr(result, "body_iterator"):
                        _ = [chunk async for chunk in result.body_iterator]
                self.assertTrue(clients.created)
                for kwargs in clients.created:
                    self.assertIs(kwargs["verify"], local._LOCAL_HTTP_CONTEXT)
                    self.assertIs(kwargs["trust_env"], False)
                    timeout = kwargs["timeout"]
                    observed = ((timeout.read, timeout.connect, timeout.pool, timeout.write)
                                if isinstance(timeout, httpx.Timeout) else (timeout,) * 4)
                    self.assertEqual(observed, expected)
                self.assertEqual(clients.open_clients, 0)
                self.assertEqual(clients.open_streams, 0)

    async def test_invalid_agent_origin_is_503_before_client_or_admission(self):
        from fastapi import HTTPException
        clients = self.fixtures.FakeClients()
        with patch.object(httpx, "AsyncClient", clients), \
                patch.object(self.agent, "get_dispatcher", return_value=self.admission):
            for endpoint in ("http://example.test:11434", "https://127.0.0.1:11434",
                             "http://user:secret@127.0.0.1:11434"):
                with self.subTest(endpoint=endpoint), patch.object(self.agent, "OLLAMA_URL", endpoint):
                    with self.assertRaises(HTTPException) as caught:
                        await self.agent.call_ollama("fixture", "fallback", "system", "synthetic", .5, .9)
                    self.assertEqual(caught.exception.status_code, 503)
                    self.assertEqual(caught.exception.detail, {"code": "local_ollama_endpoint_required"})
        self.assertFalse(clients.created)
        self.assertFalse(self.admission.calls)

    async def test_blocked_arbiter_allows_event_loop_progress_and_preserves_plan(self):
        fixture = self.fixtures
        entered, release, progressed = threading.Event(), threading.Event(), threading.Event()
        finished = threading.Event()
        def probe(model, *, task_type):
            self.assertEqual((model, task_type), ("fixture", "chat"))
            entered.set()
            release.wait(.3)
            finished.set()
            return {"host": fixture.HOST, "num_gpu": 7}
        async def heartbeat():
            while not entered.is_set():
                await asyncio.sleep(0)
            if not finished.is_set():
                progressed.set()
            release.set()
        clients = fixture.FakeClients(lambda *args: fixture.response({"message": {"content": "ok"}}))
        self.patch_clients(clients)
        pulse = asyncio.create_task(heartbeat())
        try:
            with patch.object(self.chat, "arbitrate_workload", probe):
                result = await self.chat.generate_chat_completion(self.request(stream=False))
            await asyncio.wait_for(pulse, timeout=1)
        finally:
            release.set()
            if not pulse.done():
                pulse.cancel()
        self.assertTrue(progressed.is_set(), "synchronous arbiter blocked event-loop progress")
        self.assertEqual(result["response"], "ok")
        self.assertEqual(clients.calls[0][2]["json"]["options"]["num_gpu"], 7)


if __name__ == "__main__":
    unittest.main()
