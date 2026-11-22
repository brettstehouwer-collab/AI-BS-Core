"""Capture-only trade transport receipts for an explicit OFFLINE_ONLY store.

No network, credentials, order submission or automatic fill application. Caller
transport provenance is retained as a claim, never authenticated-account proof.
"""
import base64
from dataclasses import asdict, dataclass
import hashlib

from .coding_journal import write_json_record
from .coding_locks import record_lock
from .crypto_com_acknowledgements import CryptoComAcknowledgements, _json
from .crypto_com_adapter import _instrument, _result
from .crypto_com_trade_inbox import CryptoComTradeInbox, MAX_BYTES, _reference
from .crypto_execution_controls import ControlError, encode

METHOD = 'private/get-trades'
ENDPOINT = 'https://api.crypto.com/exchange/v1/' + METHOD
INT64_MAX = 9223372036854775807


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _integer(value):
    if type(value) is not int or not 0 <= value <= INT64_MAX:
        raise ControlError('explicit nonnegative int64 required')
    return value


@dataclass(frozen=True)
class TradeQuery:
    start_ns: int
    end_ns: int
    limit: int = 100
    instrument_name: str | None = 'CRO_USDT'

    def params(self):
        _integer(self.start_ns)
        _integer(self.end_ns)
        if self.start_ns >= self.end_ns or type(self.limit) is not int or not 1 <= self.limit <= 100:
            raise ControlError('ascending nanosecond interval and limit1..100 required')
        # These are the Exchange's wire names, independently of internal units.
        result = {'start_time': self.start_ns, 'end_time': self.end_ns, 'limit': self.limit}
        if self.instrument_name is not None:
            value = self.instrument_name
            if not isinstance(value, str) or _instrument(value.replace('_', '/')) != value:
                raise ControlError('explicit spot instrument required')
            result['instrument_name'] = value
        return result


class TradeResponseCapture:
    """Raw receipt before admission; inbox capture never advances its head."""
    _read = CryptoComAcknowledgements._read

    def __init__(self, inbox):
        if not isinstance(inbox, CryptoComTradeInbox):
            raise ControlError('existing offline trade inbox required')
        self.inbox = inbox
        path = inbox.adapter.coordinator.path
        self.root = path.with_name(path.name + '.transport')
        self._validate()

    def _scope(self):
        return dict(self.inbox._scope(), purpose='READONLY_TRADE_TRANSPORT_1')

    @classmethod
    def create(cls, inbox):
        if not isinstance(inbox, CryptoComTradeInbox):
            raise ControlError('existing offline trade inbox required')
        inbox._validate()
        path = inbox.adapter.coordinator.path
        root = path.with_name(path.name + '.transport')
        root.mkdir(mode=0o700)
        write_json_record(root/'scope.json', dict(inbox._scope(), purpose='READONLY_TRADE_TRANSPORT_1'), exclusive=True)
        return cls(inbox)

    def _validate(self):
        self.inbox._validate()
        info = self.root.lstat()
        if (not self.root.is_dir() or self.root.is_symlink()
                or getattr(info, 'st_file_attributes', 0) & 0x400
                or self._read(self.root/'scope.json') != self._scope()):
            raise ControlError('transport receipt store/account binding differs')

    def capture(self, *, request_id, nonce, query, http_status, raw_response,
                previous_checkpoint, provenance='SYNTHETIC'):
        _integer(request_id)
        _integer(nonce)
        if not isinstance(query, TradeQuery):
            raise ControlError('explicit trade query required')
        params = query.params()
        _reference(previous_checkpoint, optional=True)
        if type(http_status) is not int or not 100 <= http_status <= 599:
            raise ControlError('explicit HTTP status required')
        if provenance not in ('SYNTHETIC', 'CALLER_ASSERTED_TLS'):
            raise ControlError('recognized non-authoritative transport provenance required')
        if not isinstance(raw_response, bytes) or not 0 < len(raw_response) <= MAX_BYTES:
            raise ControlError('bounded original response bytes required')
        self._validate()
        record = {'schema': 1, 'scope_sha256': _hash(encode(self._scope()).encode()),
                  'endpoint': ENDPOINT, 'method': METHOD, 'request_id': request_id,
                  'nonce': nonce, 'query': asdict(query), 'wire_params': params,
                  'previous_checkpoint': previous_checkpoint, 'http_status': http_status,
                  'provenance': provenance, 'raw_base64': base64.b64encode(raw_response).decode('ascii'),
                  'raw_bytes': len(raw_response), 'raw_sha256': _hash(raw_response)}
        reference = _hash(encode(record).encode())
        with record_lock(self.root/'capture.lock'):
            self._validate()
            path = self.root/(reference+'.receipt.json')
            if path.exists():
                if self._read(path) != record:
                    raise ControlError('original transport receipt changed')
            else:
                write_json_record(path, record, exclusive=True)
                if self._read(path) != record:
                    raise ControlError('original transport receipt readback differs')
            return self._finish(reference, record, raw_response, query)

    def _response_admitted(self, record, raw, query):
        if record['http_status'] != 200:
            return False
        try:
            rows = _result(_json(raw), METHOD, record['request_id']).get('data')
            if not isinstance(rows, list) or len(rows) > query.limit:
                return False
            for row in rows:
                if not isinstance(row, dict) or row.get('account_id') != self.inbox.adapter.account_id:
                    return False
                symbol = row.get('instrument_name')
                if (not isinstance(symbol, str) or _instrument(symbol.replace('_', '/')) != symbol
                        or (query.instrument_name is not None and symbol != query.instrument_name)
                        or row.get('isolation_id') or row.get('isolation_type')):
                    return False
                ms = row.get('create_time')
                if type(ms) is not int or ms < 0:
                    return False
                if 'create_time_ns' in row:
                    ns = row['create_time_ns']
                    if (type(ns) is not int or ns//1000000 != ms
                            or not query.start_ns <= ns < query.end_ns):
                        return False
                elif not query.start_ns <= ms*1000000 < (ms+1)*1000000 <= query.end_ns:
                    return False
            return True
        except ControlError:
            return False

    def _finish(self, reference, record, raw, query):
        admitted = self._response_admitted(record, raw, query)
        input_reference = None
        if admitted:
            input_reference = self.inbox.capture(request_id=record['request_id'],
                start_ns=query.start_ns, end_ns=query.end_ns, limit=query.limit,
                instrument_name=query.instrument_name, previous_checkpoint=record['previous_checkpoint'],
                raw_response=raw)
        result = {'status': 'CAPTURED_NOT_APPLIED' if admitted else 'RETAINED_REJECTED',
                  'capture_reference': reference, 'input_sha256': input_reference,
                  'scope': 'OFFLINE_ONLY', 'authentication_verified': False,
                  'coverage_verified': False, 'orders_sent': 0, 'live_dispatch_enabled': False}
        path = self.root/(reference+'.completed.json')
        if path.exists():
            if self._read(path) != result:
                raise ControlError('transport completion differs')
        else:
            write_json_record(path, result, exclusive=True)
            if self._read(path) != result:
                raise ControlError('transport completion readback differs')
        return result

    def recover(self, reference):
        _reference(reference)
        self._validate()
        with record_lock(self.root/'capture.lock'):
            record = self._read(self.root/(reference+'.receipt.json'))
            if (not isinstance(record, dict) or _hash(encode(record).encode()) != reference
                    or record.get('scope_sha256') != _hash(encode(self._scope()).encode())
                    or record.get('schema') != 1 or record.get('endpoint') != ENDPOINT
                    or record.get('method') != METHOD):
                raise ControlError('transport receipt identity/context differs')
            try:
                query = TradeQuery(**record['query'])
                raw = base64.b64decode(record['raw_base64'], validate=True)
            except (ValueError, TypeError, KeyError) as error:
                raise ControlError('transport receipt encoding/context invalid') from error
            if (query.params() != record['wire_params'] or len(raw) != record['raw_bytes']
                    or not 0 < len(raw) <= MAX_BYTES or _hash(raw) != record['raw_sha256']):
                raise ControlError('transport original bytes/query differ')
            _integer(record['request_id'])
            _integer(record['nonce'])
            _reference(record['previous_checkpoint'], optional=True)
            if (type(record['http_status']) is not int or not 100 <= record['http_status'] <= 599
                    or record['provenance'] not in ('SYNTHETIC', 'CALLER_ASSERTED_TLS')):
                raise ControlError('transport status/provenance invalid')
            return self._finish(reference, record, raw, query)
