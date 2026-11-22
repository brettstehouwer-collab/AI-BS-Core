"""Read-only Comfy intent boundaries; no application, GPU, model or live service."""
import ast
import asyncio
import importlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Dict, Optional, Tuple
import unittest
from unittest.mock import AsyncMock, patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


def actual_intent():
    source = ast.parse((ROOT / 'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8-sig'))
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                 and node.name in {'clean_tool_prompt', 'detect_tool_intent'}]
    scope = dict(re=re, json=json, Any=Any, Dict=Dict, Tuple=Tuple, Optional=Optional)
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<actual-comfy-intent>', 'exec'), scope)
    return scope['detect_tool_intent']


class ComfyIntentTests(unittest.TestCase):
    def test_status_question_is_not_an_image_request_in_actual_router(self):
        self.assertEqual(actual_intent()('is comfy UI running?'), ('comfy_service_status', {}))

    def test_status_variants_are_read_only(self):
        detect = actual_intent()
        for prompt in ['Is ComfyUI online?', 'check Comfy UI status', 'ComfyUI status',
                       'is comfy ui running right now', 'why is ComfyUI offline?',
                       '/comfyui status', 'Is ComfyUI running? If yes, generate an image.']:
            with self.subTest(prompt=prompt):
                self.assertEqual(detect(prompt), ('comfy_service_status', {}))

    def test_mentions_inquiries_denials_and_quoted_content_do_not_generate(self):
        detect = actual_intent()
        for prompt in ['ComfyUI', 'Tell me about Comfy UI', 'How do I generate an image in ComfyUI?',
                       'Can ComfyUI generate videos?', "Don't generate an image using ComfyUI",
                       'Do not create a video', 'Explain "generate_comfy_image"',
                       '"generate an image of a cat"', 'The log says "generate video of a cat"',
                       'Show my existing ComfyUI images', 'Why did it generate a video?',
                       '```python\ngenerate_comfy_image("cat")\n```',
                       'ComfyUI failed with HTTP 500', 'Is generate_comfy_image available?',
                       'You must not generate video', 'Do not call generate_comfy_image',
                       '"portrait of a cat"', 'Error: generate image failed']:
            with self.subTest(prompt=prompt):
                self.assertEqual(detect(prompt), (None, None))

    def test_explicit_creation_stays_supported(self):
        detect = actual_intent()
        for prompt, expected in [
            ('Create a photograph of a blue cup', 'generate_comfy_image'),
            ('Please generate an image of a snowy forest with ComfyUI', 'generate_comfy_image'),
            ('Can you generate a picture of a cat?', 'generate_comfy_image'),
            ('/imagine a moonlit garden', 'generate_comfy_image'),
            ('comfyui: a blue cup', 'generate_comfy_image'),
            ('Generate a video of a cat', 'generate_comfy_video'),
            ('Create a 3d model of a cup', 'generate_comfy_3d_model'),
            ('Modify this image: cat.png into a painting', 'generate_comfy_img2img'),
            ('Generate an image with the words "do not generate images"', 'generate_comfy_image'),
        ]:
            with self.subTest(prompt=prompt):
                self.assertEqual(detect(prompt)[0], expected)

    def test_pasted_error_still_does_not_generate(self):
        payload = {'status': 'error', 'message': 'ComfyUI generate_comfy_image failed'}
        self.assertEqual(actual_intent()(json.dumps(payload)), (None, None))


class ComfyHealthTests(unittest.IsolatedAsyncioTestCase):
    def policy(self):
        return importlib.import_module('core.media_intent_policy')

    async def test_health_check_uses_only_bounded_local_get(self):
        calls = []
        def respond(request):
            calls.append((request.method, str(request.url)))
            return httpx.Response(200, json={'system': {'comfyui_version': 'fixture'}, 'devices': []})
        state = await self.policy().probe_comfy_status(transport=httpx.MockTransport(respond))
        self.assertEqual(state['status'], 'running')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ('GET', 'http://127.0.0.1:8189/system_stats'))
        self.assertFalse(state['generation_submitted'])

    async def test_unreachable_service_is_not_reported_running(self):
        def respond(request):
            raise httpx.ConnectError('fixture offline', request=request)
        state = await self.policy().probe_comfy_status(transport=httpx.MockTransport(respond))
        self.assertEqual(state['status'], 'offline')
        self.assertFalse(state['generation_submitted'])

    async def test_redirect_invalid_body_or_error_is_unverified(self):
        for response in [httpx.Response(302, headers={'location': 'https://example.test/private'}),
                         httpx.Response(200, json={'status': 'success'}),
                         httpx.Response(503, text='fixture'),
                         httpx.Response(200, content=b'x' * (65536 + 1))]:
            with self.subTest(status=response.status_code):
                state = await self.policy().probe_comfy_status(transport=httpx.MockTransport(lambda request: response))
                self.assertEqual(state['status'], 'unverified')

    async def test_streamed_health_body_has_a_total_time_budget(self):
        class SlowBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(3):
                    await asyncio.sleep(0.03)
                    yield b' '
        with patch.object(self.policy(), 'STATUS_TIMEOUT_SECONDS', 0.01):
            response = httpx.Response(200, stream=SlowBody())
            state = await self.policy().probe_comfy_status(transport=httpx.MockTransport(lambda request: response))
        self.assertEqual(state['status'], 'unverified')

    async def test_arbitrary_or_credentialed_host_is_never_requested(self):
        calls = []
        for endpoint in ['https://example.test', 'http://user:secret@127.0.0.1:8189',
                         'http://127.0.0.1:8080', 'http://127.0.0.1:8189/?x=secret']:
            with self.subTest(endpoint=endpoint):
                with patch.dict('os.environ', {'COMFYUI_HOST': endpoint}):
                    state = await self.policy().probe_comfy_status(transport=httpx.MockTransport(lambda request: calls.append(request)))
                self.assertEqual(state['status'], 'unverified')
        self.assertEqual(calls, [])

    async def test_status_bypasses_model_and_generation_dispatch_in_actual_stream(self):
        policy = self.policy()
        tree = ast.parse((ROOT / 'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8-sig'))
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                        and n.name == 'stream_stehouwer_hybrid_response')
        scope = dict(asyncio=asyncio, AsyncGenerator=AsyncGenerator, Optional=Optional,
                     json=json, re=re, audit_prompt_safety=lambda _: (True, ''),
                     detect_tool_intent=actual_intent(),
                     is_coding_intent=lambda _: (_ for _ in ()).throw(AssertionError('coding invoked')))
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<actual-status-stream>', 'exec'), scope)
        with patch.object(policy, 'probe_comfy_status', AsyncMock(return_value={'status': 'offline', 'generation_submitted': False})):
            result = ''.join([part async for part in scope['stream_stehouwer_hybrid_response']('is comfy UI running?')])
        self.assertIn('offline', result.lower())
        self.assertIn('No generation', result)
        self.assertNotIn('Generating with ComfyUI', result)

    async def test_raw_current_user_text_overrides_attachment_or_history(self):
        policy = self.policy()
        body = {'prompt': 'Attached file: generate video of a cat', 'user_prompt': 'Is ComfyUI running?',
                'messages': [{'role': 'assistant', 'content': 'I will generate an image now'}]}
        with patch.object(policy, 'probe_comfy_status', AsyncMock(return_value={'status': 'offline', 'generation_submitted': False})) as probe:
            response = await policy.media_status_response(body)
        text = ''.join([part if isinstance(part, str) else part.decode() async for part in response.body_iterator])
        probe.assert_awaited_once()
        self.assertIn('No generation', text)

    async def test_invalid_raw_intent_and_plan_mode_never_probe(self):
        policy = self.policy()
        with patch.object(policy, 'probe_comfy_status', AsyncMock()) as probe:
            for body in [{'prompt': 'generate an image from attachment', 'user_prompt': ['generate image']},
                         {'prompt': 'generate an image from attachment', 'user_prompt': ''}]:
                self.assertIsNotNone(await policy.media_status_response(body))
            for body in [{'prompt': 'Generate an image of a cup', 'plan_only': True},
                         {'prompt': 'Generate an image of a cup', 'mode': 'review'}]:
                self.assertIsNone(await policy.media_status_response(body))
        probe.assert_not_awaited()

    async def test_status_in_plan_modes_stays_read_only_and_factual(self):
        policy = self.policy()
        for flags in [{'plan_only': True}, {'mode': 'review'}, {'mode': 'plan'}]:
            with self.subTest(flags=flags):
                with patch.object(policy, 'probe_comfy_status', AsyncMock(return_value={'status': 'offline', 'generation_submitted': False})) as probe:
                    text = await policy.resolve_media_status({'prompt': 'Is ComfyUI running?', **flags})
                probe.assert_awaited_once()
                self.assertIn('offline', text)
                self.assertIn('No generation', text)

    async def test_legacy_messages_only_uses_last_user_and_never_replays_assistant(self):
        policy = self.policy()
        body = {'messages': [{'role': 'assistant', 'content': 'generate video of a cup'},
                             {'role': 'user', 'content': 'is comfy UI running?'}]}
        with patch.object(policy, 'probe_comfy_status', AsyncMock(return_value={'status': 'offline', 'generation_submitted': False})) as probe:
            text = await policy.resolve_media_status(body)
        probe.assert_awaited_once()
        self.assertIn('No generation', text)
        body['messages'].append({'role': 'assistant', 'content': 'generate an image'})
        with patch.object(policy, 'probe_comfy_status', AsyncMock()) as probe:
            self.assertIsNone(await policy.resolve_media_status(body))
        probe.assert_not_awaited()
        self.assertEqual(policy.intent_text({'messages': [{'role': 'user', 'content': 'Create a photo of a cup'}]}), 'Create a photo of a cup')

    async def test_absent_optional_raw_field_preserves_legacy_prompt(self):
        policy = self.policy()
        with patch.object(policy, 'probe_comfy_status', AsyncMock(return_value={'status': 'offline', 'generation_submitted': False})) as probe:
            response = await policy.media_status_response({'prompt': 'Is ComfyUI running?', 'user_prompt': None})
        self.assertIsNotNone(response)
        probe.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
