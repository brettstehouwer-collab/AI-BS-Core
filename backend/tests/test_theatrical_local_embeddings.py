"""Synthetic protocol tests. No real model, manuscripts or services are used."""
import copy
import io
import json
import sqlite3
import time
import unittest
from unittest.mock import Mock, patch

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.security.theatrical_corpus_registry import CorpusRegistry
from backend.security.theatrical_local_embeddings import LocalNomicEmbedder
from backend.tests.test_theatrical_corpus_registry import Store


DIGEST = 'a' * 64
MODEL = 'nomic-embed-text:latest'


class Protocol:
    def __init__(self):
        self.calls = []
        self.tags = {'models': [dict(name=MODEL, digest=DIGEST)]}
        self.show = dict(capabilities=['embedding'], remote_model=None, remote_host=None,
                         details=dict(family='nomic-bert', format='gguf', parent_model=''))
        self.override = None

    def request(self, method, path, payload, deadline):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if self.override:
            value = self.override(method, path, payload)
            if value is not None:
                return value
        if path == '/api/tags':
            return copy.deepcopy(self.tags)
        if path == '/api/show':
            return copy.deepcopy(self.show)
        if path == '/api/embed':
            return dict(model=MODEL, embeddings=[[0.5] * 768 for _ in payload['input']])
        raise AssertionError(path)


class LocalEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.adapter = LocalNomicEmbedder(expected_digest=DIGEST)
        self.protocol = Protocol()
        self.wire = patch.object(self.adapter, '_request_json', self.protocol.request)
        self.wire.start()
        self.addCleanup(self.wire.stop)

    def assert_code(self, code, call):
        with self.assertRaises(CorpusBoundaryError) as caught:
            call()
        self.assertEqual(str(caught.exception), code)

    def test_explicit_profile_is_stable_and_binds_digest_and_port(self):
        self.assertEqual(self.adapter.embedding_profile,
                         LocalNomicEmbedder(expected_digest=DIGEST).embedding_profile)
        for other in [LocalNomicEmbedder(expected_digest='b'*64),
                      LocalNomicEmbedder(expected_digest=DIGEST, port=11435)]:
            self.assertNotEqual(self.adapter.embedding_profile, other.embedding_profile)
        self.assertEqual(self.adapter.dimensions, 768)

    def test_only_fixed_numeric_loopback_port_and_explicit_digest_config(self):
        for kwargs in [dict(expected_digest=''), dict(expected_digest='A'*64),
                       dict(expected_digest=DIGEST, port=True),
                       dict(expected_digest=DIGEST, port=8080),
                       dict(expected_digest=DIGEST, timeout_seconds=0),
                       dict(expected_digest=DIGEST, timeout_seconds=float('nan')),
                       dict(expected_digest=DIGEST, timeout_seconds=301)]:
            with self.subTest(kwargs=kwargs):
                self.assert_code('INVALID_EMBEDDING_CONFIG', lambda: LocalNomicEmbedder(**kwargs))

    def test_query_document_prefixes_and_original_unicode_are_preserved(self):
        text = '\ufeffINT. ROOM\r\nCafe\u0301 \U0001f3ad'
        self.assertEqual(len(self.adapter.embed_documents([text])), 1)
        self.assertEqual(len(self.adapter.embed_query(text)), 768)
        payloads = [payload for _, path, payload in self.protocol.calls if path == '/api/embed']
        self.assertEqual(payloads[0]['input'], ['search_document: ' + text])
        self.assertEqual(payloads[1]['input'], ['search_query: ' + text])
        for payload in payloads:
            self.assertEqual(payload['model'], MODEL)
            self.assertIs(payload['truncate'], False)
            self.assertEqual(payload['keep_alive'], '0s')
            self.assertEqual(payload['options'], dict(num_gpu=0, num_thread=2, num_ctx=8192))
        self.assertEqual([p for _, p, _ in self.protocol.calls[:3]],
                         ['/api/tags', '/api/show', '/api/embed'])

    def test_documents_are_batched_and_all_text_is_validated_before_io(self):
        self.assertEqual(len(self.adapter.embed_documents(['x'] * 17)), 17)
        batches = [p['input'] for _, route, p in self.protocol.calls if route == '/api/embed']
        self.assertEqual(list(map(len, batches)), [8, 8, 1])
        self.protocol.calls.clear()
        self.assert_code('INVALID_EMBEDDING_INPUT', lambda: self.adapter.embed_documents(['ok', '\ud800']))
        self.assertEqual(self.protocol.calls, [])

    def test_input_bounds_and_types_reject_without_requests(self):
        for bad in [[], (), 'text', [None], [''], ['x'*4097], ['ok']*2049]:
            with self.subTest(kind=type(bad).__name__):
                self.assert_code('INVALID_EMBEDDING_INPUT', lambda: self.adapter.embed_documents(bad))
        self.assert_code('INVALID_EMBEDDING_INPUT', lambda: self.adapter.embed_query(['q']))
        self.assertEqual(self.protocol.calls, [])

    def test_total_utf8_byte_bound_not_character_count(self):
        self.assert_code('INVALID_EMBEDDING_INPUT',
                         lambda: self.adapter.embed_documents(['\U0001f3ad'*4096] * 513))
        self.assertEqual(self.protocol.calls, [])

    def test_wrong_missing_or_duplicate_tag_never_receives_text(self):
        for models in [[], [dict(name=MODEL, digest='b'*64)],
                       [dict(name=MODEL, digest=DIGEST)]*2,
                       [dict(name='other', digest=DIGEST)]]:
            self.protocol.tags = {'models': models}
            self.assert_code('EMBEDDING_MODEL_MISMATCH', lambda: self.adapter.embed_query('private'))
        self.assertFalse(any(p == '/api/embed' for _, p, _ in self.protocol.calls))

    def test_remote_or_generation_capability_is_rejected(self):
        for patch_values in [dict(remote_host='https://remote.invalid'),
                             dict(remote_model='remote'), dict(capabilities=['embedding', 'completion']),
                             dict(capabilities=[]), dict(details=dict(family='llama', format='gguf'))]:
            original = copy.deepcopy(self.protocol.show)
            self.protocol.show.update(patch_values)
            self.assert_code('EMBEDDING_MODEL_MISMATCH', lambda: self.adapter.embed_query('private'))
            self.protocol.show = original
        self.assertFalse(any(p == '/api/embed' for _, p, _ in self.protocol.calls))

    def test_tag_change_after_batch_discards_vectors(self):
        def change(method, path, payload):
            if path == '/api/embed':
                self.protocol.tags['models'][0]['digest'] = 'b'*64
        self.protocol.override = change
        self.assert_code('EMBEDDING_MODEL_MISMATCH', lambda: self.adapter.embed_documents(['x']*9))
        self.assertEqual(sum(p == '/api/embed' for _, p, _ in self.protocol.calls), 1)

    def test_model_name_vector_shape_and_numeric_values_are_checked(self):
        bad_responses = [dict(model='other', embeddings=[[0.5]*768]),
                         dict(model=MODEL, embeddings=[]), dict(model=MODEL, embeddings=[[1, 2]]),
                         dict(model=MODEL, embeddings=[[0]*768]),
                         dict(model=MODEL, embeddings=[[True]*768]),
                         dict(model=MODEL, embeddings=[[float('nan')]*768]),
                         dict(model=MODEL, embeddings=[[1e100]*768]),
                         dict(model=MODEL, embeddings=[[0.5]*768]*2)]
        for bad in bad_responses:
            self.protocol.override = lambda m, p, b: bad if p == '/api/embed' else None
            self.assert_code('INVALID_EMBEDDING_RESPONSE', lambda: self.adapter.embed_query('q'))

    def test_provider_error_is_redacted_and_no_retry_or_fallback_occurs(self):
        def fail(method, path, payload):
            raise RuntimeError('SECRET manuscript and credentials')
        self.protocol.override = fail
        self.assert_code('EMBEDDING_UNAVAILABLE', lambda: self.adapter.embed_query('q'))
        self.assertEqual(len(self.protocol.calls), 1)

    def test_concurrent_request_is_rejected_and_gate_recovers(self):
        self.adapter._gate.acquire()
        try:
            self.assert_code('EMBEDDING_BUSY', lambda: self.adapter.embed_query('q'))
            self.assertEqual(self.protocol.calls, [])
        finally:
            self.adapter._gate.release()
        self.assertEqual(len(self.adapter.embed_query('q')), 768)

    def test_registry_composition_preserves_bytes_and_rejects_dependency_change(self):
        connection = sqlite3.connect(':memory:')
        self.addCleanup(connection.close)
        registry = CorpusRegistry(connection)
        store = Store()
        raw = b'\xef\xbb\xbfINT. ROOM\r\nSYNTHETIC\r\n'
        scope = registry.ingest('local_admin', 'play', [('s', raw)], store,
                               self.adapter.embed_documents,
                               embedding_profile=self.adapter.embedding_profile, dimensions=768)
        result = registry.retrieve('local_admin', 'play', store, self.adapter.embed_query('room'),
                                   embedding_profile=self.adapter.embedding_profile)
        self.assertEqual(result.scope, scope)
        self.assertEqual(result.documents[0].encode('utf-8'), raw)
        self.protocol.tags['models'][0]['digest'] = 'b'*64
        self.assert_code('CORPUS_EMBEDDING_UNAVAILABLE', lambda: registry.ingest(
            'local_admin', 'play', [('s', b'changed')], store, self.adapter.embed_documents,
            embedding_profile=self.adapter.embedding_profile, dimensions=768))
        self.assertEqual(registry.resolve('local_admin', 'play').scope, scope)


class WireTests(unittest.TestCase):
    def call_wire(self, raw=b'{}', headers=None, status=200, timeout=1):
        adapter = LocalNomicEmbedder(expected_digest=DIGEST, timeout_seconds=timeout)
        values = {'Content-Type': 'application/json', 'Content-Length': str(len(raw))}
        values.update(headers or {})
        response = Mock(status=status)
        response.getheader.side_effect = lambda key, default=None: values.get(key, default)
        response.read1.side_effect = io.BytesIO(raw).read1
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('backend.security.theatrical_local_embeddings.HTTPConnection', return_value=connection):
            try:
                return adapter._request_json('POST', '/api/embed', {'input': ['q']},
                                             time.monotonic() + timeout)
            finally:
                connection.close.assert_called()

    def test_strict_bounded_json_transport(self):
        self.assertEqual(self.call_wire(b'{"ok":true}'), {'ok': True})
        for raw, headers in [(b'{"x":1,"x":2}', {}), (b'{"x":NaN}', {}),
                             (b'[]', {}), (b'\xff', {}),
                             (b'{}', {'Content-Length': '100'}),
                             (b'{}', {'Content-Length': '1048577'}),
                             (b'{}', {'Content-Type': 'text/html'}),
                             (b'{}', {'Content-Encoding': 'gzip'}),
                             (b' ' * 1048577, {'Content-Length': None})]:
            with self.subTest(headers=headers, size=len(raw)):
                with self.assertRaises(CorpusBoundaryError):
                    self.call_wire(raw, headers)

    def test_all_admitted_unicode_fits_wire_batch_limit(self):
        adapter = LocalNomicEmbedder(expected_digest=DIGEST)
        raw = b'{}'
        response = Mock(status=200)
        response.getheader.side_effect = lambda k, d=None: {
            'Content-Type': 'application/json', 'Content-Length': '2'}.get(k, d)
        response.read1.side_effect = io.BytesIO(raw).read1
        connection = Mock()
        connection.getresponse.return_value = response
        payload = dict(model=MODEL, input=['search_document: ' + '\U0001f3ad'*4096]*8)
        with patch('backend.security.theatrical_local_embeddings.HTTPConnection', return_value=connection):
            self.assertEqual(adapter._request_json('POST', '/api/embed', payload,
                                                  time.monotonic()+1), {})
        wire = connection.request.call_args.kwargs['body']
        self.assertEqual(json.loads(wire)['input'], payload['input'])

    def test_deadline_closes_owned_socket_and_releases_gate(self):
        adapter = LocalNomicEmbedder(expected_digest=DIGEST, timeout_seconds=0.01)
        response = Mock(status=200)
        response.getheader.side_effect = lambda k, d=None: {'Content-Type': 'application/json'}.get(k, d)
        def slow_read(_):
            time.sleep(0.04)
            return b''
        response.read1.side_effect = slow_read
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('backend.security.theatrical_local_embeddings.HTTPConnection', return_value=connection):
            with self.assertRaises(CorpusBoundaryError):
                adapter.embed_query('q')
        connection.sock.shutdown.assert_called_once()
        connection.sock.close.assert_called_once()
        self.assertTrue(adapter._gate.acquire(blocking=False))
        adapter._gate.release()

    def test_transport_ignores_proxy_does_not_follow_redirect_and_closes(self):
        adapter = LocalNomicEmbedder(expected_digest=DIGEST)
        response = Mock(status=302)
        response.getheader.return_value = 'application/json'
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('backend.security.theatrical_local_embeddings.HTTPConnection', return_value=connection) as constructor:
            with self.assertRaises(CorpusBoundaryError) as caught:
                adapter.embed_query('q')
        self.assertEqual(str(caught.exception), 'EMBEDDING_UNAVAILABLE')
        self.assertEqual(constructor.call_args.args, ('127.0.0.1', 11434))
        self.assertEqual(constructor.call_count, 1)
        connection.close.assert_called()


if __name__ == '__main__':
    unittest.main()
