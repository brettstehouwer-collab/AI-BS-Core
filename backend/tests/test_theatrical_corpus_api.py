"""In-process authenticated HTTP contract; synthetic local key, no live services."""
import os
import sqlite3
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.security.theatrical_corpus_api import create_theatrical_corpus_router
from backend.security.theatrical_corpus_registry import CorpusRegistry
from backend.tests.test_theatrical_corpus_registry import Store


class CorpusApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'AI_BS_ADMIN_KEY': 'synthetic-private-test-key', 'AI_BS_ADMIN_EMAILS': '',
        })
        self.environment.start()
        self.connection = sqlite3.connect(':memory:', check_same_thread=False)
        self.registry = CorpusRegistry(self.connection)
        self.store = Store()
        self.embedder = Mock()
        self.embedder.embed_documents.side_effect = lambda texts: [[0.25, 0.75] for _ in texts]
        self.embedder.embed_query.return_value = [0.25, 0.75]
        app = FastAPI()
        app.include_router(create_theatrical_corpus_router(
            self.registry, self.store, self.embedder,
            embedding_profile='local-fixture-v1', dimensions=2))
        self.client = TestClient(app)
        self.auth = {'X-Admin-Key': 'synthetic-private-test-key'}

    def tearDown(self):
        self.client.close()
        self.connection.close()
        self.environment.stop()

    def ingest(self, **kwargs):
        return self.client.post('/api/theatrical/corpora/play/ingest', headers=self.auth,
            json=kwargs or dict(sources=[dict(source_id='script', text='SYNTHETIC\r\n')]))

    def query(self, **kwargs):
        return self.client.post('/api/theatrical/corpora/play/evidence', headers=self.auth,
                                json=kwargs or dict(query='Which line?', limit=3))

    def test_real_auth_dependency_rejects_absent_wrong_and_claimed_owner(self):
        for headers in [{}, {'X-Admin-Key': 'wrong'}, {'X-Client-ID': 'local_admin'},
                        {'Authorization': 'Bearer invalid'}]:
            response = self.client.post('/api/theatrical/corpora/play/ingest', headers=headers,
                        json=dict(sources=[dict(source_id='s', text='unauthorized')]))
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.creates, 0)
        self.embedder.embed_documents.assert_not_called()

    def test_local_admin_ingest_and_evidence_preserve_bytes_and_provenance(self):
        response = self.ingest()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['capability'], 'evidence_only')
        result = self.query()
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertFalse(body['model_execution'])
        self.assertEqual(body['evidence'][0]['text'], 'SYNTHETIC\r\n')
        self.assertEqual(body['evidence'][0]['source_id'], 'script')
        self.assertEqual(body['evidence'][0]['start_byte'], 0)
        self.assertEqual(body['revision'], response.json()['revision'])

    def test_body_cannot_select_owner_revision_profile_or_vectors(self):
        self.ingest()
        for field, value in [('owner_id', 'foreign'), ('revision', 'a'*64),
                             ('query_embedding', [1, 2]), ('embedding_profile', 'remote')]:
            response = self.query(**dict(query='q', **{field: value}))
            self.assertEqual(response.status_code, 422, response.text)
        self.embedder.embed_query.assert_not_called()
        self.assertEqual(self.ingest(sources=[dict(source_id='s', text='x')], owner_id='other').status_code, 422)

    def test_verified_firebase_owner_cannot_see_local_admin_corpus(self):
        self.ingest()
        with patch('backend.security.theatrical_corpus_api.get_admin_principal', return_value='firebase:project:other'):
            response = self.query()
        self.assertEqual(response.status_code, 404, response.text)
        self.embedder.embed_query.assert_not_called()

    def test_status_and_deactivate_use_current_exact_revision(self):
        created = self.ingest().json()
        status = self.client.get('/api/theatrical/corpora/play/status', headers=self.auth)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()['chunk_count'], 1)
        denied = self.client.post('/api/theatrical/corpora/play/deactivate', headers=self.auth,
                                  json=dict(expected_revision='a'*64))
        self.assertEqual(denied.status_code, 409)
        deactivated = self.client.post('/api/theatrical/corpora/play/deactivate', headers=self.auth,
                                      json=dict(expected_revision=created['revision']))
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertEqual(self.query().status_code, 404)
        self.assertEqual(len(self.store.collections), 1)

    def test_missing_corpus_and_provider_failure_are_truthful(self):
        self.assertEqual(self.query().status_code, 404)
        self.embedder.embed_query.assert_not_called()
        self.ingest()
        self.embedder.embed_query.side_effect = RuntimeError('PRIVATE_RAW_EXCEPTION')
        result = self.query()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('PRIVATE_RAW_EXCEPTION', result.text)
        self.assertNotIn('SYNTHETIC', result.text)

    def test_invalid_prompt_limits_sources_and_paths(self):
        for payload in [dict(query=''), dict(query='q', limit=True), dict(query='x'*4097),
                        dict(query='q', limit=11)]:
            response = self.query(**payload)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.ingest(sources=[]).status_code, 422)
        self.assertEqual(self.ingest(sources=[dict(source_id='../s', text='x')]).status_code, 422)
        self.assertEqual(self.ingest(sources=[dict(source_id='s', text=12)]).status_code, 422)


if __name__ == '__main__': unittest.main()
