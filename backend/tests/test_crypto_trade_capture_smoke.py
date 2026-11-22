"""Fifteen capture-only transport receipt cases; synthetic facts, no network."""
import base64
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
from uuid import uuid4

from backend.tests import test_crypto_com_adapter_smoke as fixture
from core.crypto_com_adapter import CryptoComOfflineAdapter
from core.crypto_com_trade_inbox import CryptoComTradeInbox
from core.crypto_execution_controls import ControlError, OfflineExecutionCoordinator
from core import crypto_trade_capture as capture_module
from core.crypto_trade_capture import TradeQuery, TradeResponseCapture


class CryptoTradeCaptureSmoke(TestCase):
    def setUp(self):
        fixture.CryptoComAdapterSmoke.setUp(self)
        self.inbox = CryptoComTradeInbox.create(self.adapter)
        self.capture_box = TradeResponseCapture.create(self.inbox)
        self.query = TradeQuery(1000000000, 2000000000, instrument_name='CRO_USD')
        self.before = self.store.snapshot()
        self.head_before = self.inbox.checkpoint()

    def raw(self, rows=None, **envelope):
        value = {'id': 9, 'method': 'private/get-trades', 'code': 0,
                 'result': {'data': [self.trade] if rows is None else rows}}
        value.update(envelope)
        return (json.dumps(value, indent=2) + '\r\n').encode()

    def capture(self, raw=None, box=None, **arguments):
        args = dict(request_id=9, nonce=1200, query=self.query, http_status=200,
                    raw_response=self.raw() if raw is None else raw,
                    previous_checkpoint=None, provenance='SYNTHETIC')
        args.update(arguments)
        return (box or self.capture_box).capture(**args)

    def unchanged(self):
        self.assertEqual(self.store.snapshot(), self.before)
        self.assertEqual(self.inbox.checkpoint(), self.head_before)

    def retained_bytes(self, original):
        root = self.path.with_name(self.path.name + '.transport')
        self.assertTrue(root.is_dir())
        encoded = base64.b64encode(original).decode()
        self.assertTrue(any(encoded in p.read_text(encoding='utf-8')
                            for p in root.rglob('*.json') if p.is_file()), 'Exact original bytes not retained')

    def assert_receipt(self, result, accepted):
        self.assertEqual(result['status'], 'CAPTURED_NOT_APPLIED' if accepted else 'RETAINED_REJECTED')
        self.assertRegex(result['capture_reference'], r'^[a-f0-9]{64}$')
        if accepted:
            self.assertRegex(result['input_sha256'], r'^[a-f0-9]{64}$')
        else:
            self.assertIsNone(result['input_sha256'])
        self.assertIs(result['authentication_verified'], False)
        self.assertIs(result['coverage_verified'], False)
        self.assertEqual(result['orders_sent'], 0)

    def test_01_query_real_api_keys_and_frozen_defaults(self):
        query = TradeQuery(1, 2)
        self.assertEqual(query.params(), {'start_time': 1, 'end_time': 2, 'limit': 100,
                                         'instrument_name': 'CRO_USDT'})
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            query.limit = 1

    def test_02_query_rejects_ambiguous_ranges_types_and_limits(self):
        for args in ((True, 2), (0, 0), (2, 1), (-1, 2), (1, 9223372036854775808)):
            with self.subTest(args=args), self.assertRaises((ControlError, ValueError, TypeError)):
                TradeQuery(*args).params()
        for limit in (0, 101, True, 1.0):
            with self.subTest(limit=limit), self.assertRaises((ControlError, ValueError, TypeError)):
                TradeQuery(1, 2, limit=limit).params()

    def test_03_query_all_instruments_and_invalid_spot_filters(self):
        self.assertNotIn('instrument_name', TradeQuery(1, 2, instrument_name=None).params())
        for instrument in ('CRO/USDT', 'BTCUSD-PERP', '', 1):
            with self.subTest(instrument=instrument), self.assertRaises((ControlError, ValueError, TypeError)):
                TradeQuery(1, 2, instrument_name=instrument).params()

    def test_04_capture_preserves_exact_bytes_without_applying(self):
        raw = self.raw()
        result = self.capture(raw)
        self.assert_receipt(result, True)
        self.retained_bytes(raw)
        self.assertIn(result['input_sha256'], self.inbox.pending_inputs()['inputs'])
        self.unchanged()

    def test_05_unknown_or_manual_client_is_retained_without_apply(self):
        for client in ('', 'manual-order', str(uuid4())):
            result = self.capture(self.raw([dict(self.trade, client_oid=client)]), request_id=9)
            self.assert_receipt(result, True)
        self.unchanged()

    def test_06_http_failure_retained_before_parse(self):
        raw = b'\xffsynthetic unavailable response\r\n'
        self.assert_receipt(self.capture(raw, http_status=503), False)
        self.retained_bytes(raw)
        self.unchanged()

    def test_07_exchange_nonzero_response_retained(self):
        raw = self.raw(code=10004)
        self.assert_receipt(self.capture(raw), False)
        self.retained_bytes(raw)
        self.unchanged()

    def test_08_request_method_and_id_mismatch_retained(self):
        for changes in ({'id': 10}, {'method': 'private/get-order-history'}, {'id': True}):
            raw = self.raw(**changes)
            self.assert_receipt(self.capture(raw), False)
            self.retained_bytes(raw)
        self.unchanged()

    def test_09_wrong_account_or_filter_rejected_before_inbox(self):
        for changes in ({'account_id': 'other-account'}, {'instrument_name': 'ETH_USD'}):
            raw = self.raw([dict(self.trade, **changes)])
            self.assert_receipt(self.capture(raw), False)
            self.retained_bytes(raw)
        self.assertEqual(self.inbox.pending_inputs()['inputs'], [])
        self.unchanged()

    def test_10_timestamp_membership_and_precision_fail_closed(self):
        for changes in ({'create_time': 2000}, {'create_time': 999},
                        {'create_time_ns': 1200000000}, {'create_time': '1100'}):
            raw = self.raw([dict(self.trade, **changes)])
            self.assert_receipt(self.capture(raw), False)
        self.unchanged()

    def test_11_malformed_duplicate_nonfinite_json_retained(self):
        for raw in (b'{', self.raw().replace(b'"code": 0', b'"code": 0,"code": 0'),
                    self.raw().replace(b'"code": 0', b'"code": NaN')):
            self.assert_receipt(self.capture(raw), False)
            self.retained_bytes(raw)
        self.unchanged()

    def test_12_restart_recovers_without_fetch_or_financial_mutation(self):
        result = self.capture()
        adapter = CryptoComOfflineAdapter(OfflineExecutionCoordinator(self.path), exchange_account_id='1234')
        reopened = TradeResponseCapture(CryptoComTradeInbox(adapter))
        with patch.object(adapter, 'stage_limit', side_effect=AssertionError('resubmit forbidden')), \
             patch.object(adapter, 'replay_trade', side_effect=AssertionError('apply forbidden')):
            self.assertEqual(reopened.recover(result['capture_reference']), result)
        self.unchanged()

    def test_13_duplicate_stable_and_changed_response_distinct(self):
        first = self.capture()
        self.assertEqual(self.capture(), first)
        changed = self.capture(self.raw([dict(self.trade, traded_quantity='0.5')]))
        self.assert_receipt(changed, True)
        self.assertNotEqual(first['capture_reference'], changed['capture_reference'])
        self.unchanged()

    def test_14_completion_interruption_recaptures_without_apply(self):
        original = capture_module.write_json_record
        calls = 0
        def interrupt(path, record, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic interrupted receipt completion')
            return original(path, record, **kwargs)
        with patch.object(capture_module, 'write_json_record', side_effect=interrupt):
            with self.assertRaises(OSError):
                self.capture()
        self.retained_bytes(self.raw())
        reopened = TradeResponseCapture(self.inbox)
        result = self.capture(box=reopened)
        self.assert_receipt(result, True)
        self.assertEqual(reopened.recover(result['capture_reference']), result)
        self.unchanged()

    def test_15_provenance_cannot_establish_authentication_or_coverage(self):
        result = self.capture(self.raw([]))
        self.assert_receipt(result, True)
        self.assertFalse(self.capture_box.recover(result['capture_reference'])['authentication_verified'])
        self.assertFalse(self.inbox.checkpoint()['coverage_verified'])
        self.unchanged()


if __name__ == '__main__':
    main()
