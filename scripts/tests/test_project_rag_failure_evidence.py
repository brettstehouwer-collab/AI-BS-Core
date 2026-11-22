"""Sanitized real embedding failure paths; mocked provider/admission, no live calls."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi import HTTPException

ROOT = Path('C:/AI-BS')
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'backend'))
STAGE = Path(os.environ['AIBS_PROJECT_RAG_STAGE_ROOT']) if os.environ.get('AIBS_PROJECT_RAG_STAGE_ROOT') else ROOT
spec = importlib.util.spec_from_file_location('rag_failure_evidence_under_test', STAGE / 'backend/core/project_rag.py')
rag = importlib.util.module_from_spec(spec); spec.loader.exec_module(rag)


class Dispatcher:
    def __init__(self):
        self.calls = 0; self.released = 0; self.ctx = 8192; self.failure = False

    @asynccontextmanager
    async def lease(self, *args, **kwargs):
        self.calls += 1
        if self.failure:
            raise rag.GPUAdmissionError('secret_admission_detail')
        try:
            yield dict(num_ctx=self.ctx, num_batch=128, keep_alive_s=60,
                       gpu_admitted=False, execution='fixture_only')
        finally:
            self.released += 1


class EmbeddingFailureEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dispatcher = Dispatcher(); self.calls = []; self.behavior = 'timeout'; self.actual_client = httpx.AsyncClient
        self.seen = []; self.secret = 'DO_NOT_EMIT_exception_body_key_or_prompt'; self.client_options = []
        async def handler(request):
            self.calls.append(request)
            if self.behavior == 'timeout':
                raise httpx.ReadTimeout(self.secret, request=request)
            if self.behavior == 'provider':
                return httpx.Response(503, json={'error': self.secret})
            if self.behavior == 'json':
                return httpx.Response(200, content=self.secret.encode())
            if self.behavior == 'shape':
                return httpx.Response(200, json=['invalid_embedding_envelope'])
            if self.behavior == 'cancel':
                raise asyncio.CancelledError(self.secret)
            if self.behavior == 'partial' and len(self.calls) == 2:
                raise httpx.ReadTimeout(self.secret, request=request)
            return httpx.Response(200, json={'model': 'nomic-embed-text:latest',
                                           'embedding': [0., 0.] if self.behavior == 'zero' else [.1, .2]})
        def client(**kwargs):
            self.client_options.append(kwargs.copy())
            return self.actual_client(transport=httpx.MockTransport(handler), **kwargs)
        for guard in [patch.object(rag, 'get_dispatcher', return_value=self.dispatcher),
                      patch.object(rag.httpx, 'AsyncClient', side_effect=client)]:
            guard.start(); self.addCleanup(guard.stop)

    async def failure(self, text='synthetic source', status=502):
        with self.assertRaises(HTTPException) as caught:
            await rag.get_embedding_async(text, receipt_sink=self.seen.append)
        error = caught.exception; self.assertEqual(error.status_code, status)
        evidence = error.detail['embedding_evidence']
        self.assertEqual(len(evidence), 1); self.assertEqual(evidence, self.seen)
        row = evidence[0]
        self.assertEqual(row['requested_model'], 'nomic-embed-text')
        self.assertEqual(row['input_sha256'], hashlib.sha256(text.encode()).hexdigest())
        self.assertFalse(row['embedding_verified']); self.assertEqual(row['status'], 'error')
        serialized = json.dumps(error.detail)
        self.assertNotIn(self.secret, serialized); self.assertNotIn(text, serialized)
        return row

    async def test_read_timeout_retains_budget_category_and_one_released_admission(self):
        row = await self.failure()
        self.assertEqual(row['error_category'], 'read_timeout')
        self.assertEqual(row['error_type'], 'ReadTimeout'); self.assertIsNone(row['provider_http_status'])
        self.assertEqual(row['context_budget']['admitted_context'], 8192)
        self.assertEqual(len(self.calls), 1); self.assertEqual(self.dispatcher.released, 1)

    async def test_provider_failure_retains_status_without_provider_body(self):
        self.behavior = 'provider'; row = await self.failure()
        self.assertEqual(row['error_category'], 'provider_http_status')
        self.assertEqual(row['provider_http_status'], 503); self.assertEqual(len(self.calls), 1)

    async def test_invalid_json_is_separate_from_timeout(self):
        self.behavior = 'json'; row = await self.failure()
        self.assertEqual(row['error_category'], 'invalid_response_json'); self.assertEqual(row['provider_http_status'], 200)

    async def test_nonobject_provider_envelope_is_sanitized_invalid_response(self):
        self.behavior = 'shape'; row = await self.failure()
        self.assertEqual(row['error_category'], 'invalid_response_shape')

    def assert_finite_local_client(self):
        from core.local_ollama_http import _LOCAL_HTTP_CONTEXT, _require_local_request
        self.assertEqual(len(self.client_options), 1)
        options = self.client_options[0]; timeout = options['timeout']
        self.assertEqual((timeout.read, timeout.connect, timeout.write, timeout.pool), (60, 5, 15, 5))
        self.assertIs(options['trust_env'], False); self.assertIs(options['verify'], _LOCAL_HTTP_CONTEXT)
        self.assertEqual(options['event_hooks']['request'], [_require_local_request])

    async def test_standalone_embedding_client_uses_real_local_guard_and_bounded_cold_load_budget(self):
        self.behavior = 'success'; self.assertEqual(await rag.get_embedding_async('synthetic'), [.1, .2])
        self.assert_finite_local_client(); self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.dispatcher.calls, 1); self.assertEqual(self.dispatcher.released, 1)

    async def test_invalid_zero_vector_never_published_as_embedding(self):
        self.behavior = 'zero'; row = await self.failure()
        self.assertEqual(row['error_category'], 'invalid_vector'); self.assertNotIn('dimensions', row)

    async def test_admission_failure_has_no_http_or_fabricated_admitted_budget(self):
        self.dispatcher.failure = True; row = await self.failure()
        self.assertEqual(row['error_category'], 'admission_failed')
        self.assertEqual(self.calls, []); self.assertNotIn('admission', row)
        self.assertNotIn('context_budget', row)

    async def test_budget_refusal_keeps_413_and_never_calls_provider(self):
        self.dispatcher.ctx = 1024; row = await self.failure('x' * 2000, status=413)
        self.assertEqual(row['error_category'], 'context_budget_exceeded'); self.assertEqual(self.calls, [])

    async def test_cancellation_propagates_with_one_sanitized_receipt_and_release(self):
        self.behavior = 'cancel'
        with self.assertRaises(asyncio.CancelledError):
            await rag.get_embedding_async('synthetic source', receipt_sink=self.seen.append)
        self.assertEqual(len(self.seen), 1); self.assertEqual(self.seen[0]['status'], 'cancelled')
        self.assertEqual(self.seen[0]['error_category'], 'cancelled')
        self.assertNotIn(self.secret, json.dumps(self.seen)); self.assertEqual(self.dispatcher.released, 1)

    async def test_partial_embedding_failure_retains_prior_receipt_and_never_upserts(self):
        self.behavior = 'partial'; collection = Mock()
        docs = [dict(content='synthetic first'), dict(content='synthetic second')]
        with patch.object(rag, '_snapshot', return_value=({'source_chunks': 2}, docs)), \
                patch.object(rag, '_collection', return_value=collection):
            with self.assertRaises(HTTPException) as caught:
                await rag.sync_project_screenplay('Synthetic', owner='fixture_owner')
        detail = caught.exception.detail
        self.assertEqual([row['status'] for row in detail['embedding_evidence']], ['completed', 'error'])
        self.assertEqual(detail['embeddings_completed'], 1)
        self.assertFalse(detail['index_receipt_published']); self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.dispatcher.calls, 2); self.assertEqual(self.dispatcher.released, 2)
        collection.upsert.assert_not_called(); self.assertNotIn(self.secret, json.dumps(detail))
        self.assert_finite_local_client()


if __name__ == '__main__':
    unittest.main()
