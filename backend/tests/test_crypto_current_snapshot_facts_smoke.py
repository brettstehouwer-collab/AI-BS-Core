"""Pure synthetic current snapshot facts; no account/transport/storage I/O."""
import copy
from decimal import Decimal
import unittest
from core.crypto_current_snapshot_facts import project_current_snapshot


def fixture():
    row={'instrument_name':'USD','total_borrow':'0','has_risk':False,'is_liquidating':False,'isolated_positions':[],
        'position_balances':[{'instrument_name':'USDT','quantity':'95','reserved_qty':'3'},
                             {'instrument_name':'CRO','quantity':'7','reserved_qty':'1'}]}
    return dict(before={'data':[row]},after={'data':[copy.deepcopy(row)]},ordinary={'data':[]},
        advanced={'data':[]},positions={'data':[]},fees={'instrument_name':'CRO_USDT',
        'effective_maker_rate_bps':'-1','effective_taker_rate_bps':'5'})


class CurrentSnapshotFactsSmoke(unittest.TestCase):
    def test_01_balance_free_quote_is_observed_not_capital(self):
        facts=project_current_snapshot(fixture());self.assertEqual(facts['observed_free_quote_usdt'],'92')
        self.assertIsNone(facts['trial_capital_usdt']);self.assertTrue(facts['balance_bracket_unchanged'])

    def test_02_preexisting_cro_has_no_basis_or_profit(self):
        facts=project_current_snapshot(fixture());self.assertEqual(facts['preexisting_cro_quantity'],'7')
        self.assertFalse(facts['preexisting_cro_basis_known']);self.assertIsNone(facts['preexisting_cro_basis_usdt'])
        self.assertIsNone(facts['realized_profit_usdt'])

    def test_03_reservation_change_detected(self):
        data=fixture();data['after']['data'][0]['position_balances'][0]['reserved_qty']='4'
        self.assertFalse(project_current_snapshot(data)['balance_bracket_unchanged'])

    def test_04_quantity_change_detected(self):
        data=fixture();data['after']['data'][0]['position_balances'][1]['quantity']='8'
        self.assertFalse(project_current_snapshot(data)['balance_bracket_unchanged'])

    def test_05_duplicate_assets_refused_across_wallet_rows(self):
        data=fixture();data['before']['data'].append(copy.deepcopy(data['before']['data'][0]))
        with self.assertRaises(ValueError):project_current_snapshot(data)

    def test_06_invalid_numeric_types_and_nonfinite_refused(self):
        for value in (True,0.1,'NaN','Infinity','1e9999','10000000000000000000000.0000000001',[],None):
            data=fixture();data['before']['data'][0]['position_balances'][0]['quantity']=value
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):project_current_snapshot(data)

    def test_07_reserve_cannot_exceed_quantity_or_be_negative(self):
        for value in ('96','-1'):
            data=fixture();data['after']['data'][0]['position_balances'][0]['reserved_qty']=value
            with self.assertRaises(ValueError):project_current_snapshot(data)

    def test_08_missing_asset_never_invented_zero(self):
        data=fixture();data['after']['data'][0]['position_balances']=[]
        facts=project_current_snapshot(data);self.assertIsNone(facts['observed_free_quote_usdt'])
        self.assertIsNone(facts['preexisting_cro_quantity'])

    def test_09_missing_or_malformed_liability_risk_unknown(self):
        for changes in ({'total_borrow':None},{'has_risk':'false'},{'is_liquidating':0}):
            data=fixture();data['after']['data'][0].update(changes)
            self.assertEqual(project_current_snapshot(data)['liabilities_status'],'UNKNOWN')
        data=fixture();del data['before']['data'][0]['total_borrow']
        self.assertEqual(project_current_snapshot(data)['liabilities_status'],'UNKNOWN')
        data=fixture();del data['after']['data'][0]['isolated_positions']
        self.assertEqual(project_current_snapshot(data)['liabilities_status'],'UNKNOWN')

    def test_10_present_risk_or_borrow_is_held_observation(self):
        for changes in ({'total_borrow':'1'},{'has_risk':True},{'is_liquidating':True}):
            data=fixture();data['before']['data'][0].update(changes)
            self.assertEqual(project_current_snapshot(data)['liabilities_status'],'RISK_OBSERVED')

    def test_11_empty_collections_not_full_family_coverage(self):
        facts=project_current_snapshot(fixture());self.assertTrue(all(facts['empty_observed'].values()))
        self.assertFalse(facts['all_order_families_complete']);self.assertFalse(facts['atomic_snapshot'])

    def test_12_nonempty_orders_and_positions_preserved_as_counts(self):
        data=fixture()
        for label in ('ordinary','advanced','positions'):data[label]['data']=[{'instrument_name':'CRO_USDT'}]
        facts=project_current_snapshot(data);self.assertEqual(facts['observed_counts'],dict(ordinary=1,advanced=1,positions=1))
        self.assertFalse(any(facts['empty_observed'].values()));self.assertFalse(facts['admission_allowed'])

    def test_13_signed_fees_and_currency_unknown(self):
        facts=project_current_snapshot(fixture());self.assertEqual(facts['effective_maker_rate_bps'],'-1')
        self.assertEqual(facts['effective_taker_rate_bps'],'5');self.assertIsNone(facts['actual_fee_currency'])
        for value in ('-10001','10001',False,0.5,'NaN'):
            data=fixture();data['fees']['effective_maker_rate_bps']=value
            with self.assertRaises(ValueError):project_current_snapshot(data)

    def test_14_exact_label_schema_and_arrays_required(self):
        for label in ('before','ordinary','advanced','positions','fees','after'):
            data=fixture();del data[label]
            with self.assertRaises(ValueError):project_current_snapshot(data)
        for label in ('ordinary','advanced','positions'):
            data=fixture();data[label]['data']={}
            with self.assertRaises(ValueError):project_current_snapshot(data)
        data=fixture();data['fees']['instrument_name']='CRO_USD'
        with self.assertRaises(ValueError):project_current_snapshot(data)

    def test_15_inputs_unchanged_and_no_authority(self):
        data=fixture();before=copy.deepcopy(data);facts=project_current_snapshot(data);self.assertEqual(data,before)
        self.assertIsNone(facts['exchange_account_id']);self.assertEqual(facts['orders_sent'],0)
        for key in ('account_identity_verified','ready_for_live','live_dispatch_enabled','native_protection_qualified','admission_allowed'):
            self.assertIs(facts[key],False)


if __name__=='__main__':unittest.main()
