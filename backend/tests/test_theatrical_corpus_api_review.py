"""Additional adversarial review of the unmounted API; synthetic data only."""
import json
import unittest

from backend.tests import test_theatrical_corpus_api as api_fixture


class CorpusApiReviewTests(unittest.TestCase):
    setUp = api_fixture.CorpusApiTests.setUp
    tearDown = api_fixture.CorpusApiTests.tearDown
    ingest = api_fixture.CorpusApiTests.ingest
    query = api_fixture.CorpusApiTests.query

    def test_all_routes_require_authentication(self):
        self.ingest()
        for method, suffix, body in [('get', 'status', None),
                ('post', 'evidence', dict(query='q')),
                ('post', 'deactivate', dict(expected_revision='a' * 64))]:
            response = self.client.request(method, '/api/theatrical/corpora/play/' + suffix,
                                           json=body)
            self.assertEqual(response.status_code, 403, response.text)
        self.embedder.embed_query.assert_not_called()
        self.assertEqual(len(self.store.collections), 1)

    def test_configuration_mismatch_does_not_embed_prompt(self):
        self.registry.ingest('local_admin', 'play', [('script', b'PRIVATE FIXTURE')],
            self.store, lambda texts: [[.25, .75]],
            embedding_profile='different-admitted-profile', dimensions=2)
        response = self.query()
        self.assertEqual(response.status_code, 503)
        self.embedder.embed_query.assert_not_called()
        self.assertNotIn('PRIVATE FIXTURE', response.text)

    def test_revocation_during_query_embedding_returns_no_evidence(self):
        revision = self.ingest().json()['revision']

        def revoke(query):
            self.registry.deactivate('local_admin', 'play', expected_revision=revision)
            return [.25, .75]

        self.embedder.embed_query.side_effect = revoke
        response = self.query()
        self.assertEqual(response.status_code, 404, response.text)
        self.assertNotIn('SYNTHETIC', response.text)
        self.assertEqual(len(self.store.collections), 1)

    def test_replacement_during_query_embedding_is_not_silently_selected(self):
        self.ingest()

        def replace(query):
            self.registry.ingest('local_admin', 'play', [('script', b'REPLACEMENT FIXTURE')],
                self.store, self.embedder.embed_documents,
                embedding_profile='local-fixture-v1', dimensions=2)
            return [.25, .75]

        self.embedder.embed_query.side_effect = replace
        response = self.query()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertNotIn('FIXTURE', response.text)
        self.assertEqual(len(self.store.collections), 2)

    def test_invalid_provider_vector_does_not_return_evidence(self):
        self.ingest()
        for vector in [[True, 0], [float('nan'), 0], [1], None]:
            self.embedder.embed_query.return_value = vector
            response = self.query()
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SYNTHETIC', response.text)

    def test_utf8_byte_bound_and_invalid_unicode_before_embedding(self):
        oversized = self.ingest(sources=[dict(source_id='script', text='\U0001f3ad' * 530000)])
        self.assertEqual(oversized.status_code, 422, oversized.text)
        malformed = self.client.post('/api/theatrical/corpora/play/ingest', headers={
            **self.auth, 'Content-Type': 'application/json'},
            content=json.dumps(dict(sources=[dict(source_id='script', text='\ud800')])).encode('ascii'))
        self.assertEqual(malformed.status_code, 422, malformed.text)
        self.embedder.embed_documents.assert_not_called()
        self.assertEqual(self.store.creates, 0)

    def test_authentication_precedes_malformed_json_and_oversized_header(self):
        for body, headers in [(b'{malformed', {}), (b'', {'Content-Length': '9999999999'})]:
            response = self.client.post('/api/theatrical/corpora/play/ingest',
                                        content=body, headers=headers)
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.store.creates, 0)

    def test_request_envelope_limit_and_validation_do_not_echo_input(self):
        from backend.security.theatrical_corpus_api import MAX_REQUEST_BYTES
        prefix = '/api/theatrical/corpora/play/ingest'
        declared = self.client.post(prefix, headers={**self.auth, 'Content-Length': '9999999999'}, content=b'')
        self.assertEqual(declared.status_code, 413, declared.text)
        # A false small Content-Length cannot bypass the actual receive-byte limit.
        actual = self.client.post(prefix, headers={**self.auth, 'Content-Length': '1'},
                                  content=b' ' * (MAX_REQUEST_BYTES + 1))
        self.assertEqual(actual.status_code, 413, actual.text)
        malformed = self.ingest(sources=[dict(source_id='../private-fixture', text='PRIVATE_TEXT')])
        self.assertEqual(malformed.status_code, 422)
        self.assertNotIn('PRIVATE', malformed.text)
        self.assertNotIn('private-fixture', malformed.text)
        self.assertEqual(malformed.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.store.creates, 0)


if __name__ == '__main__':
    unittest.main()
