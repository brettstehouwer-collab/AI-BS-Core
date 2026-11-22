"""Ten connected temporary-store cases; fixture assertions confer no live authority."""
from decimal import Decimal
import json
import unittest
from uuid import uuid4

from tests import test_crypto_trial_admission_smoke as fixture
from core.crypto_execution_controls import ControlError, Fill, Held, digest, text_decimal
from core.crypto_com_native_stop import build_native_stop_draft


class TrialStopCompositionSmoke(unittest.TestCase):
    quote = fixture.TrialAdmissionSmoke.quote
    reserve = fixture.TrialAdmissionSmoke.reserve
    execute_buy = fixture.TrialAdmissionSmoke.execute_buy
    dump = fixture.TrialAdmissionSmoke.dump

    def setUp(self):
        fixture.TrialAdmissionSmoke.setUp(self)

    def buy(self, *, quantity=None, fees=()):
        result = self.reserve(stop='0.08')
        cid = result['intent']['client_id']
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'INTENT')
        self.store.begin_submission(cid, now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'SUBMITTING')
        qty = quantity or result['receipt']['quantity_cro']
        self.store.apply_fill(Fill(fill_id='composition-buy', client_id=cid,
            exchange_order_id='synthetic-buy', symbol='CRO/USDT', side='buy',
            quantity=qty, cost=text_decimal(Decimal(qty)*Decimal('0.1')),
            fees=fees, sequence=1, occurred_ms=self.clock+1))
        self.assertEqual(self.store.snapshot()['fills'][0]['state'], 'APPLIED')
        return result

    def facts(self, *, require_terminal=True):
        """Explicit test-only bridge; not installed in any production caller."""
        snapshot = self.store.snapshot()
        if (snapshot['unmatched_fills'] or not snapshot['fills']
                or any(row['state']!='APPLIED' for row in snapshot['fills'])
                or snapshot['risk']['halted']
                or (require_terminal and any(row['state'] in ('UNKNOWN','SUBMITTING','PARTIAL')
                    for row in snapshot['orders']))):
            raise ControlError('test bridge requires fully applied, resolved fixture')
        balance = next(row for row in snapshot['balances'] if row['asset']=='CRO')
        inventory = Decimal(balance['total'])
        reserved = sum((Decimal(row['reserve_amount']) for row in snapshot['orders']
            if row['reserve_asset']=='CRO'), Decimal(0))
        available = inventory-reserved
        return dict(account=self.store.account, instrument_name='CRO_USDT', client_oid=str(uuid4()),
            net_inventory=text_decimal(inventory), available_base=text_decimal(available),
            quantity=text_decimal(available), quantity_tick='0.5', price_tick='0.01',
            minimum_quantity='0.5', minimum_notional_quote='0.01', trigger_price='0.08',
            last_price='0.1', fee_asset='USDT', fee_reserve='0.01', available_fee='1',
            actual_fill_fees_complete=True, reconciliation_complete=True,
            unresolved_orders=False, provenance_sha256=digest(snapshot))

    def test_01_full_fill_actual_inventory_native_draft(self):
        entry=self.buy(); facts=self.facts(); draft=build_native_stop_draft(**facts)
        self.assertEqual(draft['draft']['params']['quantity'],entry['receipt']['quantity_cro'])
        self.assertEqual(draft['facts_sha256'],digest(facts))
        self.assertEqual(draft['provenance_sha256'],digest(self.store.snapshot()))

    def test_02_partial_below_minimum_refused(self):
        self.buy(quantity='0.5')
        with self.assertRaises(ControlError):self.facts()
        # Even an explicit caller override cannot meet the selected fixture minimum.
        facts=self.facts(require_terminal=False);facts['minimum_notional_quote']='1'
        with self.assertRaises(ControlError):build_native_stop_draft(**facts)

    def test_03_actual_base_entry_fee_reduces_stop_quantity(self):
        entry=self.buy(fees=(('CRO','0.5'),));facts=self.facts()
        self.assertEqual(Decimal(facts['quantity']),Decimal(entry['receipt']['quantity_cro'])-Decimal('0.5'))
        self.assertEqual(build_native_stop_draft(**facts)['draft']['params']['quantity'],'10')

    def test_04_reserved_inventory_deducted(self):
        self.buy();self.clock+=10;self.quote('0.1')
        self.store.prepare(str(uuid4()),symbol='CRO/USDT',side='sell',quantity='5',limit_price='0.1',now_ms=self.clock)
        facts=self.facts();self.assertEqual(Decimal(facts['available_base']),Decimal('5.25'))
        facts['quantity']='5'
        self.assertEqual(build_native_stop_draft(**facts)['draft']['params']['quantity'],'5')
        facts['quantity']='10.5'
        with self.assertRaises(ControlError):build_native_stop_draft(**facts)

    def test_05_unknown_submission_no_test_bridge_proposal(self):
        entry=self.reserve(stop='0.08');cid=entry['intent']['client_id']
        self.store.begin_submission(cid,now_ms=self.clock);self.store.mark_unknown(cid,'TIMEOUT')
        with self.assertRaises(ControlError):self.facts()

    def test_06_unapplied_fill_no_test_bridge_proposal(self):
        entry=self.reserve(stop='0.08');cid=entry['intent']['client_id']
        self.store.begin_submission(cid,now_ms=self.clock)
        with self.assertRaises(Held):self.store.apply_fill(Fill(fill_id='unapplied',client_id=cid,
            exchange_order_id='synthetic-buy',symbol='CRO/USDT',side='buy',quantity='10.5',
            cost='1.05',fees=(('USDT','1'),),sequence=1,occurred_ms=self.clock+1))
        self.assertEqual(self.store.snapshot()['fills'][0]['state'],'PENDING')
        with self.assertRaises(ControlError):self.facts()

    def test_07_exact_advanced_endpoint_and_reference_names(self):
        self.buy();draft=build_native_stop_draft(**self.facts())['draft']
        self.assertEqual(draft['method'],'private/advanced/create-order')
        self.assertEqual(draft['params']['ref_price_type'],'LAST_PRICE')
        self.assertEqual(draft['params']['ref_price'],'0.08')
        self.assertNotIn('trigger_price',draft['params'])
        self.assertNotIn('api_key',draft);self.assertNotIn('sig',draft)

    def test_08_account_receipt_freshness_are_explicit_interface_gaps(self):
        self.buy();facts=self.facts();facts.update(account='wrong-account',provenance_sha256='b'*64)
        result=build_native_stop_draft(**facts)
        # Builder validates syntax only: it has no bound account, receipt lookup or timestamp.
        self.assertFalse(result['provenance_authenticated'])
        self.assertFalse(result['ready_for_live'])
        self.assertNotIn('now_ms',facts)

    def test_09_generic_core_stop_is_not_native_acceptance(self):
        self.buy();self.assertTrue(self.store.snapshot()['stops'])
        self.clock+=10;self.quote('0.08')
        generic=self.store.evaluate_stop('CRO/USDT',now_ms=self.clock)
        self.assertIsNotNone(generic)
        self.assertEqual(json.loads(generic['request'])['side'],'sell')
        self.assertEqual(generic['state'],'INTENT')
        self.assertNotIn('native_order_accepted',generic)
        self.assertFalse(self.store.entry_status()['native_protection_qualified'])

    def test_10_closed_loss_cutoff_still_allows_reducing_exit(self):
        fixture.TrialAdmissionSmoke.fresh(self,'0.5')
        result=self.reserve(stop='0.08');self.execute_buy(result,'0.0525')
        self.clock+=10;self.quote('0.01');cid=str(uuid4())
        self.store.prepare(cid,symbol='CRO/USDT',side='sell',quantity='5',limit_price='0.01',now_ms=self.clock)
        self.store.begin_submission(cid,now_ms=self.clock)
        self.store.apply_fill(Fill(fill_id='cutoff-partial',client_id=cid,exchange_order_id='cutoff-sell',
            symbol='CRO/USDT',side='sell',quantity='5',cost='0.05',fees=(('CRO','0.25'),),
            sequence=2,occurred_ms=self.clock+1))
        self.clock+=10;self.quote('0.01')
        self.assertTrue(self.store.refresh_entry_hold(now_ms=self.clock)['entry_held'])
        reducing=str(uuid4());self.store.prepare(reducing,symbol='CRO/USDT',side='sell',quantity='5',
            limit_price='0.01',now_ms=self.clock);self.store.begin_submission(reducing,now_ms=self.clock)
        self.assertEqual(next(row for row in self.store.snapshot()['orders'] if row['client_id']==reducing)['state'],'SUBMITTING')
        self.assertFalse(self.store.entry_status()['live_daily_cutoff_enforced'])


if __name__=='__main__':unittest.main()
