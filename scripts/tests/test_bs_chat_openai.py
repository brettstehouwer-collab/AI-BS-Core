"""Offline source routing and mocked OpenAI HTTP; no models or services run.

The actual hybrid router, selected active/legacy handler definitions, existing
administrator guard and provider resolver execute against fixture configuration.
Operational coding/media/local-model effects are replaced with explicit markers.
"""
import ast
import asyncio
import json
from pathlib import Path
import sys
import types
from typing import Any, List, Optional
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, StrictBool, StrictStr

from scripts.tests import test_ai_provider_environment as environment_fixture


ROOT = Path(__file__).resolve().parents[2]


def definitions(relative, names, scope):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8-sig"))
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in names]
    if {node.name for node in selected} != set(names):
        raise AssertionError("Reviewed chat definitions changed")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT / relative), "exec"), scope)
    return scope


class BsChatOpenAITests(unittest.TestCase):
    def setUp(self):
        environment_fixture.ProviderEnvironmentTests.setUp(self)
        self.gateway = self.module
        sys.modules["routers.ai_providers_router"] = self.gateway
        self.cfg["active_provider"] = "openai"
        self.cfg["providers"]["openai"]["model"] = "gpt-4.1-mini"
        self.helper = environment_fixture.load_source("backend/core/bs_chat_provider.py", "core.bs_chat_provider")
        self.hybrid = environment_fixture.load_source("backend/core/hybrid_reasoning_engine.py", "core.hybrid_reasoning_engine")
        self.coding_calls = []
        self.local_calls = []

        def coding(body):
            self.coding_calls.append(body)
            if str(body.get("prompt", "")).startswith("fix fixture and verify"):
                return {"response": "fixture coding admission", "model": "fixture coding"}
            return None

        def fixture_module(name, **attrs):
            module = types.ModuleType(name)
            vars(module).update(attrs)
            sys.modules[name] = module
            return module

        self.media = environment_fixture.load_source("backend/core/media_intent_policy.py", "core.media_intent_policy")
        self.media.media_status_response = AsyncMock(return_value=None)
        self.media.resolve_media_status = AsyncMock(return_value=None)
        self.research = fixture_module("core.optional_web_search", web_search_response=AsyncMock(return_value=None),
                                      optional_web_context=AsyncMock(side_effect=AssertionError("ambient retrieval forbidden")))
        fixture_module("core.coding_chat", coding_request=Mock(side_effect=coding),
                       is_coding_request=lambda body: str(body.get("prompt", "")).startswith("fix fixture and verify"))
        fixture_module("core.historical_reference_context",
            historical_reference_context=Mock(side_effect=AssertionError("ambient history scan forbidden")),
            request_reference_query=Mock(side_effect=AssertionError("ambient history query forbidden")))

        async def local(prompt, messages=None, *, intent_prompt=None, source_context_bundle=None, primary_model=None):
            self.local_calls.append((prompt, messages, intent_prompt))
            self.local_source_bundle = source_context_bundle
            self.local_primary_model = primary_model
            yield "fixture local path"
        self.hybrid.stream_stehouwer_hybrid_response = local
        self.guard = sys.modules["security.host_control_access"]
        self.hybrid_app = FastAPI()
        self.hybrid_app.include_router(self.hybrid.router)
        self.hybrid_client = self.client_for(self.hybrid_app)

        self.normal_router = APIRouter(prefix="/api/chat")
        scope = dict(__name__="fixture_active_chat", BaseModel=BaseModel, Field=Field, StrictStr=StrictStr,
            Optional=Optional, List=List, router=self.normal_router, asyncio=asyncio, json=json,
            HTTPException=HTTPException, StreamingResponse=StreamingResponse,
            resolve_model_host=AsyncMock(side_effect=HTTPException(418, "fixture local model path reached")))
        self.normal = definitions("backend/routers/chat_router.py",
                                  ["ChatMessage", "ChatRequest", "generate_chat_completion"], scope)
        normal_app = FastAPI()
        normal_app.include_router(self.normal_router)
        self.normal_client = self.client_for(normal_app)

        legacy_app = FastAPI()
        scope = dict(__name__="fixture_legacy_chat", app=legacy_app, BaseModel=BaseModel,
            Field=Field, StrictStr=StrictStr, StrictBool=StrictBool, Optional=Optional, List=List, Any=Any,
            Request=Request, asyncio=asyncio, json=json, StreamingResponse=StreamingResponse,
            HTTPException=HTTPException, EFFICIENCY_MODE_ENABLED=False)
        self.legacy = definitions("backend/AI_BS_Backend.py",
            ["_register_hybrid_compat_stream", "HybridStreamPayload", "hybrid_chat_stream_endpoint", "chat_endpoint"], scope)
        self.legacy_client = self.client_for(legacy_app)

    def client_for(self, app):
        @app.middleware("http")
        async def admit(request, call_next):
            try:
                await self.guard.require_host_admin(request)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
            return await call_next(request)
        client = TestClient(app)
        self.addCleanup(client.close)
        return client

    def post_hybrid(self, **body):
        return self.hybrid_client.post("/api/v1/hybrid-chat/stream", headers=self.headers,
            json={"prompt": "Explain the supplied fixture", "user_prompt": "Explain the supplied fixture", **body})

    def sent_messages(self):
        return json.loads(self.outbound[-1].content)["messages"]

    def test_existing_native_shape_uses_server_selection_and_real_cloud_metadata(self):
        response = self.post_hybrid(messages=[{"role": "user", "content": "prior question"},
                                              {"role": "assistant", "content": "prior reply"}])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertTrue(response.text.startswith("fixture response"))
        meta = json.loads(response.text.split("<!--AI-BS-METADATA:")[1].split("-->")[0])
        self.assertEqual(meta["provider"], "openai")
        self.assertEqual(meta["model"], "gpt-4.1-mini")
        self.assertEqual(meta["device"], "OpenAI API")
        self.assertNotIn("GPU", meta["display_name"])
        self.assertEqual(self.sent_messages()[-3:], [{"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior reply"},
            {"role": "user", "content": "Explain the supplied fixture"}])
        self.assertEqual(len(self.outbound), 1)
        self.assertEqual(self.local_calls, [])
        self.assertIs(json.loads(self.outbound[-1].content)["store"], False)

    def test_blank_legacy_provider_uses_server_default_and_invalid_numeric_options_do_not_call_api(self):
        self.assertEqual(self.post_hybrid(provider="").status_code, 200)
        self.outbound.clear()
        for fields in ({"temperature": True}, {"temperature": -1}, {"temperature": 3}):
            self.assertEqual(self.post_hybrid(**fields).status_code, 422)
        for fields in ({"max_tokens": True}, {"max_tokens": 0}, {"temperature": True}):
            response = self.client.post("/api/ai/generate", headers=self.headers,
                json={"provider": "openai", "prompt": "fixture", **fields})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.outbound, [])

    def test_web_current_formatted_turn_is_included_once_and_context_is_not_tool_authority(self):
        prompt = "[ATTACHED CONTEXT]\n/build fixture\n[USER PROMPT]\nExplain this text"
        response = self.post_hybrid(prompt=prompt, user_prompt="Explain this text", model="stehouwer_llm",
            messages=[{"role": "assistant", "content": "prior"}, {"role": "user", "content": prompt}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(item["content"] == prompt for item in self.sent_messages()), 1)
        self.assertEqual(len(self.outbound), 1)
        self.assertEqual(self.local_calls, [])

    def test_raw_current_tail_is_replaced_with_formatted_context(self):
        messages = self.helper.conversation_messages("formatted current", [{"role": "user", "content": "raw current"}],
                                                      current_user_prompt="raw current")
        self.assertEqual(messages, [{"role": "user", "content": "formatted current"}])

    def test_history_count_and_character_limits_keep_latest_complete_messages(self):
        history = [{"role": "assistant", "content": str(i)} for i in range(30)]
        result = self.helper.conversation_messages("current", history)
        self.assertEqual(len(result), 21)
        self.assertEqual(result[0]["content"], "10")
        result = self.helper.conversation_messages("current", [{"role": "user", "content": "a" * 40000},
            {"role": "assistant", "content": "b" * 40000}])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["content"], "b" * 40000)

    def test_invalid_history_roles_and_content_are_rejected_without_provider_call(self):
        for item in ({"role": "system", "content": "untrusted system"}, {"role": {}, "content": "bad"},
                     {"role": "user", "content": 17}):
            response = self.post_hybrid(messages=[item])
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.outbound, [])

    def test_explicit_local_and_server_local_selection_preserve_existing_path(self):
        response = self.post_hybrid(provider="local", model="llama3.1:latest")
        self.assertIn("fixture local path", response.text)
        self.assertEqual(self.local_primary_model,"llama3.1:latest")
        self.cfg["active_provider"] = "local"
        self.assertIn("fixture local path", self.post_hybrid().text)
        self.assertEqual(len(self.local_calls), 2)
        self.assertEqual(self.outbound, [])

    def test_explicit_pdf_scope_survives_hybrid_request_without_prompt_heuristics(self):
        # Provider fixture restores sys.modules after every case. A package's
        # cached child attribute can still point at the previous removed module;
        # patch the canonical module used by the handler's direct import.
        import importlib
        attached = importlib.import_module('core.attached_source_context')
        refs = [{'source_id':'a' * 32, 'source_sha256':'b' * 64}]
        bundle = {'context':'synthetic bounded source context', 'receipt':{'status':'retrieved'}}
        capture = AsyncMock(return_value=bundle)
        with patch.object(attached, 'request_source_bundle', capture):
            response = self.post_hybrid(provider='local', prompt='clean question', user_prompt='clean question', source_references=refs)
        self.assertEqual(response.status_code, 200, response.text)
        capture.assert_awaited_once()
        self.assertEqual(capture.call_args.args, ('clean question', refs))
        self.assertEqual(self.local_source_bundle, bundle)
        self.assertEqual(self.outbound, [])

    def test_invalid_pdf_scope_is_rejected_on_all_routes_before_dispatch(self):
        malformed = [{'source_id':'a' * 32, 'source_sha256':'b' * 64, 'owner':'forged-owner'}]
        for client, route in ((self.hybrid_client, '/api/v1/hybrid-chat/stream'),
                              (self.normal_client, '/api/chat'), (self.legacy_client, '/v1/chat/completions')):
            with self.subTest(route=route):
                response = client.post(route, headers=self.headers, json={'prompt':'Explain this',
                    'user_prompt':'Explain this', 'source_references':malformed})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.outbound, [])
        self.assertEqual(self.local_calls, [])

    def test_explicit_openai_overrides_local_default_and_saved_models_are_preserved(self):
        self.cfg["active_provider"] = "local"
        self.cfg["providers"]["openai"]["model"] = "gpt-4o"
        self.assertEqual(self.post_hybrid(provider="openai").status_code, 200)
        self.assertEqual(json.loads(self.outbound[-1].content)["model"], "gpt-4o")
        self.assertEqual(self.post_hybrid(provider="openai", model="gpt-4.1-mini").status_code, 200)
        self.assertEqual(json.loads(self.outbound[-1].content)["model"], "gpt-4.1-mini")

    def test_host_and_shadow_coding_intents_stay_in_existing_local_branch(self):
        for prompt in ("/build fixture", "/code write a python function", "please use the shadow coder to explain this"):
            response = self.post_hybrid(prompt=prompt, user_prompt=prompt)
            self.assertIn("fixture local path", response.text)
        self.assertEqual(len(self.local_calls), 3)
        self.assertEqual(self.outbound, [])

    def test_bounded_coding_request_uses_existing_adapter_without_openai(self):
        response = self.post_hybrid(prompt="fix fixture and verify", user_prompt="fix fixture and verify")
        self.assertIn("fixture coding admission", response.text)
        self.assertEqual(len(self.coding_calls), 1)
        self.assertEqual(self.outbound, [])

    def test_plan_review_and_invalid_backend_never_call_provider_or_local_model(self):
        for fields in ({"mode": " PLAN "}, {"mode": "review"}, {"plan_only": True},
                       {"mode": "unsupported"}, {"execution_backend": "windows_vm"},
                       {"execution_backend": "not-a-backend"}):
            response = self.post_hybrid(**fields)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("fixture response", response.text)
        self.assertEqual(self.local_calls, [])
        self.assertEqual(self.outbound, [])

    def test_media_and_explicit_research_keep_existing_responses(self):
        self.media.media_status_response.return_value = {"response": "fixture media status"}
        self.assertEqual(self.post_hybrid().json()["response"], "fixture media status")
        self.media.media_status_response.return_value = None
        self.research.web_search_response.return_value = {"response": "fixture research"}
        self.assertEqual(self.post_hybrid(use_web_search=True).json()["response"], "fixture research")
        self.assertEqual(self.outbound, [])

    def test_missing_key_and_unsupported_model_fail_without_any_fallback(self):
        response = self.post_hybrid(model="unsupported-local-model")
        self.assertEqual(response.status_code, 400)
        with patch.dict(self.gateway.os.environ, {"OPENAI_API_KEY": ""}):
            response = self.post_hybrid()
            self.assertEqual(response.status_code, 503)
        self.assertEqual(self.outbound, [])
        self.assertEqual(self.local_calls, [])

    def test_upstream_failure_is_http_error_before_stream_and_is_never_retried(self):
        self.reply = lambda request: httpx.Response(429, text="private upstream " + environment_fixture.ENV_KEY)
        response = self.post_hybrid()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private upstream", response.text)
        self.assertNotIn(environment_fixture.ENV_KEY, response.text)
        self.assertEqual(len(self.outbound), 1)
        self.assertEqual(self.local_calls, [])

    def test_upstream_model_quota_and_auth_failures_have_safe_diagnostics(self):
        request_id = '92e84bf8-437e-4862-bdfe-b41d1c8e848c'
        for status, code, expected in ((404, 'model_not_found', 'project access'),
                (401, 'invalid_api_key', 'authentication failed'),
                (403, 'permission_denied', 'permissions'),
                (429, 'insufficient_quota', 'quota or credits'),
                (429, 'rate_limit_exceeded', 'not retried')):
            self.outbound.clear()
            self.reply = lambda request, status=status, code=code: httpx.Response(status,
                headers={'x-request-id': request_id},
                json={'error': {'code': code, 'message': 'private upstream ' + environment_fixture.ENV_KEY}})
            with self.subTest(status=status, code=code):
                response = self.post_hybrid()
                self.assertEqual(response.status_code, 502)
                self.assertIn(expected, response.text)
                self.assertIn(code, response.text)
                self.assertIn(request_id, response.text)
                self.assertNotIn(environment_fixture.ENV_KEY, response.text)
                self.assertNotIn('private upstream', response.text)
                self.assertEqual(len(self.outbound), 1)
                self.assertEqual(self.local_calls, [])

    def test_untrusted_diagnostic_fields_are_not_reflected(self):
        self.reply = lambda request: httpx.Response(404,
            headers={'x-request-id': environment_fixture.ENV_KEY},
            json={'error': {'code': environment_fixture.ENV_KEY, 'message': environment_fixture.ENV_KEY}})
        response = self.post_hybrid()
        self.assertEqual(response.status_code, 502)
        self.assertIn('gpt-4.1-mini', response.text)
        self.assertNotIn(environment_fixture.ENV_KEY, response.text)
        self.assertEqual(len(self.outbound), 1)

    def test_empty_or_invalid_provider_reply_is_not_success(self):
        for reply in ("", None, {"untrusted": "object"}):
            self.reply = lambda request, text=reply: httpx.Response(200, json={"choices": [{"message": {"content": text}}]})
            self.assertEqual(self.post_hybrid().status_code, 502)
        self.assertEqual(len(self.outbound), 3)
        self.assertEqual(self.local_calls, [])

    def test_generated_fenced_code_remains_text_and_never_runs(self):
        self.reply = lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "```powershell\nfixture command\n```"}}]})
        prompt = "write a python function to add two numbers"
        response = self.post_hybrid(prompt=prompt, user_prompt=prompt)
        self.assertEqual(response.status_code, 200)
        self.assertIn("proposal only", response.text)
        self.assertEqual(len(self.outbound), 1)
        self.assertEqual(self.local_calls, [])
        self.assertEqual(self.coding_calls, [])

    def test_active_api_chat_keeps_history_and_returns_cloud_metadata(self):
        response = self.normal_client.post("/api/chat", headers=self.headers, json={"provider": "openai", "stream": False,
            "user_prompt": "current fixture", "messages": [{"role": "user", "content": "prior"},
                {"role": "assistant", "content": "prior reply"}, {"role": "user", "content": "current fixture"}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "fixture response")
        self.assertEqual(response.json()["device"], "OpenAI API")
        self.assertEqual(len(self.sent_messages()), 4)
        self.normal["resolve_model_host"].assert_not_awaited()

    def test_active_api_chat_stream_preserves_sse_contract(self):
        response = self.normal_client.post("/api/chat", headers=self.headers,
            json={"provider": "openai", "prompt": "current fixture", "stream": True})
        self.assertEqual(response.status_code, 200)
        event = json.loads(response.text.split("data: ", 1)[1].split("\n\n", 1)[0])
        self.assertTrue(event["done"])
        self.assertEqual(event["content"], "fixture response")
        self.assertEqual(event["provider"], "openai")

    def test_active_api_chat_local_mode_reaches_existing_local_model_path(self):
        response = self.normal_client.post("/api/chat", headers=self.headers,
            json={"provider": "local", "prompt": "current fixture", "stream": False})
        self.assertEqual(response.status_code, 418)
        self.normal["resolve_model_host"].assert_awaited_once()
        self.assertEqual(self.outbound, [])

    def test_active_api_chat_plan_and_upstream_failure_do_not_fall_back(self):
        response = self.normal_client.post("/api/chat", headers=self.headers,
            json={"prompt": "current fixture", "mode": "review", "stream": False})
        self.assertIn("no tools, model calls", response.json()["response"])
        self.assertEqual(self.outbound, [])
        self.reply = lambda request: httpx.Response(401, text="fixture upstream refusal")
        response = self.normal_client.post("/api/chat", headers=self.headers,
            json={"prompt": "current fixture", "stream": False})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(len(self.outbound), 1)
        self.normal["resolve_model_host"].assert_not_awaited()

    def test_legacy_hybrid_and_compatibility_routes_reuse_cloud_path(self):
        for route in ("/api/v1/hybrid-chat/stream", "/api/chat", "/v1/chat/completions"):
            response = self.legacy_client.post(route, headers=self.headers,
                json={"prompt": "current fixture", "user_prompt": "current fixture", "stream": False})
            self.assertEqual(response.status_code, 200)
            self.assertIn("fixture response", response.text)
        self.assertEqual(len(self.outbound), 3)
        self.research.optional_web_context.assert_not_awaited()

    def test_legacy_encrypted_chat_resolves_provided_context_before_provider_call(self):
        payload = {"prompt": "decrypted fixture", "stream": False}
        decrypt = Mock(return_value=json.dumps(payload).encode())
        self.legacy["vault"] = types.SimpleNamespace(decrypt_payload=decrypt)
        response = self.legacy_client.post("/api/chat", headers=self.headers,
            json={"encrypted": True, "iv": "fixture", "ciphertext": "fixture"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.sent_messages()[-1]["content"], "decrypted fixture")
        decrypt.assert_called_once_with("fixture", "fixture")

    def test_anonymous_chat_is_denied_before_configuration_or_provider_access(self):
        for client, route in ((self.hybrid_client, "/api/v1/hybrid-chat/stream"),
                              (self.normal_client, "/api/chat"), (self.legacy_client, "/v1/chat/completions")):
            response = client.post(route, content="invalid body")
            self.assertEqual(response.status_code, 403)
        self.gateway.load_config.assert_not_called()
        self.assertEqual(self.outbound, [])


if __name__ == "__main__":
    unittest.main()
