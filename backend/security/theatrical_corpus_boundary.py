"""Read-only corpus retrieval prerequisite, deliberately not wired to live routes.

Callers must authenticate and choose scope from their own admitted registry. This
module provides neither that authority nor model/history/tool/cache isolation.
It imports no store/model clients and cannot certify a provider's filtering.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re


class CorpusBoundaryError(ValueError):
    """Public errors contain fixed codes only, never provider/content details."""


_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_REVISION = re.compile(r'[0-9a-f]{64}\Z')


@dataclass(frozen=True)
class CorpusScope:
    owner_id: str
    corpus_id: str
    revision: str

    def __post_init__(self):
        if any(type(v) is not str or not _IDENTIFIER.fullmatch(v)
               for v in (self.owner_id, self.corpus_id)):
            raise CorpusBoundaryError('INVALID_CORPUS_SCOPE')
        if type(self.revision) is not str or not _REVISION.fullmatch(self.revision):
            raise CorpusBoundaryError('INVALID_CORPUS_SCOPE')

    @property
    def collection_name(self):
        key = json.dumps([self.owner_id, self.corpus_id, self.revision],
                         ensure_ascii=True, separators=(',', ':')).encode('ascii')
        return 'theatre_' + hashlib.sha256(key).hexdigest()[:48]


@dataclass(frozen=True)
class CorpusEvidence:
    scope: CorpusScope
    ids: tuple[str, ...]
    documents: tuple[str, ...]

    @property
    def has_evidence(self):
        return bool(self.documents)


def retrieve_corpus_evidence(client, scope, query_embedding, *, limit=3):
    """Query an existing exact collection once; validate the entire response.

    Embeddings must be supplied explicitly. No text embedding request, count,
    collection creation, fallback, retry, history, model or write is performed.
    Scope metadata checks prevent mixed-scope provider responses from entering
    evidence; metadata provenance and store integrity need separate enforcement.
    """
    if type(scope) is not CorpusScope:
        raise CorpusBoundaryError('INVALID_CORPUS_SCOPE')
    # Revalidate even instances restored through mechanisms bypassing __init__.
    CorpusScope(scope.owner_id, scope.corpus_id, scope.revision)
    if type(limit) is not int or not 1 <= limit <= 10:
        raise CorpusBoundaryError('INVALID_RETRIEVAL_LIMIT')
    if type(query_embedding) not in (list, tuple) or not 1 <= len(query_embedding) <= 4096:
        raise CorpusBoundaryError('INVALID_QUERY_EMBEDDING')
    for value in query_embedding:
        if type(value) not in (int, float):
            raise CorpusBoundaryError('INVALID_QUERY_EMBEDDING')
        try:
            valid = math.isfinite(value)
        except (OverflowError, ValueError):
            valid = False
        if not valid:
            raise CorpusBoundaryError('INVALID_QUERY_EMBEDDING')

    try:
        collection = client.get_collection(name=scope.collection_name)
        name = collection.name
    except Exception:
        raise CorpusBoundaryError('CORPUS_UNAVAILABLE') from None
    if type(name) is not str or name != scope.collection_name:
        raise CorpusBoundaryError('CORPUS_COLLECTION_MISMATCH')

    metadata = dict(owner_id=scope.owner_id, corpus_id=scope.corpus_id, revision=scope.revision)
    try:
        response = collection.query(
            query_embeddings=[list(query_embedding)], n_results=limit,
            where={'$and': [{key: value} for key, value in metadata.items()]},
            include=['documents', 'metadatas'])
    except Exception:
        raise CorpusBoundaryError('CORPUS_UNAVAILABLE') from None

    if type(response) is not dict:
        raise CorpusBoundaryError('INVALID_CORPUS_RESULT')
    rows = []
    for key in ('ids', 'documents', 'metadatas'):
        value = response.get(key)
        if type(value) is not list or len(value) != 1 or type(value[0]) is not list:
            raise CorpusBoundaryError('INVALID_CORPUS_RESULT')
        rows.append(value[0])
    ids, documents, metadatas = rows
    if len(ids) > limit or len(ids) != len(documents) or len(ids) != len(metadatas):
        raise CorpusBoundaryError('INVALID_CORPUS_RESULT')
    seen = set()
    for doc_id, document, item in zip(ids, documents, metadatas):
        if type(doc_id) is not str or not 1 <= len(doc_id) <= 256 or doc_id in seen:
            raise CorpusBoundaryError('INVALID_CORPUS_RESULT')
        seen.add(doc_id)
        if type(document) is not str or not 1 <= len(document) <= 65536:
            raise CorpusBoundaryError('INVALID_CORPUS_RESULT')
        if type(item) is not dict or any(
            type(item.get(key)) is not str or item[key] != value
            for key, value in metadata.items()
        ):
            raise CorpusBoundaryError('CORPUS_METADATA_MISMATCH')
    return CorpusEvidence(scope, tuple(ids), tuple(documents))
