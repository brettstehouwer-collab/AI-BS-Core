"""Offline acknowledgement evidence/recovery; no transport or live-store support.

Reuses frozen journal/lock helpers. Account binding is local provenance, not
authenticated account proof. Cooperative locks are not a hostile-writer sandbox.
"""
import base64
import hashlib
import json
from pathlib import Path

from .coding_journal import write_json_record
from .coding_locks import record_lock
from .crypto_com_adapter import CONTRACT, CryptoComOfflineAdapter, _client_id
from .crypto_execution_controls import ControlError, encode

MAX_RESPONSE_BYTES = 1024 * 1024


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ControlError('duplicate JSON member in retained acknowledgement')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ControlError('nonfinite JSON value in retained acknowledgement')


def _json(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                          parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ControlError('retained acknowledgement JSON is invalid') from exc


class CryptoComAcknowledgements:
    """Explicit sidecar of one existing OS-temporary OFFLINE_ONLY coordinator."""
    def __init__(self, adapter):
        if not isinstance(adapter, CryptoComOfflineAdapter):
            raise ControlError('offline Crypto.com adapter required')
        self.adapter = adapter
        self.root = adapter.coordinator.path.with_name(adapter.coordinator.path.name + '.acks')
        self._validate_scope()

    @staticmethod
    def _scope(adapter):
        path = adapter.coordinator._path(adapter.coordinator.path, exists=True)
        info = path.stat()
        return {'schema': 1, 'contract': CONTRACT, 'scope': 'OFFLINE_ONLY',
                'account_id': adapter.account_id,
                'store': {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino}}

    @classmethod
    def create(cls, adapter):
        if not isinstance(adapter, CryptoComOfflineAdapter):
            raise ControlError('offline Crypto.com adapter required')
        scope = cls._scope(adapter)
        root = adapter.coordinator.path.with_name(adapter.coordinator.path.name + '.acks')
        root.mkdir(mode=0o700)  # Exclusive: never initialize over prior/partial evidence.
        write_json_record(root / 'scope.json', scope, exclusive=True)
        return cls(adapter)

    def _read(self, path):
        info = path.lstat()
        if path.is_symlink() or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ControlError('linked acknowledgement evidence is unsupported')
        with path.open('rb') as stream:
            raw = stream.read(2 * MAX_RESPONSE_BYTES + 1)
        if len(raw) > 2 * MAX_RESPONSE_BYTES:
            raise ControlError('acknowledgement evidence exceeds its bound')
        return _json(raw)

    def _validate_scope(self):
        info = self.root.lstat()
        if (not self.root.is_dir() or self.root.is_symlink()
                or getattr(info, 'st_file_attributes', 0) & 0x400
                or self._read(self.root / 'scope.json') != self._scope(self.adapter)):
            raise ControlError('acknowledgement store/account binding differs')

    def _slot(self, client_id, request_id):
        _client_id(client_id)
        if type(request_id) is not int or not 0 <= request_id <= 9223372036854775807:
            raise ControlError('explicit int64 acknowledgement request id required')
        return self.root / (client_id + '.' + str(request_id))

    def _context(self, client_id, request_id):
        self._validate_scope()
        slot = self._slot(client_id, request_id)
        order, _, _ = self.adapter._order(client_id)
        return slot, {'schema': 1, 'scope_sha256': _hash(encode(self._scope(self.adapter)).encode()),
                      'client_id': client_id, 'request_id': request_id,
                      'intent_sha256': _hash(order['request'].encode())}

    def _quarantine(self, client_id, reason):
        marker = self.root / (client_id + '.quarantine.json')
        if not marker.exists():
            write_json_record(marker, {'client_id': client_id, 'reason': reason,
                              'recovery_action': 'HOLD_AND_LOOKUP_ONLY_NEVER_RESEND'}, exclusive=True)
        raise ControlError('contradictory acknowledgements retained; client quarantined')

    def capture(self, client_id, *, request_id, raw_response):
        """Persist exact bytes before parsing; conflicting/partial evidence survives."""
        if not isinstance(raw_response, bytes) or not 0 < len(raw_response) <= MAX_RESPONSE_BYTES:
            raise ControlError('bounded original response bytes required')
        self._validate_scope()
        with record_lock(self.root / 'receipts.lock'):
            slot, context = self._context(client_id, request_id)
            record = dict(context, raw_base64=base64.b64encode(raw_response).decode('ascii'),
                          raw_bytes=len(raw_response), raw_sha256=_hash(raw_response))
            fingerprint = _hash(encode(record).encode())
            evidence = slot.with_name(slot.name + '.' + fingerprint + '.input.json')
            if evidence.exists():
                if self._read(evidence) != record:
                    raise ControlError('existing acknowledgement input differs')
            else:
                write_json_record(evidence, record, exclusive=True)
                if self._read(evidence) != record:
                    raise ControlError('acknowledgement input readback differs')
            binding = slot.with_name(slot.name + '.binding.json')
            expected = dict(context, input_sha256=fingerprint)
            if binding.exists():
                if self._read(binding) != expected:
                    self._quarantine(client_id, 'SAME_REQUEST_RESPONSE_CONFLICT')
                return False
            write_json_record(binding, expected, exclusive=True)
            if self._read(binding) != expected:
                raise ControlError('acknowledgement binding readback differs')
            return True

    def _verified_input(self, path, fingerprint, context):
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
            raise ControlError('invalid acknowledgement fingerprint')
        record = self._read(path)
        if (not isinstance(record, dict) or _hash(encode(record).encode()) != fingerprint
                or set(record) != set(context) | {'raw_base64', 'raw_bytes', 'raw_sha256'}
                or any(record.get(k) != v for k, v in context.items())):
            raise ControlError('acknowledgement evidence differs')
        try:
            raw = base64.b64decode(record['raw_base64'], validate=True)
        except (ValueError, TypeError) as exc:
            raise ControlError('invalid acknowledgement byte encoding') from exc
        if (type(record['raw_bytes']) is not int or len(raw) != record['raw_bytes']
                or not 0 < len(raw) <= MAX_RESPONSE_BYTES or _hash(raw) != record['raw_sha256']):
            raise ControlError('acknowledgement original byte checksum differs')
        return raw

    def _check_client_inputs(self, client_id, context):
        seen, exchange_id = {}, None
        # Bound recovery work; never silently ignore extra/partial/conflicting input.
        for count, path in enumerate(self.root.glob(client_id + '.*.input.json'), 1):
            if count > 64:
                raise ControlError('acknowledgement recovery bound exceeded; retained for review')
            parts = path.name.split('.')
            if len(parts) != 5 or not parts[1].isascii() or not parts[1].isdigit():
                raise ControlError('invalid acknowledgement evidence name')
            request_id, fingerprint = int(parts[1]), parts[2]
            self._slot(client_id, request_id)
            if str(request_id) != parts[1]:
                raise ControlError('noncanonical acknowledgement evidence name')
            raw = self._verified_input(path, fingerprint, dict(context, request_id=request_id))
            if request_id in seen and seen[request_id] != fingerprint:
                self._quarantine(client_id, 'SAME_REQUEST_RESPONSE_CONFLICT')
            seen[request_id] = fingerprint
            ack = self.adapter.inspect_acknowledgement(client_id, _json(raw), request_id=request_id)
            if exchange_id is not None and ack['exchange_order_id'] != exchange_id:
                self._quarantine(client_id, 'CLIENT_EXCHANGE_ORDER_CONFLICT')
            exchange_id = ack['exchange_order_id']

    def recover(self, client_id, *, request_id):
        """Inspect saved facts only. Never stages, resends or invents a fill."""
        self._validate_scope()
        with record_lock(self.root / 'receipts.lock'):
            slot, context = self._context(client_id, request_id)
            if (self.root / (client_id + '.quarantine.json')).exists():
                raise ControlError('acknowledgement client remains quarantined')
            self._check_client_inputs(client_id, context)
            binding = self._read(slot.with_name(slot.name + '.binding.json'))
            if (not isinstance(binding, dict) or set(binding) != set(context) | {'input_sha256'}
                    or any(binding.get(k) != v for k, v in context.items())):
                raise ControlError('acknowledgement context differs')
            fingerprint = binding['input_sha256']
            if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
                raise ControlError('invalid acknowledgement fingerprint')
            evidence = slot.with_name(slot.name + '.' + fingerprint + '.input.json')
            raw = self._verified_input(evidence, fingerprint, context)
            ack = self.adapter.inspect_acknowledgement(client_id, _json(raw), request_id=request_id)
            result = {'scope': 'OFFLINE_ONLY', 'input_sha256': fingerprint,
                      'account_binding': 'LOCAL_PROVENANCE_NOT_AUTHENTICATED',
                      'live_dispatch_enabled': False, 'acknowledgement': ack}
            verified = slot.with_name(slot.name + '.verified.json')
            if verified.exists():
                if self._read(verified) != result:
                    raise ControlError('saved acknowledgement verification differs')
            else:
                write_json_record(verified, result, exclusive=True)
                if self._read(verified) != result:
                    raise ControlError('acknowledgement verification readback differs')
            return result
