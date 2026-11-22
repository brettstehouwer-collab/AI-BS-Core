"""Offline provider gateway tests: fixture credentials and mocked HTTP only.

No real environment files, provider configuration, credentials, or API calls are
used. The actual router and host admission guard run against in-memory fixtures.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
ENV_KEY = "ENV_ONLY_PRIVATE_credential-987654"
ADMIN_KEY = "fixture-local-administrator"


def load_source(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ProviderEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        sys.path.insert(0, str(ROOT / "backend"))
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self.original_path))
        auth = types.ModuleType("security.firebase_auth")
        auth.get_admin_principal = lambda key, authorization: "fixture-admin" if key == ADMIN_KEY else None
        modules = patch.dict(sys.modules, {"security.firebase_auth": auth})
        modules.start()
        self.addCleanup(modules.stop)
        load_source("backend/security/host_control_access.py", "security.host_control_access")
        self.module = load_source("backend/routers/ai_providers_router.py", "fixture_ai_provider_environment")
        env = patch.dict(os.environ, {"OPENAI_API_KEY": ENV_KEY})
        env.start()
        self.addCleanup(env.stop)
        self.cfg = {"active_provider": "local", "providers": {
            "local": {"model": "fixture-local-model"}, "openai": {"api_key": ""}}}
        configuration = patch.object(self.module, "load_config", side_effect=lambda: copy.deepcopy(self.cfg))
        configuration.start()
        self.addCleanup(configuration.stop)
        saved = patch.object(self.module, "save_config")
        self.save = saved.start()
        self.addCleanup(saved.stop)
        self.outbound = []
        self.reply = None
        real_client = httpx.AsyncClient

        def handle(request):
            self.outbound.append(request)
            if self.reply:
                return self.reply(request)
            if request.method == "GET":
                return httpx.Response(200, json={"data": []})
            return httpx.Response(200, json={"choices": [{"message": {"content": "fixture response"}}]})

        def client(**kwargs):
            kwargs.setdefault("trust_env", False)
            return real_client(transport=httpx.MockTransport(handle), **kwargs)

        network = patch.object(self.module.httpx, "AsyncClient", side_effect=client)
        network.start()
        self.addCleanup(network.stop)
        app = FastAPI()
        app.include_router(self.module.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.headers = {"X-Admin-Key": ADMIN_KEY}

    def provider(self, provider="openai"):
        response = self.client.get("/api/ai/providers", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        return next(item for item in response.json()["providers"] if item["id"] == provider)

    def generate(self, payload=None, headers=None):
        return self.client.post("/api/ai/generate", headers={**self.headers, **(headers or {})},
                                json={"provider": "openai", "prompt": "fixture prompt", **(payload or {})})

    def test_environment_listing_has_generic_marker_and_keeps_local_active(self):
        response = self.client.get("/api/ai/providers", headers=self.headers)
        data = response.json()
        self.assertEqual(data["active_provider"], "local")
        provider = next(item for item in data["providers"] if item["id"] == "openai")
        self.assertTrue(provider["is_configured"])
        self.assertEqual(provider["credential_source"], "environment")
        self.assertEqual(provider["masked_key"], "***")
        self.assertEqual(provider["saved_model"], "gpt-4.1-mini")
        self.assertIn("gpt-4.1-mini", provider["models"])
        for secret in (ENV_KEY, ENV_KEY[:6], ENV_KEY[-4:]):
            self.assertNotIn(secret, response.text)
        self.assertEqual(self.outbound, [])
        self.save.assert_not_called()

    def test_saved_credential_and_model_take_precedence(self):
        self.cfg["providers"]["openai"] = {"api_key": "fixture-saved-key", "model": "gpt-4o"}
        provider = self.provider()
        self.assertEqual(provider["credential_source"], "saved")
        self.assertEqual(provider["saved_model"], "gpt-4o")
        response = self.generate()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.outbound[-1].headers["authorization"], "Bearer fixture-saved-key")
        self.assertEqual(json.loads(self.outbound[-1].content)["model"], "gpt-4o")

    def test_generation_credential_precedence_body_header_saved_environment(self):
        cases = [
            ({"api_key": "fixture-body-key"}, {"X-AI-Key": "fixture-header-key"}, "fixture-saved-key", "fixture-body-key"),
            ({}, {"X-AI-Key": "fixture-header-key"}, "fixture-saved-key", "fixture-header-key"),
            ({}, {}, "fixture-saved-key", "fixture-saved-key"),
            ({}, {}, "", ENV_KEY),
        ]
        for payload, headers, saved, expected in cases:
            with self.subTest(expected=expected):
                self.cfg["providers"]["openai"]["api_key"] = saved
                self.assertEqual(self.generate(payload, headers).status_code, 200)
                self.assertEqual(self.outbound[-1].headers["authorization"], "Bearer " + expected)
        self.save.assert_not_called()

    def test_generation_environment_fallback_and_explicit_model_payload(self):
        response = self.generate({"model": "gpt-4o", "max_tokens": 17, "temperature": 0.2})
        self.assertEqual(response.json(), {"provider": "openai", "model": "gpt-4o", "content": "fixture response"})
        request = self.outbound[-1]
        self.assertEqual(str(request.url), "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer " + ENV_KEY)
        payload = json.loads(request.content)
        self.assertEqual(payload["max_tokens"], 17)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": "fixture prompt"})

    def test_omitted_blank_and_masked_validation_keys_use_server_environment(self):
        for value in (None, "", "  ", "***", "fixtur...7654"):
            with self.subTest(value=value):
                payload = {"provider": "openai"}
                if value is not None:
                    payload["api_key"] = value
                response = self.client.post("/api/ai/validate-key", headers=self.headers, json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "valid")
                self.assertEqual(self.outbound[-1].headers["authorization"], "Bearer " + ENV_KEY)
                self.assertEqual(str(self.outbound[-1].url), "https://api.openai.com/v1/models")

    def test_validation_uses_body_then_header_then_saved_credentials(self):
        self.cfg["providers"]["openai"]["api_key"] = "fixture-saved-key"
        for payload, headers, expected in (
            ({"api_key": "fixture-body-key"}, {"X-AI-Key": "fixture-header-key"}, "fixture-body-key"),
            ({}, {"X-AI-Key": "fixture-header-key"}, "fixture-header-key"),
            ({"api_key": "***"}, {}, "fixture-saved-key"),
        ):
            response = self.client.post("/api/ai/validate-key", headers={**self.headers, **headers},
                                        json={"provider": "openai", **payload})
            self.assertEqual(response.json()["status"], "valid")
            self.assertEqual(self.outbound[-1].headers["authorization"], "Bearer " + expected)

    def test_model_validation_distinguishes_authentication_from_model_access(self):
        self.reply = lambda request: httpx.Response(200, json={'data': [{'id': 'gpt-4.1-mini'}]})
        response = self.client.post('/api/ai/validate-key', headers=self.headers,
            json={'provider': 'openai', 'model': 'o1'})
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertTrue(data['authenticated'])
        self.assertFalse(data['model_available'])
        self.assertFalse(data['generation_verified'])
        self.assertEqual(data['models'], ['gpt-4.1-mini'])
        self.assertEqual(len(self.outbound), 1)
        self.assertEqual(self.outbound[0].method, 'GET')
        self.save.assert_not_called()

    def test_listed_supported_model_validation_never_claims_generation(self):
        self.reply = lambda request: httpx.Response(200, json={'data': [{'id': 'gpt-4.1-mini'}, {'id': 'custom-fixture'}]})
        for model, status in (('gpt-4.1-mini', 'valid'), ('custom-fixture', 'error')):
            with self.subTest(model=model):
                response = self.client.post('/api/ai/validate-key', headers=self.headers,
                    json={'provider': 'openai', 'model': model})
                data = response.json()
                self.assertEqual(data['status'], status)
                self.assertTrue(data['model_available'])
                self.assertEqual(data['model_supported'], model == 'gpt-4.1-mini')
                self.assertFalse(data['generation_verified'])
        self.assertTrue(all(request.method == 'GET' for request in self.outbound))

    def test_missing_environment_credential_fails_before_network(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.assertFalse(self.provider()["is_configured"])
            self.assertEqual(self.generate().status_code, 401)
            response = self.client.post("/api/ai/validate-key", headers=self.headers, json={"provider": "openai"})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.outbound, [])

    def test_masked_openai_generation_and_save_never_store_environment_key(self):
        self.assertEqual(self.generate({"api_key": "***"}).status_code, 200)
        response = self.client.post("/api/ai/config", headers=self.headers, json={"providers": {
            "openai": {"api_key": "***", "model": "gpt-4.1-mini"}}})
        self.assertEqual(response.status_code, 200)
        stored = self.save.call_args.args[0]
        self.assertEqual(stored["providers"]["openai"]["api_key"], "")
        self.assertNotIn(ENV_KEY, json.dumps(stored))
        self.cfg["providers"]["openai"]["api_key"] = "fixture-saved-key"
        response = self.client.post("/api/ai/config", headers=self.headers, json={"providers": {
            "openai": {"api_key": "fixtur...-key"}}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.save.call_args.args[0]["providers"]["openai"]["api_key"], "fixture-saved-key")

    def test_authentication_errors_do_not_expose_response_body_or_credentials(self):
        self.reply = lambda request: httpx.Response(401, text="private failure " + ENV_KEY)
        response = self.client.post("/api/ai/validate-key", headers=self.headers, json={"provider": "openai"})
        self.assertEqual(response.json()["status"], "error")
        self.assertNotIn("private failure", response.text)
        self.assertNotIn(ENV_KEY, response.text)

    def test_validation_transport_errors_are_sanitized(self):
        def fail(request):
            raise httpx.ConnectError("private transport " + ENV_KEY, request=request)
        self.reply = fail
        response = self.client.post("/api/ai/validate-key", headers=self.headers, json={"provider": "openai"})
        self.assertEqual(response.json()["status"], "error")
        self.assertNotIn("private transport", response.text)
        self.assertNotIn(ENV_KEY, response.text)

    def test_generation_http_and_transport_errors_are_sanitized(self):
        def fail(request):
            raise httpx.ConnectError("private transport " + ENV_KEY, request=request)
        for reply in (lambda request: httpx.Response(429, text="private failure " + ENV_KEY), fail):
            self.reply = reply
            response = self.generate()
            self.assertEqual(response.status_code, 502)
            for secret in (ENV_KEY, "private failure", "private transport"):
                self.assertNotIn(secret, response.text)

    def test_admin_admission_precedes_request_body_and_configuration_access(self):
        for path in ("/api/ai/config", "/api/ai/validate-key", "/api/ai/generate"):
            response = self.client.post(path, content="invalid json", headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(self.client.get("/api/ai/providers").status_code, 403)
        self.module.load_config.assert_not_called()
        self.save.assert_not_called()
        self.assertEqual(self.outbound, [])

    def test_local_provider_selection_and_payload_remain_local(self):
        self.reply = lambda request: httpx.Response(200, json={"message": {"content": "fixture local"}})
        response = self.client.post("/api/ai/generate", headers=self.headers, json={"prompt": "fixture prompt"})
        self.assertEqual(response.json(), {"provider": "local", "model": "fixture-local-model", "content": "fixture local"})
        self.assertEqual(str(self.outbound[-1].url), "http://127.0.0.1:11434/api/chat")
        self.assertNotIn("authorization", self.outbound[-1].headers)


if __name__ == "__main__":
    unittest.main()
