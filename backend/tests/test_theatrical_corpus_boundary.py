"""Synthetic retrieval-boundary tests; no real store/model or feature activation."""
import copy
import math
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

from backend.security.theatrical_corpus_boundary import (
    CorpusBoundaryError, CorpusScope, retrieve_corpus_evidence,
)


class CorpusBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scope = CorpusScope('owner-A', 'play-A', 'a' * 64)
        self.metadata = dict(owner_id='owner-A', corpus_id='play-A', revision='a' * 64)
        self.response = dict(ids=[['part-1']], documents=[['SYNTHETIC AUTHORIZED LINE']],
                             metadatas=[[self.metadata]])
        self.collection = Mock()
        self.collection.name = self.scope.collection_name
        self.collection.query.return_value = self.response
        self.client = Mock()
        self.client.get_collection.return_value = self.collection

    def retrieve(self, **kwargs):
        return retrieve_corpus_evidence(self.client, self.scope, [0.1, 0.2], **kwargs)

    def test_exact_collection_and_all_filters(self):
        result = self.retrieve()
        self.client.get_collection.assert_called_once_with(name=self.scope.collection_name)
        self.collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2]], n_results=3,
            where={'$and': [{'owner_id': 'owner-A'}, {'corpus_id': 'play-A'}, {'revision': 'a' * 64}]},
            include=['documents', 'metadatas'])
        self.assertEqual(result.documents, ('SYNTHETIC AUTHORIZED LINE',))
        self.client.get_or_create_collection.assert_not_called()
        self.client.create_collection.assert_not_called()

    def test_collection_changes_with_each_scope_dimension(self):
        scopes = [self.scope, CorpusScope('owner-B', 'play-A', 'a'*64),
                  CorpusScope('owner-A', 'play-B', 'a'*64), CorpusScope('owner-A', 'play-A', 'b'*64)]
        self.assertEqual(len({s.collection_name for s in scopes}), 4)
        self.assertTrue(all(s.collection_name.startswith('theatre_') for s in scopes))

    def test_scope_validation(self):
        for args in [('', 'p', 'a'*64), (' a', 'p', 'a'*64), ('a', '../p', 'a'*64),
                     ('a', 'p', 'latest'), ('a', 'p', 'A'*64), ('a'*129, 'p', 'a'*64),
                     (1, 'p', 'a'*64)]:
            with self.subTest(args=args), self.assertRaises(CorpusBoundaryError):
                CorpusScope(*args)

    def test_scope_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.scope.owner_id = 'other'

    def test_wrong_collection_rejected_before_query(self):
        self.collection.name = 'ai_bs_context_memory'
        with self.assertRaises(CorpusBoundaryError): self.retrieve()
        self.collection.query.assert_not_called()

    def test_foreign_metadata_rejects_entire_result(self):
        for key in self.metadata:
            with self.subTest(key=key):
                response = copy.deepcopy(self.response)
                response['metadatas'][0][0][key] = 'FOREIGN CANARY'
                self.collection.query.return_value = response
                with self.assertRaises(CorpusBoundaryError) as error: self.retrieve()
                self.assertNotIn('CANARY', str(error.exception))

    def test_missing_or_malformed_metadata(self):
        for value in [None, {}, [], dict(self.metadata, revision=None)]:
            with self.subTest(value=value):
                response = copy.deepcopy(self.response)
                response['metadatas'] = [[value]]
                self.collection.query.return_value = response
                with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_mixed_authorized_and_foreign_rejected(self):
        self.collection.query.return_value = dict(ids=[['one','two']], documents=[['OK','FOREIGN']],
            metadatas=[[self.metadata, dict(self.metadata, corpus_id='other')]])
        with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_empty_result_is_explicit_evidence(self):
        self.collection.query.return_value = dict(ids=[[]], documents=[[]], metadatas=[[]])
        result = self.retrieve()
        self.assertEqual(result.documents, ())
        self.assertFalse(result.has_evidence)

    def test_response_shape(self):
        for response in [None, {}, {'ids':[]}, dict(self.response, documents=[]),
                         dict(self.response, ids=[['one'], ['two']]),
                         dict(self.response, documents=[[]])]:
            with self.subTest(response=response):
                self.collection.query.return_value = response
                with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_duplicate_and_invalid_ids(self):
        for ids in [['one','one'], [''], [None], ['x'*257]]:
            with self.subTest(ids=ids):
                self.collection.query.return_value = dict(ids=[ids],
                    documents=[['OK']*len(ids)], metadatas=[[self.metadata]*len(ids)])
                with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_text_and_result_bounds(self):
        for docs in [[''], [None], ['x'*65537], ['x']*4]:
            with self.subTest(docs=docs):
                self.collection.query.return_value = dict(ids=[[str(i) for i in range(len(docs))]],
                    documents=[docs], metadatas=[[self.metadata]*len(docs)])
                with self.assertRaises(CorpusBoundaryError): self.retrieve()

    def test_provider_failure_sanitized_and_no_retry(self):
        for target in [self.client.get_collection, self.collection.query]:
            with self.subTest(target=target):
                target.side_effect = RuntimeError('PRIVATE DOCUMENT / CREDENTIAL')
                with self.assertRaises(CorpusBoundaryError) as error: self.retrieve()
                self.assertEqual(str(error.exception), 'CORPUS_UNAVAILABLE')
                self.assertIsNone(error.exception.__cause__)
                target.side_effect = None
        self.assertEqual(self.client.get_collection.call_count, 2)
        self.assertEqual(self.collection.query.call_count, 1)

    def test_embeddings_validated_before_store(self):
        for vector in [[], [True], ['0.1'], [math.nan], [math.inf], [0]*4097, None]:
            with self.subTest(vector=vector), self.assertRaises(CorpusBoundaryError):
                retrieve_corpus_evidence(self.client, self.scope, vector)
        self.client.get_collection.assert_not_called()

    def test_limit_validated_before_store(self):
        for limit in [0, 11, True, 1.5, '3']:
            with self.subTest(limit=limit), self.assertRaises(CorpusBoundaryError):
                self.retrieve(limit=limit)
        self.client.get_collection.assert_not_called()

    def test_evidence_is_detached_and_frozen(self):
        evidence = self.retrieve()
        self.response['documents'][0][0] = 'MUTATED'
        self.assertEqual(evidence.documents, ('SYNTHETIC AUTHORIZED LINE',))
        with self.assertRaises(FrozenInstanceError): evidence.documents = ()


if __name__ == '__main__':
    unittest.main()
