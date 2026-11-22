"""Durable OFFLINE_ONLY get-trades replay; no network, keys or live-store path.

Local checkpoints describe applied input, never Exchange pagination/completeness.
Only cooperating callers use this lock; direct coordinator writers are not fenced.
"""
import base64
import hashlib
import json

from .coding_journal import write_json_record
from .coding_locks import record_lock
from .crypto_com_acknowledgements import CryptoComAcknowledgements, _json
from .crypto_com_adapter import CryptoComOfflineAdapter, _client_id, _result
from .crypto_execution_controls import ControlError, encode

MAX_BYTES = 1024 * 1024


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _reference(value, *, optional=False):
    if optional and value is None:
        return value
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ControlError('explicit input checksum required')
    return value


class CryptoComTradeInbox:
    """Explicit receipt chain for one existing temporary offline account store."""
    _read = CryptoComAcknowledgements._read

    def __init__(self, adapter):
        if not isinstance(adapter, CryptoComOfflineAdapter):
            raise ControlError('offline Crypto.com adapter required')
        self.adapter = adapter
        self.root = adapter.coordinator.path.with_name(adapter.coordinator.path.name + '.trades')
        self._validate()

    def _scope(self):
        return dict(CryptoComAcknowledgements._scope(self.adapter), purpose='TRADE_RESPONSE_INBOX_1')

    @classmethod
    def create(cls, adapter):
        if not isinstance(adapter, CryptoComOfflineAdapter):
            raise ControlError('offline Crypto.com adapter required')
        scope = dict(CryptoComAcknowledgements._scope(adapter), purpose='TRADE_RESPONSE_INBOX_1')
        root = adapter.coordinator.path.with_name(adapter.coordinator.path.name + '.trades')
        root.mkdir(mode=0o700)
        write_json_record(root / 'scope.json', scope, exclusive=True)
        write_json_record(root / 'head.json', {'last_applied_input': None, 'completed_sha256': None}, exclusive=True)
        return cls(adapter)

    def _validate(self):
        info = self.root.lstat()
        if (not self.root.is_dir() or self.root.is_symlink()
                or getattr(info, 'st_file_attributes', 0) & 0x400
                or self._read(self.root / 'scope.json') != self._scope()):
            raise ControlError('trade inbox account/store binding differs')

    def _head(self):
        head = self._read(self.root / 'head.json')
        if not isinstance(head, dict) or set(head) != {'last_applied_input', 'completed_sha256'}:
            raise ControlError('trade inbox checkpoint is invalid')
        previous = _reference(head['last_applied_input'], optional=True)
        if previous is not None:
            completed = self._read(self.root / (previous + '.completed.json'))
            if (not isinstance(completed, dict) or completed.get('input_sha256') != previous
                    or _hash(encode(completed).encode()) != _reference(head['completed_sha256'])):
                raise ControlError('checkpoint has no matching completed input')
        elif head['completed_sha256'] is not None:
            raise ControlError('empty checkpoint has unexpected completion evidence')
        return previous

    def _admit(self, reference, previous, current):
        """Persist one selected input before finance; interruption cannot fork it."""
        path = self.root / 'active.json'
        expected = {'input_sha256': reference, 'previous_checkpoint': previous}
        if path.exists():
            active = self._read(path)
            if not isinstance(active, dict) or set(active) != set(expected):
                raise ControlError('selected trade input is invalid')
            _reference(active['input_sha256'])
            _reference(active['previous_checkpoint'], optional=True)
            if active != expected and (not isinstance(active, dict)
                    or set(active) != set(expected) or active['input_sha256'] != current):
                raise ControlError('another trade page remains active; recover it first')
            if active == expected:
                return
        write_json_record(path, expected, exclusive=not path.exists())
        if self._read(path) != expected:
            raise ControlError('selected trade input readback differs')

    def capture(self, *, request_id, start_ns, end_ns, limit, instrument_name,
                previous_checkpoint, raw_response):
        """Save originals before parse/apply. Explicit ns bounds; no guessed cursor."""
        if (type(request_id) is not int or not 0 <= request_id <= 9223372036854775807
                or type(start_ns) is not int or type(end_ns) is not int
                or not 0 <= start_ns < end_ns <= 9223372036854775807
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ControlError('explicit request id, nanosecond bounds and limit1..100 required')
        if instrument_name is not None:
            from .crypto_com_adapter import _instrument
            if not isinstance(instrument_name, str) or _instrument(instrument_name.replace('_', '/')) != instrument_name:
                raise ControlError('explicit spot instrument or None required')
        _reference(previous_checkpoint, optional=True)
        if not isinstance(raw_response, bytes) or not 0 < len(raw_response) <= MAX_BYTES:
            raise ControlError('bounded original trade response bytes required')
        self._validate()
        with record_lock(self.root / 'trade.lock'):
            self._validate()
            record = {'schema': 1, 'scope_sha256': _hash(encode(self._scope()).encode()),
                      'previous_checkpoint': previous_checkpoint, 'request_id': request_id,
                      'query': {'start_time_ns': start_ns, 'end_time_ns': end_ns,
                                'limit': limit, 'instrument_name': instrument_name},
                      'raw_base64': base64.b64encode(raw_response).decode('ascii'),
                      'raw_bytes': len(raw_response), 'raw_sha256': _hash(raw_response)}
            reference = _hash(encode(record).encode())
            path = self.root / (reference + '.input.json')
            if path.exists():
                if self._read(path) != record:
                    raise ControlError('trade input changed')
            else:
                write_json_record(path, record, exclusive=True)
                if self._read(path) != record:
                    raise ControlError('trade input readback differs')
            return reference

    def _input(self, reference):
        _reference(reference)
        record = self._read(self.root / (reference + '.input.json'))
        fields = {'schema', 'scope_sha256', 'previous_checkpoint', 'request_id', 'query',
                  'raw_base64', 'raw_bytes', 'raw_sha256'}
        if (not isinstance(record, dict) or set(record) != fields
                or _hash(encode(record).encode()) != reference or record['schema'] != 1
                or record['scope_sha256'] != _hash(encode(self._scope()).encode())):
            raise ControlError('trade input context/checksum differs')
        _reference(record['previous_checkpoint'], optional=True)
        try:
            raw = base64.b64decode(record['raw_base64'], validate=True)
        except (ValueError, TypeError) as exc:
            raise ControlError('trade input byte encoding invalid') from exc
        if (type(record['raw_bytes']) is not int or len(raw) != record['raw_bytes']
                or not 0 < len(raw) <= MAX_BYTES or _hash(raw) != record['raw_sha256']):
            raise ControlError('trade original bytes differ')
        return record, raw

    def _rows(self, record, raw):
        result = _result(_json(raw), 'private/get-trades', record['request_id'])
        rows, query = result.get('data'), record['query']
        if not isinstance(rows, list) or len(rows) > query['limit']:
            raise ControlError('trade data exceeds the captured query limit')
        # Preflight every identity before applying any row; never silently skip an
        # unknown/manual order or infer an opening position from its fill.
        for trade in rows:
            if not isinstance(trade, dict):
                raise ControlError('trade object required')
            client_id = _client_id(trade.get('client_oid'))
            _, intent, _ = self.adapter._order(client_id)
            if (trade.get('account_id') != self.adapter.account_id
                    or trade.get('instrument_name') != intent['symbol'].replace('/', '_')
                    or trade.get('side') != intent['side'].upper()
                    or (query['instrument_name'] is not None and trade.get('instrument_name') != query['instrument_name'])):
                raise ControlError('trade account/instrument/intent differs')
            ms = trade.get('create_time')
            if type(ms) is not int or ms < 0:
                raise ControlError('explicit trade timestamp required')
            if 'create_time_ns' in trade:
                ns = trade['create_time_ns']
                if type(ns) is not int or ns // 1000000 != ms or not query['start_time_ns'] <= ns < query['end_time_ns']:
                    raise ControlError('trade timestamp differs from captured nanosecond interval')
            elif not query['start_time_ns'] <= ms * 1000000 < (ms + 1) * 1000000 <= query['end_time_ns']:
                raise ControlError('millisecond-only trade cannot prove interval membership')
        return rows

    def _fill_evidence(self, rows):
        snapshot = self.adapter.coordinator.snapshot()
        evidence = []
        for trade in rows:
            key = encode([trade['instrument_name'].replace('_', '/'), str(trade['trade_id'])])
            fill = next((row for row in snapshot['fills'] if row['fill_id'] == key), None)
            if fill is None or fill['state'] != 'APPLIED':
                raise ControlError('page contains an uncommitted fill; checkpoint retained')
            evidence.append({'key': key, 'fingerprint': fill['fingerprint'],
                             'sequence': json.loads(fill['payload'])['sequence']})
        return evidence

    def apply(self, reference):
        """Resume captured facts; coordinator persists/reuses each fill sequence."""
        self._validate()
        with record_lock(self.root / 'trade.lock'):
            self._validate()
            record, raw = self._input(reference)
            current = self._head()
            completed_path = self.root / (reference + '.completed.json')
            rows = self._rows(record, raw)
            if not completed_path.exists() and current != record['previous_checkpoint']:
                raise ControlError('stale/out-of-order page; checkpoint retained')
            # Preserve received row order as a LOCAL application sequence only.
            # Exchange chronology is unverified; no timestamp sort/coverage claim.
            if not completed_path.exists():
                self._admit(reference, record['previous_checkpoint'], current)
                for trade in rows:
                    self.adapter.replay_trade(trade['client_oid'], trade)
            completed = {'scope': 'OFFLINE_ONLY', 'input_sha256': reference,
                         'previous_checkpoint': record['previous_checkpoint'],
                         'fills': self._fill_evidence(rows), 'coverage_verified': False,
                         'live_dispatch_enabled': False}
            if completed_path.exists():
                if self._read(completed_path) != completed:
                    raise ControlError('completed trade page evidence differs')
            else:
                write_json_record(completed_path, completed, exclusive=True)
                if self._read(completed_path) != completed:
                    raise ControlError('completed trade page readback differs')
            if current == record['previous_checkpoint']:
                self._admit(reference, record['previous_checkpoint'], current)
                write_json_record(self.root / 'head.json', {'last_applied_input': reference,
                                  'completed_sha256': _hash(encode(completed).encode())})
                if self._head() != reference:
                    raise ControlError('trade checkpoint readback differs')
            return completed

    def pending_inputs(self):
        """Return retained work without choosing chronology or fetching more pages."""
        self._validate()
        with record_lock(self.root / 'trade.lock'):
            self._validate()
            pending = []
            for count, path in enumerate(self.root.glob('*.input.json'), 1):
                if count > 256:
                    raise ControlError('retained input inventory bound exceeded; explicit review required')
                reference = path.name.removesuffix('.input.json')
                self._input(reference)
                if not (self.root / (reference + '.completed.json')).exists():
                    pending.append(reference)
            active = self._read(self.root / 'active.json') if (self.root / 'active.json').exists() else None
            return {'inputs': sorted(pending), 'active_input': active,
                    'last_applied_input': self._head(), 'coverage_verified': False}

    def checkpoint(self):
        self._validate()
        with record_lock(self.root / 'trade.lock'):
            self._validate()
            return {'last_applied_input': self._head(), 'coverage_verified': False,
                    'scope': 'OFFLINE_ONLY', 'live_dispatch_enabled': False}
