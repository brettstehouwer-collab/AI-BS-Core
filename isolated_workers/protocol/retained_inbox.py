"""Retain authenticated packets and their replay claims in one SQLite commit.

The caller supplies an idle, persistent, dedicated connection with protected
storage. This module chooses no filesystem path and provides no socket, task
execution, worker admission or application authority. Recovery returns retained
bytes/receipts as data only; it never replays a packet through the codec.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import re
import sqlite3
import threading

from . import scoped_exchange as codec
from .replay_claims import _persistent, _rows

MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_PACKETS = 256
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024

PACKET_SCHEMA = 'CREATE TABLE retained_packets_v1 (worker TEXT NOT NULL, direction TEXT NOT NULL, nonce TEXT NOT NULL, packet_sha256 TEXT NOT NULL, packet_bytes INTEGER NOT NULL, expires INTEGER NOT NULL, packet BLOB NOT NULL, PRIMARY KEY(worker,direction,nonce)) WITHOUT ROWID'
CONFIG_SCHEMA = 'CREATE TABLE retained_inbox_config_v1 (version INTEGER PRIMARY KEY, packet_limit INTEGER NOT NULL, payload_limit INTEGER NOT NULL)'
EXPECTED_SCHEMA = [('table', 'retained_inbox_config_v1', CONFIG_SCHEMA),
                   ('table', 'retained_packets_v1', PACKET_SCHEMA)]


class InboxRejected(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise InboxRejected(code)


def _scope(worker, direction, nonce):
    _require(type(worker) is str and re.fullmatch('[A-Za-z0-9_:.-]{1,128}', worker) is not None,
             'WORKER_SCOPE_REQUIRED')
    _require(direction in ('host_to_guest', 'guest_to_host'), 'DIRECTION_SCOPE_REQUIRED')
    _require(type(nonce) is str and re.fullmatch('[a-f0-9]{32}', nonce) is not None,
             'NONCE_SCOPE_REQUIRED')


def _digest(value):
    _require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None,
             'PACKET_DIGEST_REQUIRED')


@dataclass(frozen=True)
class RetainedReceipt:
    worker: str
    direction: str
    nonce: str
    packet_sha256: str
    packet_bytes: int
    expires: int
    state: str = field(default='RETAINED', init=False)
    worker_admitted: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    apply_authorized: bool = field(default=False, init=False)
    verification_status: str = field(default='not_run', init=False)


@dataclass(frozen=True)
class RetainedDelivery:
    bundle: codec.VerifiedBundle
    receipt: RetainedReceipt


class RetainedInbox:
    """One dedicated connection, serialized per instance; no pruning or migration.

    Quotas count retained packet BLOB payload bytes, not SQLite pages, journals,
    filesystem allocation or a universal disk-space limit. External storage/root
    protection, lifecycle recovery policy and execution grants remain separate.
    Connection.commit() must end explicit transactions; unsupported explicit
    autocommit modes are refused rather than reported as durable acceptance.
    """
    def __init__(self, connection, create=False, packet_limit=MAX_PACKETS,
                 payload_limit=MAX_PAYLOAD_BYTES):
        _require(isinstance(connection, sqlite3.Connection), 'SQLITE_CONNECTION_REQUIRED')
        _require(type(create) is bool, 'EXPLICIT_CREATE_MODE_REQUIRED')
        _require(type(packet_limit) is int and 1 <= packet_limit <= MAX_PACKETS,
                 'PACKET_QUOTA_BOUND')
        _require(type(payload_limit) is int and 1 <= payload_limit <= MAX_PAYLOAD_BYTES,
                 'PAYLOAD_QUOTA_BOUND')
        self._connection = connection
        self._packet_limit = packet_limit
        self._payload_limit = payload_limit
        self._lock = threading.RLock()
        with self._lock, self._transaction(write=True, check=False) as current:
            if create:
                _require(not _rows(current), 'NONEMPTY_STORE_REFUSED')
                current.execute(CONFIG_SCHEMA)
                current.execute(PACKET_SCHEMA)
                current.execute('INSERT INTO retained_inbox_config_v1 VALUES(1,?,?)',
                                (packet_limit, payload_limit))
            self._check(current)

    def _check(self, connection):
        _persistent(connection)
        _require(connection.execute('PRAGMA synchronous').fetchone()[0] in (2, 3),
                 'FULL_OR_EXTRA_SYNCHRONOUS_REQUIRED')
        _require(_rows(connection) == EXPECTED_SCHEMA, 'INBOX_SCHEMA_MISMATCH')
        _require(connection.execute('SELECT version,packet_limit,payload_limit FROM retained_inbox_config_v1').fetchall()
                 == [(1, self._packet_limit, self._payload_limit)], 'PERSISTED_QUOTA_MISMATCH')

    @contextmanager
    def _transaction(self, write=False, check=True):
        connection = self._connection
        started = False
        try:
            # Never commit or roll back a transaction owned by the caller.
            _require(not connection.in_transaction, 'IDLE_DEDICATED_CONNECTION_REQUIRED')
            _persistent(connection)
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            started = True
            if check:
                self._check(connection)
            yield connection
            connection.commit()
            _require(not connection.in_transaction, 'COMMIT_NOT_CONFIRMED')
            started = False
        except Exception as error:
            if started:
                try:
                    # A commit that succeeded but lost its acknowledgement has
                    # ended the transaction. Do not undo/adopt/replay that row.
                    if connection.in_transaction:
                        connection.rollback()
                        if connection.in_transaction:
                            # Python's explicit autocommit mode makes rollback()
                            # a no-op; this BEGIN belongs solely to this object.
                            connection.execute('ROLLBACK')
                except sqlite3.Error:
                    pass
            if isinstance(error, InboxRejected):
                raise
            raise InboxRejected('INBOX_STORAGE_UNAVAILABLE') from None

    def _usage(self, connection):
        invalid = connection.execute(
            "SELECT 1 FROM retained_packets_v1 WHERE typeof(packet)!='blob' OR "
            "typeof(packet_bytes)!='integer' OR packet_bytes<1 OR packet_bytes>? OR "
            "packet_bytes!=length(packet) LIMIT 1", (MAX_PACKET_BYTES,)).fetchone()
        _require(invalid is None, 'STORED_PACKET_LENGTH_INVALID')
        count, size = connection.execute(
            'SELECT COUNT(*),COALESCE(SUM(length(packet)),0) FROM retained_packets_v1').fetchone()
        _require(type(count) is int and type(size) is int and
                 0 <= count <= self._packet_limit and 0 <= size <= self._payload_limit,
                 'STORED_QUOTA_EXCEEDED')
        return {'packets': count, 'payload_bytes': size,
                'packet_limit': self._packet_limit, 'payload_limit': self._payload_limit}

    def _retain(self, raw, worker, direction, nonce, digest, expires):
        _scope(worker, direction, nonce)
        _digest(digest)
        _require(type(expires) is int and expires > 0, 'PACKET_EXPIRY_REQUIRED')
        _require(hashlib.sha256(raw).hexdigest() == digest, 'PACKET_CLAIM_DIGEST_MISMATCH')
        with self._transaction(write=True) as connection:
            prior = connection.execute(
                'SELECT 1 FROM retained_packets_v1 WHERE worker=? AND direction=? AND nonce=?',
                (worker, direction, nonce)).fetchone()
            if prior is not None:
                return None
            usage = self._usage(connection)
            _require(usage['packets'] < self._packet_limit, 'PACKET_QUOTA_EXHAUSTED')
            _require(usage['payload_bytes'] + len(raw) <= self._payload_limit,
                     'PAYLOAD_QUOTA_EXHAUSTED')
            connection.execute('INSERT INTO retained_packets_v1 VALUES(?,?,?,?,?,?,?)',
                               (worker, direction, nonce, digest, len(raw), expires, raw))
            receipt = RetainedReceipt(worker, direction, nonce, digest, len(raw), expires)
        return receipt

    def receive(self, raw, key, policy, now):
        """Authenticate/validate first; return only after packet+claim commit.

        A failed or uncertain commit raises without an accepted bundle. Inspect
        the same scope later; never replay automatically to infer completion.
        """
        _require(type(raw) is bytes and 0 < len(raw) <= MAX_PACKET_BYTES, 'PACKET_BYTE_BOUND')
        receipt = []
        def claim(worker, direction, nonce, digest, expires):
            retained = self._retain(raw, worker, direction, nonce, digest, expires)
            if retained is None:
                return False
            receipt.append(retained)
            return True
        with self._lock:
            # No packet/store mutation occurs before the codec invokes claim
            # after authentication, scope, canonicalization and payload checks.
            bundle = codec.unpack(raw, key, policy, now, claim)
            _require(len(receipt) == 1, 'RETAINED_RECEIPT_REQUIRED')
            return RetainedDelivery(bundle, receipt[0])

    def _read(self, connection, worker, direction, nonce, expected_digest=None):
        scope = (worker, direction, nonce)
        bounds = connection.execute(
            'SELECT typeof(packet_sha256),length(packet_sha256),typeof(packet_bytes),'
            'typeof(expires) FROM retained_packets_v1 WHERE worker=? AND direction=? AND nonce=?', scope).fetchone()
        if bounds is None:
            return None
        _require(bounds == ('text', 64, 'integer', 'integer'), 'STORED_PACKET_METADATA_INVALID')
        metadata = connection.execute(
            'SELECT packet_sha256,packet_bytes,expires,typeof(packet),length(packet) '
            'FROM retained_packets_v1 WHERE worker=? AND direction=? AND nonce=?', scope).fetchone()
        if metadata is None:
            return None
        digest, size, expires, kind, actual_size = metadata
        _digest(digest)
        _require(type(size) is int and 0 < size <= MAX_PACKET_BYTES and kind == 'blob' and actual_size == size,
                 'STORED_PACKET_LENGTH_INVALID')
        _require(type(expires) is int and expires > 0, 'STORED_PACKET_EXPIRY_INVALID')
        if expected_digest is not None:
            _require(hmac.compare_digest(digest, expected_digest), 'EXPECTED_PACKET_DIGEST_MISMATCH')
        # Length/type were checked inside this read transaction before fetching
        # the BLOB, bounding allocation even when a stored record is corrupt.
        raw = connection.execute(
            'SELECT packet FROM retained_packets_v1 WHERE worker=? AND direction=? AND nonce=?', scope).fetchone()[0]
        _require(type(raw) is bytes and len(raw) == size and
                 hmac.compare_digest(hashlib.sha256(raw).hexdigest(), digest), 'STORED_PACKET_HASH_MISMATCH')
        return RetainedReceipt(worker, direction, nonce, digest, size, expires), raw

    def inspect(self, worker, direction, nonce):
        """Recover metadata only; no decoding, claim or execution on recovery."""
        _scope(worker, direction, nonce)
        with self._lock, self._transaction() as connection:
            stored = self._read(connection, worker, direction, nonce)
            return None if stored is None else stored[0]

    def read_packet(self, worker, direction, nonce, expected_digest):
        """Read bounded, hash-verified retained bytes as untrusted data only."""
        _scope(worker, direction, nonce)
        _digest(expected_digest)
        with self._lock, self._transaction() as connection:
            stored = self._read(connection, worker, direction, nonce, expected_digest)
            _require(stored is not None, 'PACKET_NOT_RETAINED')
            return stored[1]

    def usage(self):
        with self._lock, self._transaction() as connection:
            return self._usage(connection)

    def list_receipts(self):
        """Bounded metadata inventory for explicit recovery; never replay bytes.

        Checks the persisted row/payload quotas before allocating the inventory.
        Each returned receipt also validates its stored packet hash and size.
        This is retained storage evidence, not a fresh authentication exchange.
        """
        with self._lock, self._transaction() as connection:
            self._usage(connection)
            invalid = connection.execute(
                "SELECT 1 FROM retained_packets_v1 WHERE typeof(worker)!='text' OR "
                "length(worker)<1 OR length(worker)>128 OR typeof(direction)!='text' OR "
                "direction NOT IN ('host_to_guest','guest_to_host') OR typeof(nonce)!='text' OR "
                "length(nonce)!=32 LIMIT 1").fetchone()
            _require(invalid is None, 'STORED_PACKET_SCOPE_INVALID')
            scopes = connection.execute(
                'SELECT worker,direction,nonce FROM retained_packets_v1 '
                'ORDER BY worker,direction,nonce LIMIT ?', (self._packet_limit + 1,)).fetchall()
            _require(len(scopes) <= self._packet_limit, 'STORED_QUOTA_EXCEEDED')
            result = []
            for worker, direction, nonce in scopes:
                _scope(worker, direction, nonce)
                result.append(self._read(connection, worker, direction, nonce)[0])
            return tuple(result)
