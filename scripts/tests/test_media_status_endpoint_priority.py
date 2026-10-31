"""Exercise production endpoint bodies without importing the backend application."""
import ast
import asyncio
import builtins
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, List, Optional
import unittest
from unittest.mock import patch

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StrictBool, StrictStr, ValidationError

ROOT = Path(__file__).resolve().parents[2]


def extract(path, name, extra=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    item = next(n for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name)
    item.decorator_list = []
    scope = dict(Request=object, HybridStreamPayload=object, ChatRequest=object,
                 Optional=Optional, List=List, Any=Any, BaseModel=BaseModel,
                 Field=Field, StrictBool=StrictBool, StrictStr=StrictStr,
                 asyncio=asyncio, json=json, StreamingResponse=StreamingResponse,
                 EFFICIENCY_MODE_ENABLED=True)
    scope.update(extra or {})
    exec(compile(ast.Module(body=[item], type_ignores=[]), '<production-endpoint>', 'exec'), scope)
    return scope[name]


class ServiceStatusEndpointPriorityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.seen = []
        self.reply = 'ComfyUI service status fixture; no generation was submitted.'
        policy = ModuleType('core.media_intent_policy')
        async def resolve(body):
            self.seen.append(body)
            return self.reply
        policy.resolve_media_status = resolve
        web = ModuleType('core.optional_web_search')
        async def forbidden(*args, **kwargs):
            raise AssertionError('Status routing reached web/model/coding work')
        web.web_search_response = forbidden
        web.optional_web_context = forbidden
        coding = ModuleType('core.coding_chat')
        def forbidden_coding(*args, **kwargs):
            raise AssertionError('Status routing reached coding work')
        coding.coding_request = forbidden_coding
        coding.is_coding_request = lambda body: True
        history = ModuleType('core.historical_reference_context')
        history.historical_reference_context = forbidden
        history.request_reference_query = forbidden
        self.modules = patch.dict(sys.modules, {
            'core.media_intent_policy': policy, 'core.optional_web_search': web,
            'core.coding_chat': coding, 'core.historical_reference_context': history,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def request(self, stream=True):
        body = {'prompt': 'is comfy UI running?', 'user_prompt': 'is comfy UI running?',
                'model': 'explicit-selected-model', 'stream': stream, 'use_web_search': True}
        async def payload():
            return body
        return SimpleNamespace(json=payload), body

    async def consume(self, response):
        chunks = []
        async for part in response.body_iterator:
            chunks.append(part.decode() if isinstance(part, bytes) else part)
        return ''.join(chunks)

    async def test_hybrid_status_precedes_web_and_selected_model(self):
        fn = extract('backend/AI_BS_Backend.py', 'hybrid_chat_stream_endpoint')
        request, body = self.request()
        result = await fn(request)
        self.assertEqual(await self.consume(result), self.reply)
        self.assertEqual(self.seen, [body])

    async def test_legacy_nonstream_keeps_openai_choices(self):
        fn = extract('backend/AI_BS_Backend.py', 'chat_endpoint')
        request, body = self.request(stream=False)
        result = await fn(request)
        self.assertEqual(result['choices'][0]['message']['content'], self.reply)
        self.assertEqual(result['choices'][0]['message']['role'], 'assistant')
        self.assertEqual(self.seen, [body])

    async def test_legacy_stream_keeps_openai_delta_frames(self):
        fn = extract('backend/AI_BS_Backend.py', 'chat_endpoint')
        request, body = self.request()
        text = await self.consume(await fn(request))
        frames = [line[6:] for line in text.splitlines() if line.startswith('data: ')]
        self.assertEqual(json.loads(frames[0])['choices'][0]['delta']['content'], self.reply)
        self.assertEqual(frames[-1], '[DONE]')
        self.assertEqual(self.seen, [body])

    async def test_router_nonstream_keeps_response_field(self):
        fn = extract('backend/routers/chat_router.py', 'generate_chat_completion')
        _, body = self.request(stream=False)
        result = await fn(SimpleNamespace(model_dump=lambda: body, stream=False))
        self.assertEqual(result['response'], self.reply)
        self.assertEqual(self.seen, [body])

    async def test_router_stream_keeps_content_frames(self):
        fn = extract('backend/routers/chat_router.py', 'generate_chat_completion')
        _, body = self.request()
        text = await self.consume(await fn(SimpleNamespace(model_dump=lambda: body, stream=True)))
        frames = [json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: ')]
        self.assertEqual(frames[0]['content'], self.reply)
        self.assertTrue(frames[0]['done'])
        self.assertEqual(self.seen, [body])

    async def assert_router_status_avoids_unrelated_imports(self, stream):
        fn = extract('backend/routers/chat_router.py', 'generate_chat_completion')
        _, body = self.request(stream=stream)
        original = builtins.__import__
        def guarded(name, globals=None, locals=None, fromlist=(), level=0):
            if name in {'core.coding_chat', 'core.historical_reference_context'}:
                raise AssertionError('A status request must not load coding/history services')
            return original(name, globals, locals, fromlist, level)
        with patch('builtins.__import__', side_effect=guarded):
            result = await fn(SimpleNamespace(model_dump=lambda: body, stream=stream))
            if stream:
                self.assertIn(self.reply, await self.consume(result))
            else:
                self.assertEqual(result['response'], self.reply)
        self.assertEqual(self.seen, [body])

    async def test_router_status_json_does_not_import_coding_or_history(self):
        await self.assert_router_status_avoids_unrelated_imports(False)

    async def test_router_status_stream_does_not_import_coding_or_history(self):
        await self.assert_router_status_avoids_unrelated_imports(True)

    async def test_raw_intent_schema_is_optional_strict_and_bounded(self):
        models = [('backend/AI_BS_Backend.py', 'HybridStreamPayload'),
                  ('backend/routers/chat_router.py', 'ChatRequest')]
        for path, name in models:
            model = extract(path, name, {'ChatMessage': Any})
            self.assertIsNone(model(prompt='legacy prompt').user_prompt)
            self.assertEqual(model(prompt='decorated', user_prompt='status?').user_prompt, 'status?')
            for invalid in (True, 123, '', 'x' * 128001):
                with self.subTest(model=name, invalid_type=type(invalid).__name__):
                    with self.assertRaises(ValidationError):
                        model(prompt='decorated', user_prompt=invalid)


if __name__ == '__main__':
    unittest.main()
