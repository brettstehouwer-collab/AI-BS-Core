"""Explicit local proposal contracts using synthetic files and injected inference."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.core.native_local_refactor import RefactorProposalError, propose_source


class NativeLocalRefactorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / 'example.py'
        self.original = b'def answer():\r\n    return 42\r\n'
        self.path.write_bytes(self.original)
        self.calls = []
        self.response = {'text': 'def answer():\n    return 6 * 7\n',
            'receipt': {'provider': 'local', 'status': 'completed',
                        'generation_verified': True, 'completion_verified': True,
                        'completion_reason': 'stop', 'requested_model': 'fixture',
                        'model': 'fixture:latest', 'actual_model': 'fixture:latest',
                        'endpoint': 'http://127.0.0.1:11434'}}

    async def infer(self, **kwargs):
        self.calls.append(kwargs)
        return copy.deepcopy(self.response)

    async def propose(self, **kwargs):
        return await propose_source(self.path, self.root, endpoint='http://127.0.0.1:11434',
                                    model='fixture', infer=self.infer, **kwargs)

    async def assert_rejected(self, code=None, **kwargs):
        with self.assertRaises(RefactorProposalError) as caught:
            await self.propose(**kwargs)
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['example.py'])

    async def test_exact_original_and_candidate_retained_without_source_write(self):
        result = await self.propose()
        self.assertEqual(result['original_bytes'], self.original)
        self.assertEqual(result['original_sha256'], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(result['candidate_bytes'], self.response['text'].encode())
        self.assertEqual(result['candidate_sha256'], hashlib.sha256(result['candidate_bytes']).hexdigest())
        self.assertEqual(result['relative_path'], 'example.py')
        self.assertTrue(result['proposal_only'])
        self.assertTrue(result['syntax_validated'])
        self.assertFalse(result['semantics_verified'])
        self.assertFalse(result['source_written'])
        self.assertFalse(result['apply_authorized'])
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(len(self.calls), 1)

    async def test_stateless_single_origin_temperature_zero_without_history_or_tools(self):
        await self.propose()
        request = self.calls[0]
        self.assertEqual(request['endpoints'], ['http://127.0.0.1:11434'])
        self.assertEqual(request['model'], 'fixture')
        self.assertEqual(request['options']['temperature'], 0)
        self.assertIsNone(request['recovery'])
        self.assertEqual(json.loads(request['prompt']), {'path': 'example.py',
                                                         'source': self.original.decode()})
        for key in ('history', 'messages', 'tools', 'source_context_bundle'):
            self.assertNotIn(key, request)

    async def test_explicit_secondary_origin_is_not_a_fallback_list(self):
        self.response['receipt']['endpoint'] = 'http://127.0.0.1:11435'
        await propose_source(self.path, self.root, endpoint='http://127.0.0.1:11435',
                             model='fixture', infer=self.infer)
        self.assertEqual(self.calls[0]['endpoints'], ['http://127.0.0.1:11435'])
        self.assertEqual(len(self.calls), 1)

    async def test_exact_one_python_fence_is_unwrapped_without_other_text(self):
        self.response['text'] = '```python\r\ndef answer():\r\n    return 42\r\n```\r\n'
        result = await self.propose()
        self.assertEqual(result['candidate_bytes'], b'def answer():\r\n    return 42')

    async def test_refusal_prose_or_ambiguous_fences_fail_closed(self):
        for output in ('I cannot refactor this file.',
                       'Here is your code:\n```python\nx = 1\n```',
                       '```python\nx = 1\n```\nDone.',
                       '```python\nx = 1\n```\n```python\nx = 2\n```'):
            with self.subTest(output=output[:30]):
                self.response['text'] = output
                await self.assert_rejected()

    async def test_invalid_candidate_python_is_never_accepted(self):
        self.response['text'] = 'def broken(:\n    pass\n'
        await self.assert_rejected('invalid_candidate_python')

    async def test_empty_raw_and_empty_fenced_output_are_rejected(self):
        for output in ('', '\n\t ', '```python\n\n```'):
            self.response['text'] = output
            await self.assert_rejected('empty_model_output')

    async def test_unverified_or_length_limited_completion_is_rejected(self):
        for key, value in (('completion_verified', False), ('generation_verified', False),
                           ('status', 'error'), ('completion_reason', 'length')):
            receipt = copy.deepcopy(self.response['receipt'])
            with self.subTest(key=key):
                self.response['receipt'][key] = value
                await self.assert_rejected('unverified_generation')
                self.response['receipt'] = receipt

    async def test_wrong_or_unreported_model_identity_is_rejected(self):
        for key, value in (('actual_model', 'another:latest'), ('actual_model', None),
                           ('model', 'another'), ('requested_model', 'another')):
            receipt = copy.deepcopy(self.response['receipt'])
            with self.subTest(key=key, value=value):
                self.response['receipt'][key] = value
                await self.assert_rejected('model_identity_mismatch')
                self.response['receipt'] = receipt

    async def test_wrong_origin_or_remote_provider_receipt_is_rejected(self):
        self.response['receipt']['endpoint'] = 'http://127.0.0.1:11435'
        await self.assert_rejected('endpoint_identity_mismatch')
        self.response['receipt']['provider'] = 'remote'
        await self.assert_rejected('unverified_generation')

    async def test_invalid_endpoint_fails_before_inference(self):
        for endpoint in ('https://127.0.0.1:11434', 'http://example.test:11434',
                         'http://127.0.0.1:8000', 'http://user:secret@localhost:11434',
                         'http://localhost:11434/api/generate'):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(RefactorProposalError):
                    await propose_source(self.path, self.root, endpoint=endpoint,
                                         model='fixture', infer=self.infer)
        self.assertEqual(self.calls, [])

    async def test_context_limit_fails_without_truncation_or_inference(self):
        await self.assert_rejected('source_context_budget_exceeded', num_ctx=512)
        await self.assert_rejected('source_context_budget_exceeded', max_prompt_bytes=10)
        self.assertEqual(self.calls, [])

    async def test_oversized_source_and_invalid_original_fail_before_inference(self):
        self.original = b'# ' + b'x' * 32768
        self.path.write_bytes(self.original)
        await self.assert_rejected('source_limit_exceeded')
        self.original = b'def broken(:\n'
        self.path.write_bytes(self.original)
        await self.assert_rejected('invalid_original_python')
        self.assertEqual(self.calls, [])

    async def test_root_escape_and_source_alias_are_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside) / 'other.py'
            other.write_text('x = 1\n', encoding='utf-8')
            with self.assertRaises(RefactorProposalError):
                await propose_source(other, self.root, endpoint='http://127.0.0.1:11434',
                                     model='fixture', infer=self.infer)
        self.assertEqual(self.calls, [])

    async def test_hardlinked_source_is_not_admitted(self):
        alias = self.root / 'alias.py'
        os.link(self.path, alias)
        try:
            with self.assertRaises(RefactorProposalError) as caught:
                await self.propose()
            self.assertEqual(caught.exception.code, 'regular_single_link_source_required')
            self.assertEqual(self.calls, [])
        finally:
            alias.unlink()

    async def test_linked_source_is_not_admitted(self):
        alias = self.root / 'alias.py'
        try:
            alias.symlink_to(self.path)
        except OSError:
            self.skipTest('Test account cannot create an isolated symbolic link')
        try:
            with self.assertRaises(RefactorProposalError) as caught:
                await propose_source(alias, self.root, endpoint='http://127.0.0.1:11434',
                                     model='fixture', infer=self.infer)
            self.assertEqual(caught.exception.code, 'redirected_source_path')
            self.assertEqual(self.calls, [])
        finally:
            alias.unlink()

    async def test_original_utf8_bom_and_latin1_encoding_are_preserved(self):
        for original, candidate in (
                (b'\xef\xbb\xbfx = 1\n', 'x = 2\n'),
                (b'# coding: latin-1\nname = "caf\xe9"\n', '# coding: latin-1\nname = "caf\xe9"\n')):
            self.original = original
            self.path.write_bytes(original)
            self.response['text'] = candidate
            result = await self.propose()
            self.assertEqual(result['original_bytes'], original)
            if original.startswith(b'\xef\xbb\xbf'):
                self.assertTrue(result['candidate_bytes'].startswith(b'\xef\xbb\xbf'))
            else:
                self.assertIn(b'caf\xe9', result['candidate_bytes'])
            self.assertEqual(self.path.read_bytes(), original)

    async def test_encoding_cookie_change_is_rejected(self):
        self.original = b'# coding: latin-1\nname = "caf\xe9"\n'
        self.path.write_bytes(self.original)
        self.response['text'] = 'name = "plain"\n'
        await self.assert_rejected('candidate_encoding_changed')

    async def test_transport_failure_or_cancellation_never_retries(self):
        calls = []
        async def failed(**kwargs):
            calls.append(kwargs)
            raise RuntimeError('synthetic transport interruption')
        with self.assertRaises(RuntimeError):
            await propose_source(self.path, self.root, endpoint='http://127.0.0.1:11434',
                                 model='fixture', infer=failed)
        self.assertEqual(len(calls), 1)
        async def cancelled(**kwargs):
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await propose_source(self.path, self.root, endpoint='http://127.0.0.1:11434',
                                 model='fixture', infer=cancelled)
        self.assertEqual(self.path.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
