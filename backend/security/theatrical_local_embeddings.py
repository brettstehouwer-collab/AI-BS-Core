"""Dormant, bounded local embedding adapter; requires independently admitted daemon.

Advertised digest checks detect observed changes, not alias races or a dishonest
daemon. Loopback does not establish process identity, immutable model storage or
daemon egress policy. This module grants none of those boundaries and enables no
Performance Mode, download, generation, fallback or production startup route.
"""
from dataclasses import dataclass
import hashlib
from http.client import HTTPConnection
import json
import math
import re
import socket
import threading
import time

from .theatrical_corpus_boundary import CorpusBoundaryError

_MODEL = 'nomic-embed-text:latest'
_OPTIONS = dict(num_gpu=0, num_thread=2, num_ctx=8192)
_MAX_RESPONSE = 1024 * 1024


def _fail(code):
    raise CorpusBoundaryError(code) from None


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('nonfinite JSON')


@dataclass(frozen=True)
class _Config:
    digest: str
    port: int
    timeout: float


class LocalNomicEmbedder:
    """Explicit CPU-only Nomic requests, one operation at a time per instance."""

    def __init__(self, *, expected_digest, port=11434, timeout_seconds=60):
        if (type(expected_digest) is not str
                or not re.fullmatch('[0-9a-f]{64}', expected_digest)
                or type(port) is not int or port not in (11434, 11435)
                or type(timeout_seconds) not in (int, float)
                or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300):
            _fail('INVALID_EMBEDDING_CONFIG')
        self._config = _Config(expected_digest, port, float(timeout_seconds))
        self._gate = threading.BoundedSemaphore(1)
        profile = dict(version=1, model=_MODEL, digest=expected_digest, port=port,
                       dimensions=768, document_prefix='search_document: ',
                       query_prefix='search_query: ', truncate=False, keep_alive='0s',
                       options=_OPTIONS, vector_policy='finite_nonzero_raw_float32')
        self._profile = 'nomic_v1_' + hashlib.sha256(json.dumps(
            profile, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()

    @property
    def embedding_profile(self):
        return self._profile

    @property
    def dimensions(self):
        return 768

    def _request_json(self, method, path, payload, deadline):
        """Fixed numeric loopback, no proxies/redirects; bounded JSON and deadline."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _fail('EMBEDDING_UNAVAILABLE')
        connection = HTTPConnection('127.0.0.1', self._config.port, timeout=remaining)
        timer = None
        expired = threading.Event()
        try:
            connection.connect()
            owned_socket = connection.sock

            def expire():
                expired.set()
                try:
                    owned_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                finally:
                    owned_socket.close()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail('EMBEDDING_UNAVAILABLE')
            timer = threading.Timer(remaining, expire)
            timer.daemon = True
            timer.start()
            body = None if payload is None else json.dumps(
                payload, ensure_ascii=True, allow_nan=False,
                separators=(',', ':')).encode('ascii')
            # Eight admitted 4096-character strings can expand to twelve ASCII
            # bytes per non-BMP character under JSON surrogate escaping.
            if body is not None and len(body) > 512 * 1024:
                _fail('INVALID_EMBEDDING_INPUT')
            connection.request(method, path, body=body, headers={
                'Content-Type': 'application/json', 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            if (response.status != 200
                    or response.getheader('Content-Type', '').split(';', 1)[0].strip().lower()
                    != 'application/json'
                    or response.getheader('Content-Encoding', 'identity').lower() != 'identity'):
                _fail('EMBEDDING_UNAVAILABLE')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isascii() or not length.isdecimal()
                                       or int(length) > _MAX_RESPONSE):
                _fail('INVALID_EMBEDDING_RESPONSE')
            chunks, count = [], 0
            while True:
                if expired.is_set() or time.monotonic() >= deadline:
                    _fail('EMBEDDING_UNAVAILABLE')
                chunk = response.read1(min(65536, _MAX_RESPONSE + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
                if count > _MAX_RESPONSE:
                    _fail('INVALID_EMBEDDING_RESPONSE')
            if (expired.is_set() or time.monotonic() >= deadline
                    or length is not None and count != int(length)):
                _fail('EMBEDDING_UNAVAILABLE')
            value = json.loads(b''.join(chunks).decode('utf-8'),
                               object_pairs_hook=_pairs, parse_constant=_constant)
            if type(value) is not dict:
                _fail('INVALID_EMBEDDING_RESPONSE')
            return value
        except CorpusBoundaryError:
            raise
        except Exception:
            _fail('EMBEDDING_UNAVAILABLE')
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            connection.close()

    def _tags(self, deadline):
        data = self._request_json('GET', '/api/tags', None, deadline)
        models = data.get('models')
        if type(models) is not list or len(models) > 4096:
            _fail('EMBEDDING_MODEL_MISMATCH')
        matches = [item for item in models if type(item) is dict and item.get('name') == _MODEL]
        if len(matches) != 1 or matches[0].get('digest') != self._config.digest:
            _fail('EMBEDDING_MODEL_MISMATCH')

    def _verify_model(self, deadline):
        self._tags(deadline)
        data = self._request_json('POST', '/api/show', {'model': _MODEL}, deadline)
        details = data.get('details')
        if (data.get('capabilities') != ['embedding'] or data.get('remote_model')
                or data.get('remote_host') or type(details) is not dict
                or details.get('family') != 'nomic-bert' or details.get('format') != 'gguf'
                or details.get('parent_model')):
            _fail('EMBEDDING_MODEL_MISMATCH')

    @staticmethod
    def _validate(texts):
        if type(texts) is not list or not 1 <= len(texts) <= 2048:
            _fail('INVALID_EMBEDDING_INPUT')
        total = 0
        for text in texts:
            if type(text) is not str or not 1 <= len(text) <= 4096:
                _fail('INVALID_EMBEDDING_INPUT')
            try:
                size = len(text.encode('utf-8'))
            except UnicodeError:
                _fail('INVALID_EMBEDDING_INPUT')
            total += size
            if size > 16384 or total > 8 * 1024 * 1024:
                _fail('INVALID_EMBEDDING_INPUT')

    @staticmethod
    def _vectors(data, count):
        vectors = data.get('embeddings')
        if (data.get('model') != _MODEL or type(vectors) is not list
                or len(vectors) != count):
            _fail('INVALID_EMBEDDING_RESPONSE')
        result = []
        for vector in vectors:
            if type(vector) is not list or len(vector) != 768:
                _fail('INVALID_EMBEDDING_RESPONSE')
            converted = []
            for value in vector:
                if (type(value) not in (int, float) or not -3.402823466e38 <= value <= 3.402823466e38
                        or not math.isfinite(value)):
                    _fail('INVALID_EMBEDDING_RESPONSE')
                converted.append(float(value))
            if not any(converted):
                _fail('INVALID_EMBEDDING_RESPONSE')
            result.append(converted)
        return result

    def _embed(self, texts, prefix):
        # Copy the caller's list before I/O; source strings themselves are immutable.
        if type(texts) is list:
            texts = texts.copy()
        self._validate(texts)
        if not self._gate.acquire(blocking=False):
            _fail('EMBEDDING_BUSY')
        try:
            deadline = time.monotonic() + self._config.timeout
            self._verify_model(deadline)
            result = []
            for offset in range(0, len(texts), 8):
                batch = texts[offset:offset + 8]
                data = self._request_json('POST', '/api/embed', dict(
                    model=_MODEL, input=[prefix + text for text in batch], truncate=False,
                    keep_alive='0s', options=_OPTIONS.copy()), deadline)
                result.extend(self._vectors(data, len(batch)))
                self._tags(deadline)
            return result
        except CorpusBoundaryError:
            raise
        except Exception:
            _fail('EMBEDDING_UNAVAILABLE')
        finally:
            self._gate.release()

    def embed_documents(self, texts):
        return self._embed(texts, 'search_document: ')

    def embed_query(self, text):
        if type(text) is not str:
            _fail('INVALID_EMBEDDING_INPUT')
        return self._embed([text], 'search_query: ')[0]
