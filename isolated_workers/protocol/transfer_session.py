"""Durable manifest-bound file-transfer lifecycle, with no execution hooks.

The caller supplies authenticated host admission, a pinned manifest, and two
separate protected SQLite stores. The inbox retains authenticated packets first;
the journal then associates accepted packets with the transfer. These commits
are NOT atomic across stores. Unindexed cancellation evidence blocks completion
until explicit recovery. Recovery inspects retained data, never receive/unpack.
There are no sockets, path materialization, VM calls or authority grants here.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import re
import sqlite3
import threading

from backend.core.coding_vm_transfer import inspect_vm_transfer, restore_vm_transfer
from . import scoped_exchange as codec
from .replay_claims import _persistent, _rows
from .retained_inbox import RetainedInbox

CONFIG = 'CREATE TABLE transfer_session_config_v1 (version INTEGER PRIMARY KEY, scope BLOB NOT NULL)'
STATE = 'CREATE TABLE transfer_session_state_v1 (version INTEGER PRIMARY KEY, state TEXT NOT NULL, manifest_nonce TEXT, cancel_nonce TEXT)'
PACKETS = 'CREATE TABLE transfer_session_packets_v1 (nonce TEXT PRIMARY KEY, packet_sha256 TEXT NOT NULL, packet_bytes INTEGER NOT NULL, expires INTEGER NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL, payload_bytes INTEGER NOT NULL, payload_sha256 TEXT NOT NULL, payload BLOB NOT NULL) WITHOUT ROWID'
SCHEMA = [('table', 'transfer_session_config_v1', CONFIG),
          ('table', 'transfer_session_packets_v1', PACKETS),
          ('table', 'transfer_session_state_v1', STATE)]
MAX_EVENTS = 42
MAX_SCOPE_BYTES = 512 * 1024


class SessionRejected(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise SessionRejected(reason)


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _hex(value, length):
    _require(type(value) is str and re.fullmatch('[a-f0-9]{%d}' % length, value), 'INVALID_RECEIPT_IDENTITY')


@dataclass(frozen=True)
class TransferReceipt:
    transfer_id: str
    manifest_sha256: str
    admission_sha256: str
    worker: str
    owner: str
    direction: str
    state: str
    received_parts: tuple
    expected_parts: int
    payload_bytes: int
    expires: int
    pending_packets: tuple
    worker_admitted: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    apply_authorized: bool = field(default=False, init=False)
    verification_status: str = field(default='not_run', init=False)


class TransferSession:
    """One pinned transfer/direction per journal and dedicated packet inbox.

    Each direction preserves up to16MiB logical project bytes. Do not share one
    32MiB inbox between full input and output transfers: wire encoding adds size.
    Journal payload is bounded to one <=256KiB manifest, <=16MiB parts and one
    small cancellation message; SQLite/journal allocation is not a disk quota.
    Protect both stores and their ancestors externally. This is not that broker.
    """
    def __init__(self, connection, inbox, admission, manifest_bytes, *, worker,
                 owner, direction, issued, expires, create=False):
        _require(isinstance(connection, sqlite3.Connection), 'SQLITE_CONNECTION_REQUIRED')
        _require(isinstance(inbox, RetainedInbox), 'RETAINED_INBOX_REQUIRED')
        _require(type(create) is bool, 'EXPLICIT_CREATE_MODE_REQUIRED')
        _require(type(issued) is int and type(expires) is int and
                 0 <= issued < expires and expires - issued <= 1800, 'TRANSFER_TIME_BOUND')
        self._inspection = inspect_vm_transfer(manifest_bytes, admission, direction=direction)
        self._admission = json.loads(json.dumps(admission, sort_keys=True, allow_nan=False))
        self._manifest = bytes(manifest_bytes)
        self._parts = {p['path']:dict(p) for p in self._inspection.parts}
        self._manifest_path = self._inspection.manifest_path
        self._worker, self._owner, self._direction = worker, owner, direction
        self._issued, self._expires = issued, expires
        self._manifest_sha = _sha(self._manifest)
        manifest = json.loads(self._manifest)
        self._transfer_id = manifest['transfer_id']
        self._admission_sha = manifest['input_manifest_sha256']
        self._policy = codec.Policy(worker, owner, self._admission['base_image_sha256'],
                                    direction, frozenset([self._manifest_path, *self._parts]), {})
        self._scope_bytes = _encoded(dict(worker=worker, owner=owner, direction=direction,
            issued=issued, expires=expires, admission=self._admission,
            manifest_sha256=self._manifest_sha, manifest=manifest))
        _require(len(self._scope_bytes) <= MAX_SCOPE_BYTES, 'SESSION_SCOPE_BOUND')
        self._cancel = _encoded(dict(transfer_id=self._transfer_id,
                                    manifest_sha256=self._manifest_sha)).decode('utf-8')
        self._connection, self._inbox = connection, inbox
        self._lock = threading.RLock()
        with self._lock, self._transaction(write=True, check=False) as current:
            if create:
                _require(not _rows(current), 'NONEMPTY_SESSION_STORE_REFUSED')
                for sql in (CONFIG, STATE, PACKETS):
                    current.execute(sql)
                current.execute('INSERT INTO transfer_session_config_v1 VALUES(1,?)', (self._scope_bytes,))
                current.execute("INSERT INTO transfer_session_state_v1 VALUES(1,'WAITING_MANIFEST',NULL,NULL)")
            self._check(current)

    @property
    def policy(self):
        return self._policy

    def _check(self, connection):
        _persistent(connection)
        _require(_rows(connection) == SCHEMA, 'SESSION_SCHEMA_MISMATCH')
        metadata = connection.execute('SELECT version,typeof(scope),length(scope) FROM transfer_session_config_v1').fetchall()
        _require(metadata == [(1, 'blob', len(self._scope_bytes))], 'SESSION_SCOPE_MISMATCH')
        _require(connection.execute('SELECT scope FROM transfer_session_config_v1').fetchone()[0] == self._scope_bytes,
                 'SESSION_SCOPE_MISMATCH')

    @contextmanager
    def _transaction(self, write=False, check=True):
        connection = self._connection
        started = False
        try:
            _require(not connection.in_transaction, 'IDLE_DEDICATED_CONNECTION_REQUIRED')
            _persistent(connection)
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            started = True
            if check:
                self._check(connection)
            yield connection
            connection.commit()
            _require(not connection.in_transaction, 'SESSION_COMMIT_NOT_CONFIRMED')
            started = False
        except Exception as error:
            if started and connection.in_transaction:
                try:
                    connection.rollback()
                    if connection.in_transaction:
                        connection.execute('ROLLBACK')
                except sqlite3.Error:
                    pass
            if isinstance(error, SessionRejected):
                raise
            raise SessionRejected('SESSION_STORAGE_OR_PACKET_UNAVAILABLE') from None

    def _decode_retained(self, raw, retained):
        """Recheck historical retained data; no new MAC/nonce/time acceptance."""
        packet = json.loads(raw.decode('utf-8'), object_pairs_hook=codec._unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(SessionRejected('NONFINITE_STORED_PACKET')))
        _require(type(packet) is dict and set(packet) == {'body', 'mac'} and codec._hash(packet['mac']),
                 'RETAINED_ENVELOPE_INVALID')
        _require(codec._canonical(packet) == raw, 'RETAINED_ENVELOPE_NONCANONICAL')
        body = packet['body']
        _require(type(body) is dict and set(body) == {'version', 'worker', 'owner', 'base_sha256',
                 'direction', 'kind', 'message', 'nonce', 'issued', 'expires', 'files'}, 'RETAINED_BODY_INVALID')
        _require(body['worker'] == retained.worker and body['direction'] == retained.direction and
                 body['nonce'] == retained.nonce and body['expires'] == retained.expires,
                 'RETAINED_PACKET_RECEIPT_SCOPE_MISMATCH')
        foreign = any(body[name] != getattr(self._policy, name)
                      for name in ('worker', 'owner', 'base_sha256', 'direction'))
        if foreign:
            # Only a completely valid foreign record may be ignored. Missing
            # scope fields must not hide possibly interrupted cancellation.
            entries = body['files']
            _require(type(entries) is list and len(entries) <= codec.MAX_FILES and
                     all(type(entry) is dict and type(entry.get('path')) is str for entry in entries),
                     'RETAINED_FOREIGN_FILES_INVALID')
            foreign_policy = codec.Policy(body['worker'], body['owner'], body['base_sha256'], body['direction'],
                                           frozenset(entry['path'] for entry in entries), {})
            codec._validate(body, foreign_policy, body['issued'])
            return None
        # Historical issued time is used ONLY to recheck retained data shape.
        # No claim, fresh message, execution permission or receive path is used.
        return codec._validate(body, self._policy, body.get('issued'))

    def _semantic(self, bundle):
        _require(bundle is not None, 'RETAINED_SCOPE_MISMATCH')
        if bundle.kind == 'cancel':
            _require(not bundle.files and bundle.message == self._cancel, 'CANCELLATION_BINDING_MISMATCH')
            return 'cancel', '', bundle.message.encode('utf-8')
        expected_kind = 'message' if self._direction == 'host_to_guest' else 'result'
        _require(bundle.kind == expected_kind and bundle.message == '' and len(bundle.files) == 1,
                 'ONE_DECLARED_PART_PER_PACKET_REQUIRED')
        part = bundle.files[0]
        if part.path == self._manifest_path:
            _require(part.data == self._manifest, 'PINNED_MANIFEST_MISMATCH')
            return 'manifest', part.path, part.data
        _require(part.path in self._parts, 'UNDECLARED_PART')
        expected = self._parts[part.path]
        _require(len(part.data) == expected['length'] and part.sha256 == expected['sha256'], 'PART_HASH_OR_LENGTH_MISMATCH')
        return 'part', part.path, part.data

    def _stored(self, nonce, digest):
        receipt = self._inbox.inspect(self._worker, self._direction, nonce)
        _require(receipt is not None and receipt.packet_sha256 == digest, 'RETAINED_RECEIPT_MISMATCH')
        raw = self._inbox.read_packet(self._worker, self._direction, nonce, digest)
        return receipt, self._decode_retained(raw, receipt)

    def _events(self, connection):
        metadata = connection.execute(
            'SELECT nonce,packet_sha256,packet_bytes,expires,kind,path,payload_bytes,payload_sha256,typeof(payload),length(payload) '
            'FROM transfer_session_packets_v1 LIMIT ?', (MAX_EVENTS + 1,)).fetchall()
        _require(len(metadata) <= MAX_EVENTS, 'SESSION_EVENT_BOUND')
        result = {}
        total = 0
        seen_paths = set()
        for nonce, digest, size, expires, kind, path, length, payload_sha, data_type, actual_length in metadata:
            _hex(nonce, 32)
            _hex(digest, 64)
            _hex(payload_sha, 64)
            _require(type(length) is int and type(size) is int and type(expires) is int and
                     0 <= length <= codec.MAX_FILE_BYTES and 0 < size <= 2*1024*1024 and
                     data_type == 'blob' and actual_length == length, 'SESSION_STORED_LENGTH_INVALID')
            total += length
            _require(total <= 16*1024*1024 + 262144 + 256, 'SESSION_PAYLOAD_BOUND')
            receipt, bundle = self._stored(nonce, digest)
            _require(receipt.packet_bytes == size and receipt.expires == expires, 'RETAINED_METADATA_MISMATCH')
            actual_kind, actual_path, retained_data = self._semantic(bundle)
            _require((kind, path) == (actual_kind, actual_path) and len(retained_data) == length and
                     _sha(retained_data) == payload_sha, 'SESSION_PACKET_BINDING_MISMATCH')
            data = connection.execute('SELECT payload FROM transfer_session_packets_v1 WHERE nonce=?', (nonce,)).fetchone()[0]
            _require(type(data) is bytes and data == retained_data, 'SESSION_STORED_PAYLOAD_MISMATCH')
            _require(path not in seen_paths, 'SESSION_DUPLICATE_PATH')
            seen_paths.add(path)
            result[nonce] = (kind, path, data)
        return result

    def _snapshot(self, connection):
        rows = connection.execute('SELECT version,state,manifest_nonce,cancel_nonce FROM transfer_session_state_v1').fetchall()
        _require(len(rows) == 1 and rows[0][0] == 1, 'SESSION_STATE_INVALID')
        _, state, header, cancelled = rows[0]
        _require(state in ('WAITING_MANIFEST', 'RECEIVING', 'COMPLETE', 'CANCELLED'), 'SESSION_STATE_INVALID')
        events = self._events(connection)
        manifests = [nonce for nonce, event in events.items() if event[0] == 'manifest']
        cancellations = [nonce for nonce, event in events.items() if event[0] == 'cancel']
        _require(manifests == ([] if header is None else [header]) and
                 cancellations == ([] if cancelled is None else [cancelled]), 'SESSION_STATE_REFERENCE_MISMATCH')
        parts = {path:data for kind, path, data in events.values() if kind == 'part'}
        _require(not parts or header is not None, 'MANIFEST_REQUIRED_BEFORE_PARTS')
        _require((state != 'WAITING_MANIFEST' or not events) and
                 (state not in ('RECEIVING', 'COMPLETE') or (header is not None and cancelled is None)) and
                 (state != 'CANCELLED' or cancelled is not None), 'SESSION_STATE_REFERENCE_MISMATCH')
        if state == 'COMPLETE':
            restore_vm_transfer(self._manifest, parts, self._admission, direction=self._direction)
        pending = []
        for retained in self._inbox.list_receipts():
            if retained.nonce in events or retained.worker != self._worker or retained.direction != self._direction:
                continue
            raw = self._inbox.read_packet(retained.worker, retained.direction, retained.nonce, retained.packet_sha256)
            try:
                bundle = self._decode_retained(raw, retained)
                if bundle is not None and bundle.kind == 'cancel' and bundle.message == self._cancel:
                    pending.append((retained.nonce, retained.packet_sha256))
            except (ValueError, TypeError, KeyError, RecursionError):
                # Unverifiable unindexed evidence could be interrupted cancel.
                pending.append((retained.nonce, retained.packet_sha256))
        receipt = TransferReceipt(self._transfer_id, self._manifest_sha, self._admission_sha,
            self._worker, self._owner, self._direction, 'REVIEW_REQUIRED' if pending else state,
            tuple(sorted(parts)), len(self._parts), sum(map(len, parts.values())), self._expires, tuple(pending))
        return receipt, events, parts

    def _time(self, now):
        _require(type(now) is int and self._issued <= now < self._expires, 'TRANSFER_EXPIRED_OR_FUTURE')

    def _insert(self, connection, retained, kind, path, data):
        connection.execute('INSERT INTO transfer_session_packets_v1 VALUES(?,?,?,?,?,?,?,?,?)',
            (retained.nonce, retained.packet_sha256, retained.packet_bytes, retained.expires,
             kind, path, len(data), _sha(data), data))

    def receive(self, raw, key, now):
        """Retain authenticated packet, then commit its transfer association.

        Success means journal commit completed. A failed acknowledgement may
        leave retained or associated data: inspect instead of replaying blindly.
        Semantically rejected authenticated packets remain in the bounded inbox.
        """
        with self._lock, self._transaction(write=True) as connection:
            prior, events, parts = self._snapshot(connection)
            _require(prior.state in ('WAITING_MANIFEST', 'RECEIVING'), 'TRANSFER_NOT_RECEIVING')
            self._time(now)
            accepted = self._inbox.receive(raw, key, self._policy, now)
            kind, path, data = self._semantic(accepted.bundle)
            if kind == 'manifest':
                _require(prior.state == 'WAITING_MANIFEST', 'MANIFEST_ALREADY_RECEIVED')
                connection.execute("UPDATE transfer_session_state_v1 SET state='RECEIVING',manifest_nonce=? WHERE version=1", (accepted.receipt.nonce,))
            elif kind == 'part':
                _require(prior.state == 'RECEIVING' and path not in parts, 'PART_NOT_ADMISSIBLE')
            else:
                connection.execute("UPDATE transfer_session_state_v1 SET state='CANCELLED',cancel_nonce=? WHERE version=1", (accepted.receipt.nonce,))
            self._insert(connection, accepted.receipt, kind, path, data)
            receipt = self._snapshot(connection)[0]
        return receipt

    def inspect(self):
        """Read retained progress, including uncertain cancellation; no replay."""
        with self._lock, self._transaction() as connection:
            return self._snapshot(connection)[0]

    def complete(self, now):
        """Commit completion only after original whole-file validators pass."""
        with self._lock, self._transaction(write=True) as connection:
            receipt, _, parts = self._snapshot(connection)
            _require(receipt.state == 'RECEIVING', 'TRANSFER_NOT_RECEIVING')
            self._time(now)
            restore_vm_transfer(self._manifest, parts, self._admission, direction=self._direction)
            connection.execute("UPDATE transfer_session_state_v1 SET state='COMPLETE' WHERE version=1")
            receipt = self._snapshot(connection)[0]
        return receipt

    def read_complete(self):
        """Read historical complete bytes as data, even after transfer expiry."""
        with self._lock, self._transaction() as connection:
            receipt, _, parts = self._snapshot(connection)
            _require(receipt.state == 'COMPLETE', 'TRANSFER_NOT_COMPLETE')
            return restore_vm_transfer(self._manifest, parts, self._admission, direction=self._direction)

    def recover_cancellation(self, nonce, expected_digest):
        """Explicitly index already-retained cancel evidence; never replay it."""
        _hex(nonce, 32)
        _hex(expected_digest, 64)
        with self._lock, self._transaction(write=True) as connection:
            receipt, events, _ = self._snapshot(connection)
            _require(receipt.state == 'REVIEW_REQUIRED' and nonce not in events and
                     (nonce, expected_digest) in receipt.pending_packets, 'PENDING_CANCELLATION_REQUIRED')
            state = connection.execute('SELECT state FROM transfer_session_state_v1 WHERE version=1').fetchone()[0]
            _require(state in ('WAITING_MANIFEST', 'RECEIVING'), 'CANCELLATION_NOT_ADMISSIBLE')
            retained, bundle = self._stored(nonce, expected_digest)
            kind, path, data = self._semantic(bundle)
            _require(kind == 'cancel', 'PENDING_CANCELLATION_REQUIRED')
            self._insert(connection, retained, kind, path, data)
            connection.execute("UPDATE transfer_session_state_v1 SET state='CANCELLED',cancel_nonce=? WHERE version=1", (nonce,))
            receipt = self._snapshot(connection)[0]
        return receipt
