"""Dedicated corpus manifests and revision selection; no production startup wiring.

The caller must own/protect the dedicated SQLite connection and Chroma root, derive
principal from verified authentication, and supply an admitted local embedder.
Neither Python objects nor document metadata establish those trust boundaries.
No model generation, general memory, tools, fallback, deletion or source rewriting.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import re
import sqlite3
import threading

from .theatrical_corpus_boundary import (
    CorpusBoundaryError, CorpusScope, retrieve_corpus_evidence,
)

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_CHUNKS = 2048
MAX_MANIFEST_BYTES = 1024 * 1024
CHUNK_CHARACTERS = 4096
_DDL = (
    'CREATE TABLE corpus_meta (version INTEGER NOT NULL)',
    'CREATE TABLE corpus_heads (owner_id TEXT NOT NULL, corpus_id TEXT NOT NULL, '
    'revision TEXT, generation INTEGER NOT NULL, PRIMARY KEY(owner_id, corpus_id))',
    'CREATE TABLE corpus_revisions (owner_id TEXT NOT NULL, corpus_id TEXT NOT NULL, '
    'revision TEXT NOT NULL, manifest_json TEXT NOT NULL, state TEXT NOT NULL '
    "CHECK(state IN ('PENDING','READY')), prior_generation INTEGER NOT NULL, "
    'PRIMARY KEY(owner_id, corpus_id, revision))',
)


def _fail(code):
    raise CorpusBoundaryError(code) from None


def _identifier(value):
    if type(value) is not str or not _ID.fullmatch(value):
        _fail('INVALID_CORPUS_INPUT')
    return value


def _digest(value):
    if type(value) is not str or not _SHA.fullmatch(value):
        _fail('INVALID_CORPUS_MANIFEST')


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def owner_for_principal(principal):
    """Stable opaque owner for an ALREADY verified server principal, never a claim."""
    if (type(principal) is not str or not 1 <= len(principal) <= 512
            or any(ord(c) < 32 or ord(c) == 127 for c in principal)):
        _fail('INVALID_CORPUS_PRINCIPAL')
    try:
        raw = principal.encode('utf-8')
    except UnicodeError:
        _fail('INVALID_CORPUS_PRINCIPAL')
    return 'principal_' + _sha(raw)


def _profile(profile, dimensions):
    _identifier(profile)
    if type(dimensions) is not int or not 1 <= dimensions <= 4096:
        _fail('INVALID_EMBEDDING_PROFILE')


def _chunk_id(source_id, source_sha, start, end, chunk_sha):
    return 'chunk_' + _sha(_json([source_id, source_sha, start, end, chunk_sha]).encode('ascii'))


@dataclass(frozen=True)
class CorpusChunk:
    chunk_id: str
    text: str
    source_id: str
    source_sha256: str
    start_byte: int
    end_byte: int
    sha256: str


@dataclass(frozen=True)
class PreparedCorpus:
    scope: CorpusScope
    manifest_json: str
    chunks: tuple[CorpusChunk, ...]


@dataclass(frozen=True)
class RegisteredCorpus:
    scope: CorpusScope
    manifest_json: str
    generation: int


def prepare_corpus(principal, corpus_id, sources, *, embedding_profile, dimensions):
    """Chunk admitted UTF-8 bytes exactly; keep source bytes out of the registry."""
    owner = owner_for_principal(principal)
    _identifier(corpus_id)
    _profile(embedding_profile, dimensions)
    if type(sources) not in (list, tuple) or not 1 <= len(sources) <= 32:
        _fail('INVALID_CORPUS_INPUT')
    seen, total, source_rows, all_chunks = set(), 0, [], []
    # Validate before sorting; never invoke untrusted object/string conversions.
    for source in sources:
        if type(source) not in (list, tuple) or len(source) != 2:
            _fail('INVALID_CORPUS_INPUT')
        source_id, raw = source
        _identifier(source_id)
        if source_id in seen or type(raw) is not bytes or not 1 <= len(raw) <= MAX_SOURCE_BYTES:
            _fail('INVALID_CORPUS_INPUT')
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            _fail('CORPUS_SIZE_LIMIT')
        seen.add(source_id)
    for source_id, raw in sorted(sources, key=lambda x: x[0]):
        try:
            text = raw.decode('utf-8', errors='strict')
        except UnicodeError:
            _fail('INVALID_CORPUS_ENCODING')
        source_sha, start, rows = _sha(raw), 0, []
        for offset in range(0, len(text), CHUNK_CHARACTERS):
            part = text[offset:offset + CHUNK_CHARACTERS]
            encoded = part.encode('utf-8')
            end, digest = start + len(encoded), _sha(encoded)
            key = _chunk_id(source_id, source_sha, start, end, digest)
            all_chunks.append(CorpusChunk(key, part, source_id, source_sha, start, end, digest))
            rows.append(dict(id=key, start_byte=start, end_byte=end, sha256=digest))
            start = end
            if len(all_chunks) > MAX_CHUNKS:
                _fail('CORPUS_SIZE_LIMIT')
        source_rows.append(dict(source_id=source_id, sha256=source_sha,
                                byte_length=len(raw), chunks=rows))
    manifest = _json(dict(schema=1, owner_id=owner, corpus_id=corpus_id,
                         embedding_profile=embedding_profile, dimensions=dimensions,
                         chunk_characters=CHUNK_CHARACTERS, sources=source_rows))
    if len(manifest.encode('ascii')) > MAX_MANIFEST_BYTES:
        _fail('CORPUS_SIZE_LIMIT')
    return PreparedCorpus(CorpusScope(owner, corpus_id, _sha(manifest.encode('ascii'))),
                          manifest, tuple(all_chunks))


def _read_manifest(record):
    raw, scope = record.manifest_json, record.scope
    if type(raw) is not str or len(raw) > MAX_MANIFEST_BYTES:
        _fail('INVALID_CORPUS_MANIFEST')
    try:
        encoded = raw.encode('ascii')
        value = json.loads(raw)
    except (UnicodeError, ValueError, RecursionError):
        _fail('INVALID_CORPUS_MANIFEST')
    if (type(value) is not dict or _sha(encoded) != scope.revision
            or _json(value) != raw or set(value) != {'schema', 'owner_id', 'corpus_id',
                'embedding_profile', 'dimensions', 'chunk_characters', 'sources'}
            or type(value['schema']) is not int or value['schema'] != 1
            or type(value['chunk_characters']) is not int
            or value['chunk_characters'] != CHUNK_CHARACTERS
            or value['owner_id'] != scope.owner_id or value['corpus_id'] != scope.corpus_id):
        _fail('INVALID_CORPUS_MANIFEST')
    _profile(value['embedding_profile'], value['dimensions'])
    sources, chunks, seen, total = value['sources'], {}, set(), 0
    if type(sources) is not list or not 1 <= len(sources) <= 32:
        _fail('INVALID_CORPUS_MANIFEST')
    for source in sources:
        if type(source) is not dict or set(source) != {'source_id', 'sha256', 'byte_length', 'chunks'}:
            _fail('INVALID_CORPUS_MANIFEST')
        sid = _identifier(source['source_id'])
        _digest(source['sha256'])
        length, entries = source['byte_length'], source['chunks']
        if (sid in seen or type(length) is not int or not 1 <= length <= MAX_SOURCE_BYTES
                or type(entries) is not list or not 1 <= len(entries) <= MAX_CHUNKS):
            _fail('INVALID_CORPUS_MANIFEST')
        seen.add(sid)
        total += length
        start = 0
        for item in entries:
            if type(item) is not dict or set(item) != {'id', 'start_byte', 'end_byte', 'sha256'}:
                _fail('INVALID_CORPUS_MANIFEST')
            _digest(item['sha256'])
            end = item['end_byte']
            if (type(item['start_byte']) is not int or item['start_byte'] != start
                    or type(end) is not int or not start < end <= min(length, start + 4 * CHUNK_CHARACTERS)):
                _fail('INVALID_CORPUS_MANIFEST')
            expected = _chunk_id(sid, source['sha256'], start, end, item['sha256'])
            if item['id'] != expected or expected in chunks:
                _fail('INVALID_CORPUS_MANIFEST')
            chunks[expected] = (sid, source['sha256'], start, end, item['sha256'])
            start = end
        if start != length:
            _fail('INVALID_CORPUS_MANIFEST')
    if total > MAX_TOTAL_BYTES or not 1 <= len(chunks) <= MAX_CHUNKS:
        _fail('INVALID_CORPUS_MANIFEST')
    return value, chunks


def _vector(vector, dimensions):
    if type(vector) not in (tuple, list) or len(vector) != dimensions:
        _fail('INVALID_QUERY_EMBEDDING')
    for number in vector:
        if type(number) not in (int, float):
            _fail('INVALID_QUERY_EMBEDDING')
        try:
            valid = math.isfinite(number) and abs(number) <= 3.4028234663852886e38
        except (OverflowError, ValueError):
            valid = False
        if not valid:
            _fail('INVALID_QUERY_EMBEDDING')


def _metadata(scope, source):
    sid, source_sha, start, end, digest = source
    return dict(owner_id=scope.owner_id, corpus_id=scope.corpus_id, revision=scope.revision,
                source_id=sid, source_sha256=source_sha, start_byte=start,
                end_byte=end, chunk_sha256=digest)


def _validate_text(key, text, chunks):
    if type(key) is not str or key not in chunks or type(text) is not str or not 1 <= len(text) <= CHUNK_CHARACTERS:
        _fail('CORPUS_CONTENT_MISMATCH')
    try:
        raw = text.encode('utf-8')
    except UnicodeError:
        _fail('CORPUS_CONTENT_MISMATCH')
    _, _, start, end, digest = chunks[key]
    if len(raw) != end - start or _sha(raw) != digest:
        _fail('CORPUS_CONTENT_MISMATCH')
    return raw


class CorpusRegistry:
    """One exclusively managed registry DB. Never point at personal/shared stores.

    sqlite commits and Chroma writes are separate. Pending attempts are retained on
    any failure; no automatic recovery, retries or deletion. Head CAS prevents a
    stale ingestion from undoing replacement/revocation. External storage ACLs,
    authenticated principals and embedding locality require independent acceptance.
    """
    def __init__(self, connection):
        if not isinstance(connection, sqlite3.Connection):
            _fail('INVALID_REGISTRY_CONNECTION')
        self.connection = connection
        self._lock = threading.RLock()
        if connection.in_transaction:
            _fail('REGISTRY_TRANSACTION_ACTIVE')
        try:
            rows = connection.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if not rows:
                with self._write():
                    for sql in _DDL:
                        connection.execute(sql)
                    connection.execute('INSERT INTO corpus_meta VALUES (1)')
            self._check_schema()
        except sqlite3.Error:
            _fail('REGISTRY_UNAVAILABLE')

    def _check_schema(self):
        rows = self.connection.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        expected = {('table', sql.split()[2], sql) for sql in _DDL}
        if set(rows) != expected or self.connection.execute('SELECT version FROM corpus_meta').fetchall() != [(1,)]:
            _fail('INVALID_REGISTRY_SCHEMA')

    @contextmanager
    def _write(self):
        with self._lock:
            if self.connection.in_transaction:
                _fail('REGISTRY_TRANSACTION_ACTIVE')
            try:
                self.connection.execute('BEGIN IMMEDIATE')
            except sqlite3.Error:
                _fail('REGISTRY_UNAVAILABLE')
            try:
                yield
                self.connection.commit()
            except BaseException as error:
                if self.connection.in_transaction:
                    self.connection.rollback()
                if isinstance(error, sqlite3.Error):
                    _fail('REGISTRY_UNAVAILABLE')
                raise

    def _stage(self, prepared):
        scope = prepared.scope
        with self._write():
            self._check_schema()
            count, size = self.connection.execute('SELECT count(*), coalesce(sum(length(manifest_json)),0) FROM corpus_revisions').fetchone()
            if count >= 1024 or size + len(prepared.manifest_json) > 64 * 1024 * 1024:
                _fail('REGISTRY_SIZE_LIMIT')
            if self.connection.execute('SELECT 1 FROM corpus_revisions WHERE owner_id=? AND corpus_id=? AND revision=?',
                    (scope.owner_id, scope.corpus_id, scope.revision)).fetchone():
                _fail('CORPUS_REVISION_EXISTS')
            self.connection.execute('INSERT OR IGNORE INTO corpus_heads VALUES (?, ?, NULL, 0)',
                                    (scope.owner_id, scope.corpus_id))
            generation = self.connection.execute('SELECT generation FROM corpus_heads WHERE owner_id=? AND corpus_id=?',
                                                  (scope.owner_id, scope.corpus_id)).fetchone()[0]
            if type(generation) is not int or not 0 <= generation < 2**63-1:
                _fail('INVALID_REGISTRY_STATE')
            self.connection.execute('INSERT INTO corpus_revisions VALUES (?, ?, ?, ?, ?, ?)',
                (scope.owner_id, scope.corpus_id, scope.revision, prepared.manifest_json, 'PENDING', generation))
        return generation

    def resolve(self, principal, corpus_id):
        owner = owner_for_principal(principal)
        _identifier(corpus_id)
        with self._lock:
            if self.connection.in_transaction:
                _fail('REGISTRY_TRANSACTION_ACTIVE')
            try:
                self._check_schema()
                row = self.connection.execute('SELECT h.revision, h.generation, r.manifest_json, r.state '
                    'FROM corpus_heads h LEFT JOIN corpus_revisions r ON h.owner_id=r.owner_id '
                    'AND h.corpus_id=r.corpus_id AND h.revision=r.revision '
                    'WHERE h.owner_id=? AND h.corpus_id=?', (owner, corpus_id)).fetchone()
            except sqlite3.Error:
                _fail('REGISTRY_UNAVAILABLE')
            if row is None or row[0] is None:
                _fail('CORPUS_NOT_AVAILABLE')
            revision, generation, manifest, state = row
            if state != 'READY' or type(generation) is not int or not 1 <= generation < 2**63:
                _fail('INVALID_REGISTRY_STATE')
            result = RegisteredCorpus(CorpusScope(owner, corpus_id, revision), manifest, generation)
            _read_manifest(result)
            return result

    def ingest(self, principal, corpus_id, sources, client, embed_documents, *, embedding_profile, dimensions):
        prepared = prepare_corpus(principal, corpus_id, sources,
                                  embedding_profile=embedding_profile, dimensions=dimensions)
        scope = prepared.scope
        generation = self._stage(prepared)
        record = RegisteredCorpus(scope, prepared.manifest_json, generation)
        manifest, chunks = _read_manifest(record)
        try:
            vectors = embed_documents([chunk.text for chunk in prepared.chunks])
        except Exception:
            _fail('CORPUS_EMBEDDING_UNAVAILABLE')
        if type(vectors) not in (list, tuple) or len(vectors) != len(chunks):
            _fail('INVALID_QUERY_EMBEDDING')
        for vector in vectors:
            _vector(vector, dimensions)
        ids = [c.chunk_id for c in prepared.chunks]
        try:
            collection = client.create_collection(name=scope.collection_name, embedding_function=None)
            if type(collection.name) is not str or collection.name != scope.collection_name:
                _fail('CORPUS_COLLECTION_MISMATCH')
            collection.add(ids=ids, documents=[c.text for c in prepared.chunks],
                           metadatas=[_metadata(scope, chunks[key]) for key in ids],
                           embeddings=[list(v) for v in vectors])
            returned = collection.get(ids=ids, include=['documents', 'metadatas'])
        except CorpusBoundaryError:
            raise
        except Exception:
            _fail('CORPUS_UNAVAILABLE')
        if type(returned) is not dict:
            _fail('INVALID_CORPUS_RESULT')
        rows = [returned.get(key) for key in ('ids', 'documents', 'metadatas')]
        if any(type(row) is not list or len(row) != len(ids) for row in rows):
            _fail('INVALID_CORPUS_RESULT')
        seen, raw_chunks = set(), {}
        for key, text, metadata in zip(*rows):
            raw = _validate_text(key, text, chunks)
            if key in seen or type(metadata) is not dict:
                _fail('INVALID_CORPUS_RESULT')
            expected = _metadata(scope, chunks[key])
            if metadata != expected or any(type(metadata.get(k)) is not type(v) for k, v in expected.items()):
                _fail('CORPUS_METADATA_MISMATCH')
            seen.add(key)
            raw_chunks[key] = raw
        for source in manifest['sources']:
            reconstructed = b''.join(raw_chunks[c['id']] for c in source['chunks'])
            if _sha(reconstructed) != source['sha256'] or len(reconstructed) != source['byte_length']:
                _fail('CORPUS_CONTENT_MISMATCH')
        with self._write():
            self._check_schema()
            changed = self.connection.execute('UPDATE corpus_heads SET revision=?, generation=generation+1 '
                'WHERE owner_id=? AND corpus_id=? AND generation=?',
                (scope.revision, scope.owner_id, scope.corpus_id, generation)).rowcount
            if changed != 1:
                _fail('CORPUS_REVISION_CONFLICT')
            changed = self.connection.execute("UPDATE corpus_revisions SET state='READY' WHERE owner_id=? "
                "AND corpus_id=? AND revision=? AND manifest_json=? AND state='PENDING' AND prior_generation=?",
                (scope.owner_id, scope.corpus_id, scope.revision, prepared.manifest_json, generation)).rowcount
            if changed != 1:
                _fail('CORPUS_REVISION_CONFLICT')
        return scope

    def retrieve(self, principal, corpus_id, client, query_embedding, *, embedding_profile, limit=3):
        record = self.resolve(principal, corpus_id)
        manifest, chunks = _read_manifest(record)
        if embedding_profile != manifest['embedding_profile']:
            _fail('CORPUS_EMBEDDING_PROFILE_MISMATCH')
        _vector(query_embedding, manifest['dimensions'])
        evidence = retrieve_corpus_evidence(client, record.scope, query_embedding, limit=limit)
        for key, text in zip(evidence.ids, evidence.documents):
            _validate_text(key, text, chunks)
        if self.resolve(principal, corpus_id) != record:
            _fail('CORPUS_REVISION_CONFLICT')
        return evidence

    def deactivate(self, principal, corpus_id, *, expected_revision):
        owner = owner_for_principal(principal)
        _identifier(corpus_id)
        _digest(expected_revision)
        with self._write():
            self._check_schema()
            changed = self.connection.execute('UPDATE corpus_heads SET revision=NULL, generation=generation+1 '
                'WHERE owner_id=? AND corpus_id=? AND revision=? AND generation<?',
                (owner, corpus_id, expected_revision, 2**63-1)).rowcount
            if changed != 1:
                _fail('CORPUS_REVISION_CONFLICT')
