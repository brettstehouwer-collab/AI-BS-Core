"""Disposable synthetic registry fixtures; no production data or models."""
import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.security.theatrical_corpus_registry import (
    CorpusRegistry, prepare_corpus, owner_for_principal,
)


class Collection:
    def __init__(self, name):
        self.name = name
        self.rows = {}
        self.fail_add = False

    def add(self, *, ids, documents, metadatas, embeddings):
        if self.fail_add:
            raise RuntimeError('PRIVATE_PROVIDER_FAILURE')
        for values in zip(ids, documents, metadatas, embeddings):
            key, doc, meta, vector = values
            self.rows[key] = (doc, copy.deepcopy(meta), list(vector))

    def get(self, *, ids, include):
        keys = [key for key in reversed(ids) if key in self.rows]
        return dict(ids=keys, documents=[self.rows[k][0] for k in keys],
                    metadatas=[copy.deepcopy(self.rows[k][1]) for k in keys])

    def query(self, **kwargs):
        keys = list(self.rows)[:kwargs['n_results']]
        return dict(ids=[keys], documents=[[self.rows[k][0] for k in keys]],
                    metadatas=[[copy.deepcopy(self.rows[k][1]) for k in keys]])


class Store:
    def __init__(self):
        self.collections = {}
        self.creates = 0
        self.after_create = None

    def create_collection(self, *, name, embedding_function):
        assert embedding_function is None
        self.creates += 1
        if name in self.collections:
            raise RuntimeError('exists')
        result = Collection(name)
        self.collections[name] = result
        if self.after_create:
            self.after_create(result)
        return result

    def get_collection(self, *, name):
        return self.collections[name]


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(':memory:')
        self.registry = CorpusRegistry(self.connection)
        self.store = Store()
        self.embed = Mock(side_effect=lambda texts: [[0.25, 0.75] for _ in texts])
        self.sources = [('script', b'INT. ROOM\r\nSYNTHETIC LINE\r\n')]

    def tearDown(self):
        self.connection.close()

    def publish(self, principal='local_admin', corpus='play', sources=None, **kwargs):
        return self.registry.ingest(
            principal, corpus, self.sources if sources is None else sources,
            self.store, self.embed, embedding_profile='local-fixture-v1', dimensions=2,
            **kwargs)

    def retrieve(self, principal='local_admin', corpus='play'):
        return self.registry.retrieve(principal, corpus, self.store, [0.25, 0.75],
                                      embedding_profile='local-fixture-v1')

    def test_original_bytes_and_deterministic_manifest(self):
        raw = b'\xef\xbb\xbfINT. ROOM\r\n' + ('Cafe\u0301 \U0001f3ad\n' * 1100).encode()
        p = prepare_corpus('firebase:project:subject', 'play', [('script', raw)],
                           embedding_profile='local-fixture-v1', dimensions=2)
        self.assertEqual(b''.join(c.text.encode('utf-8') for c in p.chunks), raw)
        manifest = json.loads(p.manifest_json)
        self.assertEqual(manifest['sources'][0]['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(p.scope.revision, hashlib.sha256(p.manifest_json.encode()).hexdigest())
        self.assertEqual(p.scope.owner_id, owner_for_principal('firebase:project:subject'))
        self.assertNotIn('firebase:project:subject', p.manifest_json)
        self.assertEqual(p, prepare_corpus('firebase:project:subject', 'play', [('script', raw)],
                                          embedding_profile='local-fixture-v1', dimensions=2))

    def test_owner_corpus_profile_and_bytes_change_revision(self):
        def rev(principal='a', corpus='p', raw=b'x', profile='model', dims=2):
            return prepare_corpus(principal, corpus, [('s', raw)],
                                  embedding_profile=profile, dimensions=dims).scope.revision
        self.assertEqual(len({rev(), rev(principal='b'), rev(corpus='q'), rev(raw=b'x\n'),
                              rev(profile='model2'), rev(dims=3)}), 6)

    def test_invalid_inputs_before_registry_or_embed(self):
        invalid = [[], [('x', b'')], [('x', b'\xff')], [('x', 'text')],
                   [('x', b'a'), ('x', b'b')], [('../file', b'a')],
                   [('x', b'a' * (2 * 1024 * 1024 + 1))]]
        for sources in invalid:
            with self.subTest(sources_type=type(sources)), self.assertRaises(CorpusBoundaryError):
                self.publish(sources=sources)
        self.assertEqual(self.store.creates, 0)
        self.embed.assert_not_called()
        self.assertEqual(self.connection.execute('select count(*) from corpus_revisions').fetchone()[0], 0)
        for principal in ['', 'x\n', None, 'x'*513]:
            with self.assertRaises(CorpusBoundaryError): self.publish(principal=principal)

    def test_ingest_readback_then_retrieve(self):
        scope = self.publish()
        evidence = self.retrieve()
        self.assertEqual(scope, evidence.scope)
        self.assertEqual(evidence.documents, (self.sources[0][1].decode(),))
        self.assertEqual(self.registry.resolve('local_admin', 'play').scope, scope)

    def test_cross_owner_and_corpus_never_query(self):
        self.publish()
        for args in [('other_admin', 'play'), ('local_admin', 'other')]:
            with self.assertRaises(CorpusBoundaryError) as error:
                self.retrieve(*args)
            self.assertEqual(str(error.exception), 'CORPUS_NOT_AVAILABLE')

    def test_new_revision_and_revoke_never_fallback(self):
        first = self.publish()
        second = self.publish(sources=[('script', b'SECOND REVISION')])
        self.assertNotEqual(first, second)
        self.assertEqual(self.retrieve().documents, ('SECOND REVISION',))
        self.registry.deactivate('local_admin', 'play', expected_revision=second.revision)
        with self.assertRaises(CorpusBoundaryError): self.retrieve()
        self.assertEqual(len(self.store.collections), 2)
        self.assertEqual(self.connection.execute('select count(*) from corpus_revisions').fetchone()[0], 2)

    def test_pending_failed_add_preserves_old_head_and_evidence(self):
        original = self.publish()
        self.store.after_create = lambda collection: setattr(collection, 'fail_add', True)
        with self.assertRaises(CorpusBoundaryError) as error:
            self.publish(sources=[('script', b'FAILED CANDIDATE')])
        self.assertNotIn('PRIVATE_PROVIDER', str(error.exception))
        self.assertEqual(self.registry.resolve('local_admin', 'play').scope, original)
        self.assertEqual(self.connection.execute("select count(*) from corpus_revisions where state='PENDING'").fetchone()[0], 1)
        self.assertEqual(len(self.store.collections), 2)

    def test_ingestion_readback_corruption_does_not_activate(self):
        def corrupt(collection):
            old = collection.get
            def changed(**kwargs):
                result = old(**kwargs)
                result['documents'][0] = 'FOREIGN CONTENT'
                return result
            collection.get = changed
        self.store.after_create = corrupt
        with self.assertRaises(CorpusBoundaryError): self.publish()
        with self.assertRaises(CorpusBoundaryError): self.registry.resolve('local_admin', 'play')

    def test_changed_document_with_correct_scope_rejected(self):
        scope = self.publish()
        collection = self.store.collections[scope.collection_name]
        key = next(iter(collection.rows))
        _, metadata, vector = collection.rows[key]
        collection.rows[key] = ('FOREIGN CONTENT', metadata, vector)
        with self.assertRaises(CorpusBoundaryError) as error: self.retrieve()
        self.assertEqual(str(error.exception), 'CORPUS_CONTENT_MISMATCH')

    def test_unknown_chunk_id_and_partial_scope_rejected(self):
        scope = self.publish()
        collection = self.store.collections[scope.collection_name]
        key = next(iter(collection.rows))
        collection.rows['forged'] = collection.rows.pop(key)
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_bad_embedding_before_collection_creation_retains_pending(self):
        self.embed.side_effect = lambda texts: [[float('nan'), 1] for _ in texts]
        with self.assertRaises(CorpusBoundaryError): self.publish()
        self.assertEqual(self.store.creates, 0)
        self.assertEqual(self.connection.execute("select state from corpus_revisions").fetchone()[0], 'PENDING')

    def test_profile_dimension_and_unknown_collection_fail_closed(self):
        scope = self.publish()
        for vector, profile in [([1], 'local-fixture-v1'), ([1, 2], 'remote-other')]:
            with self.assertRaises(CorpusBoundaryError):
                self.registry.retrieve('local_admin', 'play', self.store, vector, embedding_profile=profile)
        del self.store.collections[scope.collection_name]
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_duplicate_attempt_retains_existing_revision(self):
        self.publish()
        with self.assertRaises(CorpusBoundaryError): self.publish()
        self.assertEqual(self.store.creates, 1)
        self.assertEqual(self.retrieve().documents[0], self.sources[0][1].decode())

    def test_head_cas_blocks_candidate_after_revocation(self):
        original = self.publish()
        self.store.after_create = lambda c: self.registry.deactivate(
            'local_admin', 'play', expected_revision=original.revision)
        with self.assertRaises(CorpusBoundaryError) as error:
            self.publish(sources=[('script', b'CONCURRENT CANDIDATE')])
        self.assertEqual(str(error.exception), 'CORPUS_REVISION_CONFLICT')
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_revoked_during_query_discards_result(self):
        scope = self.publish()
        collection = self.store.collections[scope.collection_name]
        original = collection.query
        def revoke(**kwargs):
            result = original(**kwargs)
            self.registry.deactivate('local_admin', 'play', expected_revision=scope.revision)
            return result
        collection.query = revoke
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_registry_reopen_restores_manifest_and_head(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'corpus.db'
            first = sqlite3.connect(path)
            reg = CorpusRegistry(first)
            scope = reg.ingest('owner', 'play', self.sources, self.store, self.embed,
                               embedding_profile='local-fixture-v1', dimensions=2)
            first.close()
            second = sqlite3.connect(path)
            try:
                self.assertEqual(CorpusRegistry(second).resolve('owner', 'play').scope, scope)
            finally: second.close()

    def test_unknown_schema_and_caller_transaction_preserved(self):
        other = sqlite3.connect(':memory:')
        try:
            other.execute('create table private_data(x)')
            with self.assertRaises(CorpusBoundaryError): CorpusRegistry(other)
            self.assertEqual(other.execute("select name from sqlite_master where type='table'").fetchall(), [('private_data',)])
            other.execute('insert into private_data values (1)')
            with self.assertRaises(CorpusBoundaryError): CorpusRegistry(other)
            self.assertTrue(other.in_transaction)
            self.assertEqual(other.execute('select x from private_data').fetchone(), (1,))
        finally: other.close()

    def test_existing_registry_transaction_is_not_committed_or_rolled_back(self):
        self.connection.execute("insert into corpus_heads values ('owner', 'corpus', NULL, 0)")
        with self.assertRaises(CorpusBoundaryError): self.publish()
        self.assertTrue(self.connection.in_transaction)
        self.connection.rollback()

    def test_manifest_disk_tampering_rejected_before_store(self):
        self.publish()
        self.connection.execute("update corpus_revisions set manifest_json='{}'")
        self.connection.commit()
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_wrong_expected_revocation_cannot_change_head(self):
        scope = self.publish()
        with self.assertRaises(CorpusBoundaryError):
            self.registry.deactivate('local_admin', 'play', expected_revision='0'*64)
        self.assertEqual(self.registry.resolve('local_admin', 'play').scope, scope)


if __name__ == '__main__': unittest.main()
