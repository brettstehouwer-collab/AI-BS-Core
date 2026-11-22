"""Dormant host verification-grant validation and durable attempt reservation.

No issuer, key provisioning, launcher, socket, VM controls or execution admission.
Reviewed scope, public pins, current identity and protected persistent storage
must come independently from trusted host policy. Candidate/guest values cannot
establish that provenance. Reservation receipts are data, never launch authority.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import re
import sqlite3
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.core.coding_vm_inputs import _path, _validate_project_inputs, validate_vm_inputs
from .replay_claims import _persistent, _rows

DOMAIN = 'AI-BS/host-verification-grant/v1'
SIGNING_PREFIX = b'AI-BS/host-verification-grant/v1\x00'
MAX_GRANT_BYTES = 262144
AUTHORITY_DOMAINS = ('infrastructure_test', 'disposable_verification')
CONFIG_SCHEMA = 'CREATE TABLE verification_store_v1 (version INTEGER PRIMARY KEY, store_id TEXT NOT NULL, authority_domain TEXT NOT NULL)'
ATTEMPT_SCHEMA = 'CREATE TABLE verification_attempts_v1 (task_id TEXT NOT NULL, attempt_id TEXT NOT NULL, grant_id TEXT NOT NULL, grant_sha256 TEXT NOT NULL, scope_sha256 TEXT NOT NULL, worker_id TEXT NOT NULL, expires_at INTEGER NOT NULL, packet BLOB NOT NULL, PRIMARY KEY(task_id,attempt_id)) WITHOUT ROWID'
GRANT_INDEX = 'CREATE UNIQUE INDEX verification_grant_id_v1 ON verification_attempts_v1(grant_id)'
ATTEMPT_INDEX = 'CREATE UNIQUE INDEX verification_attempt_id_v1 ON verification_attempts_v1(attempt_id)'
EXPECTED_SCHEMA = [('index', 'verification_attempt_id_v1', ATTEMPT_INDEX),
                   ('index', 'verification_grant_id_v1', GRANT_INDEX),
                   ('table', 'verification_attempts_v1', ATTEMPT_SCHEMA),
                   ('table', 'verification_store_v1', CONFIG_SCHEMA)]


class GrantRejected(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise GrantRejected(code)


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys), 'EXACT_FIELDS_REQUIRED')


def _hex(value, size=64):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}', value) is not None,
             'CANONICAL_DIGEST_OR_ID_REQUIRED')


def _label(value):
    _require(type(value) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,128}', value) is not None,
             'OPAQUE_LABEL_REQUIRED')


def _int(value, low, high):
    _require(type(value) is int and low <= value <= high, 'INTEGER_BOUND_REQUIRED')


def canonical(value):
    """Protocol canonical JSON; input-manifest hashes retain their older format."""
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError) as error:
        raise GrantRejected('PLAIN_BOUNDED_JSON_REQUIRED') from error


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        _require(name not in result, 'DUPLICATE_JSON_FIELD')
        result[name] = value
    return result


def _constant(value):
    raise GrantRejected('NONFINITE_JSON_REFUSED')


def _decode(data):
    _require(type(data) is bytes and 0 < len(data) <= MAX_GRANT_BYTES, 'BOUNDED_BYTES_REQUIRED')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise GrantRejected('STRICT_JSON_REQUIRED') from error
    _require(canonical(value) == data, 'CANONICAL_ENCODING_REQUIRED')
    return value


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _executable(path):
    _require(type(path) is str and re.fullmatch('[A-Z]:/[^\\\\]+', path) is not None,
             'ABSOLUTE_CANONICAL_EXECUTABLE_REQUIRED')
    try:
        _path(path[3:])
    except ValueError as error:
        raise GrantRejected('UNSAFE_EXECUTABLE_PATH') from error
    _require(path.lower().endswith('/python.exe'), 'BOUNDED_PYTHON_PROFILE_REQUIRED')


def _policy(manifest, worker, runtime, profile, environment):
    _require(manifest['schema_version'] == 2, 'IMMUTABLE_SCHEMA2_REQUIRED')
    _keys(worker, ('worker_id', 'vm_id', 'image_sha256', 'disposable_image_id', 'account_sid'))
    _label(worker['worker_id'])
    _require(type(worker['vm_id']) is str and re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', worker['vm_id']) is not None,
             'VM_ID_REQUIRED')
    _hex(worker['image_sha256']); _hex(worker['disposable_image_id'], 32)
    _require(worker['image_sha256'] == manifest['base_image_sha256'], 'IMAGE_MANIFEST_MISMATCH')
    _require(type(worker['account_sid']) is str and re.fullmatch('S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+', worker['account_sid']) is not None,
             'EXECUTION_ACCOUNT_SID_REQUIRED')
    _keys(runtime, ('executable_path', 'executable_sha256', 'runtime_tree_sha256', 'protection_receipt_sha256'))
    _executable(runtime['executable_path'])
    for name in ('executable_sha256', 'runtime_tree_sha256', 'protection_receipt_sha256'):
        _hex(runtime[name])
    _keys(profile, ('profile_id', 'vcpus', 'vm_memory_bytes', 'task_memory_bytes',
                    'task_cpu_rate_percent', 'process_limit', 'check_seconds', 'total_seconds',
                    'output_bytes', 'artifact_files', 'artifact_file_bytes', 'artifact_total_bytes', 'network_policy'))
    _label(profile['profile_id'])
    for name, low, high in [('vcpus', 1, 4), ('vm_memory_bytes', 268435456, 17179869184),
                            ('task_memory_bytes', 16777216, 17179869184), ('task_cpu_rate_percent', 1, 100),
                            ('process_limit', 1, 64), ('check_seconds', 1, 120),
                            ('total_seconds', 1, 600), ('output_bytes', 1024, 1048576)]:
        _int(profile[name], low, high)
    _require(profile['task_memory_bytes'] <= profile['vm_memory_bytes'], 'TASK_MEMORY_EXCEEDS_VM')
    for name, value in [('artifact_files', 20), ('artifact_file_bytes', 2097152), ('artifact_total_bytes', 16777216)]:
        _require(type(profile[name]) is int and profile[name] == value, 'RETAINED_ARTIFACT_CEILING_REQUIRED')
    _require(profile['network_policy'] == 'deny_all', 'NETWORK_DENY_REQUIRED')
    _require(all(profile[name] == manifest['limits'][name] for name in manifest['limits']), 'MANIFEST_LIMIT_MISMATCH')
    _require(type(environment) is dict and len(environment) <= 7, 'EXPLICIT_ENVIRONMENT_REQUIRED')
    allowed = {'SYSTEMROOT', 'TEMP', 'TMP', 'PYTHONUTF8', 'PYTHONIOENCODING', 'PYTHONDONTWRITEBYTECODE'}
    _require(set(environment) <= allowed and all(type(v) is str and len(v) <= 1024 and '\x00' not in v for v in environment.values()),
             'ENVIRONMENT_ALLOWLIST_REQUIRED')
    commands = []
    for check in manifest['checks']:
        _require(check['argv'][:3] == ['python', '-m', 'unittest'], 'BOUNDED_PYTHON_PROFILE_REQUIRED')
        commands.append(dict(check_id=check['check_id'], executable=runtime['executable_path'],
                             argv=[runtime['executable_path'], *check['argv'][1:]], working_directory='.'))
    return commands


def _scope_record(manifest, worker, runtime, profile, environment, fixture_manifest_sha256):
    commands = _policy(manifest, worker, runtime, profile, environment)
    immutable = [item for item in manifest['files'] if item['role'] in ('verification', 'dependency')]
    _require(any(item['role'] == 'verification' for item in immutable), 'INDEPENDENT_TESTS_REQUIRED')
    _hex(fixture_manifest_sha256)
    return dict(input_manifest=manifest,
                 input_manifest_sha256=_sha(json.dumps(manifest, sort_keys=True, allow_nan=False).encode('utf-8')),
                 immutable_files=immutable, immutable_files_sha256=_sha(canonical(immutable)),
                 fixture_manifest_sha256=fixture_manifest_sha256, worker=worker, runtime=runtime,
                 commands=commands, environment=dict(inherit=False, values=environment),
                 resource_profile=profile, resource_profile_sha256=_sha(canonical(profile)))


def prepare_scope(admission, contents, *, worker, runtime, resource_profile,
                  environment, fixture_manifest_sha256):
    """Bind independently reviewed bytes; do not infer their host authorization.

    This first profile admits only existing fixed Python unittest commands.
    Resource values are requirements to enforce later, not observed enforcement.
    No private key or operational acceptance can be created by this function.
    """
    try:
        manifest = validate_vm_inputs(admission, contents, admission)
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise GrantRejected('INPUT_ADMISSION_REFUSED') from error
    worker, runtime, profile, environment = json.loads(canonical([worker, runtime, resource_profile, environment]))
    encoded = canonical(_scope_record(manifest, worker, runtime, profile, environment, fixture_manifest_sha256))
    _require(len(encoded) < MAX_GRANT_BYTES//2, 'SCOPE_SIZE_BOUND')
    return encoded


def _prepared_scope(encoded):
    """Validate complete scope metadata, independently of signature provenance.

    Actual input bytes must have been checked by prepare_scope at admission and
    must be rechecked on held objects by the eventual native launcher.
    """
    scope = _decode(encoded)
    _keys(scope, ('input_manifest', 'input_manifest_sha256', 'immutable_files', 'immutable_files_sha256',
                  'fixture_manifest_sha256', 'worker', 'runtime', 'commands', 'environment',
                  'resource_profile', 'resource_profile_sha256'))
    m = scope['input_manifest']
    _keys(m, ('schema_version', 'task_id', 'request_id', 'attempt_id', 'repository_id', 'commit',
              'authorization_ref', 'base_image_sha256', 'files', 'checks', 'limits'))
    _require(type(m['schema_version']) is int and m['schema_version'] == 2, 'IMMUTABLE_SCHEMA2_REQUIRED')
    for name in ('task_id', 'request_id', 'attempt_id', 'repository_id', 'authorization_ref'):
        _hex(m[name], 32)
    _require(type(m['commit']) is str and len(m['commit']) in (40, 64), 'BASE_REVISION_REQUIRED')
    _hex(m['commit'], len(m['commit'])); _hex(m['base_image_sha256'])
    _require(type(m['files']) is list and 1 <= len(m['files']) <= 20, 'INPUT_FILE_BOUND')
    names = set(); total = 0
    for entry in m['files']:
        _keys(entry, ('relative_path', 'length', 'sha256', 'role'))
        try: name = _path(entry['relative_path'])
        except ValueError as error: raise GrantRejected('UNSAFE_INPUT_PATH') from error
        _require(name not in names, 'DUPLICATE_INPUT_PATH'); names.add(name)
        _hex(entry['sha256']); _int(entry['length'], 0, 2097152)
        _require(entry['role'] in ('editable', 'verification', 'dependency'), 'FILE_ROLE_REQUIRED')
        total += entry['length']
    _require(total <= 16777216, 'INPUT_TOTAL_BOUND')
    _require(type(m['checks']) is list and 1 <= len(m['checks']) <= 10, 'CHECK_COUNT_BOUND')
    checks = set()
    for check in m['checks']:
        _keys(check, ('check_id', 'argv'))
        _require(type(check['check_id']) is str and re.fullmatch('[a-z0-9_-]{1,64}', check['check_id']) is not None
                 and check['check_id'] not in checks, 'CHECK_ID_REQUIRED')
        checks.add(check['check_id'])
        argv = check['argv']
        _require(type(argv) is list and 4 <= len(argv) <= 64 and
                 all(type(a) is str and len(a) <= 1024 and '\x00' not in a for a in argv) and
                 argv[:3] == ['python', '-m', 'unittest'], 'BOUNDED_PYTHON_PROFILE_REQUIRED')
    _keys(m['limits'], ('check_seconds', 'total_seconds', 'output_bytes'))
    for name, low, high in [('check_seconds', 1, 120), ('total_seconds', 1, 600), ('output_bytes', 1024, 1048576)]:
        _int(m['limits'][name], low, high)
    _require(m['limits']['check_seconds'] <= m['limits']['total_seconds'], 'CHECK_DEADLINE_BOUND')
    try: _validate_project_inputs(m['files'], {}, m['checks'])
    except ValueError as error: raise GrantRejected('IMMUTABLE_PROJECT_PROFILE_REFUSED') from error
    _keys(scope['environment'], ('inherit', 'values'))
    _require(scope['environment']['inherit'] is False, 'INHERITED_ENVIRONMENT_REFUSED')
    rebuilt = _scope_record(m, scope['worker'], scope['runtime'], scope['resource_profile'],
                            scope['environment']['values'], scope['fixture_manifest_sha256'])
    _require(canonical(rebuilt) == encoded and len(encoded) < MAX_GRANT_BYTES//2,
             'PREPARED_SCOPE_DERIVATION_MISMATCH')
    return scope


@dataclass(frozen=True)
class VerifiedGrant:
    packet: bytes
    scope_sha256: str
    grant_sha256: str
    task_id: str
    attempt_id: str
    grant_id: str
    worker_id: str
    expires_at: int


def verify_grant(packet, *, pinned_verifiers, expected_scope, now_utc,
                 authority_domain='disposable_verification'):
    """Verify against independent host pins/scope; no executable is launched."""
    _require(authority_domain in AUTHORITY_DOMAINS, 'AUTHORITY_DOMAIN_REQUIRED')
    _int(now_utc, 1, 2**63-1)
    scope = _prepared_scope(expected_scope)
    value = _decode(packet)
    _keys(value, ('body', 'signature'))
    body = value['body']
    _keys(body, ('schema_version', 'domain', 'authority_domain', 'purpose', 'issuer_id', 'key_id',
                 'grant_id', 'issued_at', 'expires_at', 'scope'))
    _require(type(body['schema_version']) is int and body['schema_version'] == 1 and body['domain'] == DOMAIN,
             'GRANT_VERSION_DOMAIN_REQUIRED')
    _require(body['authority_domain'] == authority_domain and body['purpose'] == 'bounded_verification',
             'VERIFICATION_ONLY_DOMAIN_REQUIRED')
    for name in ('issuer_id', 'key_id'): _label(body[name])
    _hex(body['grant_id'], 32)
    for name in ('issued_at', 'expires_at'): _int(body[name], 1, 2**63-1)
    _require(body['issued_at'] <= now_utc < body['expires_at'] and
             0 < body['expires_at'] - body['issued_at'] <= 600, 'GRANT_EXPIRED_FUTURE_OR_OVERLONG')
    _require(canonical(body['scope']) == expected_scope, 'HOST_REVIEW_SCOPE_MISMATCH')
    _require(type(pinned_verifiers) is dict, 'HOST_PIN_SET_REQUIRED')
    key = pinned_verifiers.get((body['issuer_id'], body['key_id']))
    _require(type(key) is bytes and len(key) == 32, 'PINNED_HOST_KEY_REQUIRED')
    _hex(value['signature'], 128)
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(bytes.fromhex(value['signature']), SIGNING_PREFIX+canonical(body))
    except (InvalidSignature, ValueError) as error:
        raise GrantRejected('HOST_SIGNATURE_REFUSED') from error
    try:
        task_id, attempt_id = scope['input_manifest']['task_id'], scope['input_manifest']['attempt_id']
        worker_id = scope['worker']['worker_id']
    except (KeyError, TypeError) as error:
        raise GrantRejected('PREPARED_HOST_SCOPE_REQUIRED') from error
    _hex(task_id, 32); _hex(attempt_id, 32); _label(worker_id)
    return VerifiedGrant(packet, _sha(expected_scope), _sha(packet), task_id, attempt_id,
                         body['grant_id'], worker_id, body['expires_at'])


@dataclass(frozen=True)
class ReservationReceipt:
    task_id: str
    attempt_id: str
    grant_id: str
    grant_sha256: str
    scope_sha256: str
    worker_id: str
    expires_at: int
    state: str = field(default='ATTEMPT_RESERVED', init=False)
    worker_admitted: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    apply_authorized: bool = field(default=False, init=False)
    verification_status: str = field(default='not_run', init=False)


class VerificationAttemptRegistry:
    """Dedicated protected connection; no migration, pruning or store provisioning.

    The native controller must pin a single protected store and its identity.
    A fresh caller-selected database is not replay continuity or authority.
    Uncertain writes quarantine this instance. Recovery inspection is data only;
    an interrupted reservation never becomes permission to relaunch a candidate.
    """
    def __init__(self, connection, *, store_id, authority_domain, create=False):
        _require(isinstance(connection, sqlite3.Connection), 'DEDICATED_CONNECTION_REQUIRED')
        _require(type(create) is bool and authority_domain in AUTHORITY_DOMAINS, 'EXPLICIT_STORE_POLICY_REQUIRED')
        _hex(store_id, 32)
        self._connection = connection
        self._store_id = store_id
        self._domain = authority_domain
        self._lock = threading.RLock()
        self._quarantined = False
        with self._lock, self._transaction(check=False) as c:
            if create:
                _require(not _rows(c), 'NONEMPTY_STORE_REFUSED')
                c.execute(CONFIG_SCHEMA); c.execute(ATTEMPT_SCHEMA); c.execute(GRANT_INDEX); c.execute(ATTEMPT_INDEX)
                c.execute('INSERT INTO verification_store_v1 VALUES(1,?,?)', (store_id, authority_domain))
            self._check(c)

    def _check(self, c):
        _require(_rows(c) == EXPECTED_SCHEMA, 'EXACT_VERIFICATION_STORE_SCHEMA_REQUIRED')
        _require(c.execute('SELECT version,store_id,authority_domain FROM verification_store_v1').fetchall()
                 == [(1, self._store_id, self._domain)], 'PROTECTED_STORE_IDENTITY_MISMATCH')

    @contextmanager
    def _transaction(self, check=True):
        c = self._connection
        started = False
        committing = False
        try:
            _require(not self._quarantined, 'STORE_QUARANTINED')
            _require(not c.in_transaction, 'IDLE_DEDICATED_CONNECTION_REQUIRED')
            _persistent(c)
            _require(c.execute('PRAGMA synchronous').fetchone()[0] in (2, 3), 'FULL_OR_EXTRA_SYNCHRONOUS_REQUIRED')
            started = True
            # After refusing caller transactions, this BEGIN attempt is ours,
            # including an interruption after SQLite starts it but before ack.
            c.execute('BEGIN IMMEDIATE')
            if check: self._check(c)
            yield c
            committing = True
            c.commit()
            _require(not c.in_transaction, 'COMMIT_NOT_CONFIRMED')
            started = False
        except BaseException as error:
            if committing or not isinstance(error, Exception) or isinstance(error, (sqlite3.Error, OSError)):
                self._quarantined = True
            if started and c.in_transaction:
                try: c.rollback()
                except BaseException: self._quarantined = True
            if not isinstance(error, Exception): raise
            if isinstance(error, GrantRejected): raise
            raise GrantRejected('VERIFICATION_STORE_OPERATION_REFUSED') from error

    def claim_once(self, packet, *, pinned_verifiers, expected_scope, current_identity, clock):
        # Reverify inside the durable write transaction. No VerifiedGrant object
        # supplied by a caller can bypass signature, scope or expiry checks.
        with self._lock, self._transaction() as c:
            _require(callable(clock), 'TRUSTED_HOST_CLOCK_REQUIRED')
            validation_time = clock()
            verified = verify_grant(packet, pinned_verifiers=pinned_verifiers, expected_scope=expected_scope,
                                    now_utc=validation_time, authority_domain=self._domain)
            scope = _decode(expected_scope)
            _require(canonical(current_identity) == canonical(dict(worker=scope['worker'], runtime=scope['runtime'])),
                     'CURRENT_WORKER_RUNTIME_MISMATCH')
            _require(not c.execute('SELECT 1 FROM verification_attempts_v1 WHERE grant_id=? OR attempt_id=?',
                                   (verified.grant_id, verified.attempt_id)).fetchone(), 'ATTEMPT_OR_GRANT_REPLAYED')
            fresh_time = clock()
            _int(fresh_time, 1, 2**63-1)
            _require(validation_time <= fresh_time < verified.expires_at, 'GRANT_EXPIRED_OR_CLOCK_REVERSED')
            c.execute('INSERT INTO verification_attempts_v1 VALUES(?,?,?,?,?,?,?,?)',
                      (verified.task_id, verified.attempt_id, verified.grant_id, verified.grant_sha256,
                       verified.scope_sha256, verified.worker_id, verified.expires_at, verified.packet))
            receipt = ReservationReceipt(verified.task_id, verified.attempt_id, verified.grant_id,
                                         verified.grant_sha256, verified.scope_sha256, verified.worker_id, verified.expires_at)
        return receipt  # Only after confirmed commit; still no launch authority.

    def inspect(self, task_id, attempt_id):
        _hex(task_id, 32); _hex(attempt_id, 32)
        with self._lock, self._transaction() as c:
            row = c.execute('SELECT task_id,attempt_id,grant_id,grant_sha256,scope_sha256,worker_id,expires_at FROM verification_attempts_v1 WHERE task_id=? AND attempt_id=?',
                            (task_id, attempt_id)).fetchone()
        return ReservationReceipt(*row) if row else None
