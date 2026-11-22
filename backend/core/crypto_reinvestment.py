"""Durable reinvestment intent preparation in an existing OFFLINE_ONLY store.

No transport or submission call exists here. Final submission admission, daily
loss enforcement and native protective execution remain separate unqualified
requirements. Same-account filesystem writes are not a hostile-writer sandbox.
"""
from decimal import localcontext, ROUND_DOWN
import json
import sqlite3

from .crypto_execution_controls import (
    ACTIVE, ControlError, OfflineExecutionCoordinator, digest, encode,
    identifier, number, stamp, text_decimal,
)
from .crypto_trial_budget import DAY_MS, _accounting_number, _validated_baseline
from .crypto_trial_projection import _decoded, _project_trial_snapshot


class OfflineReinvestment:
    """One explicit seed/cap policy; receipts and intents share the writer transaction."""
    def __init__(self, coordinator):
        if not isinstance(coordinator, OfflineExecutionCoordinator) or coordinator.quote != 'USDT':
            raise ControlError('existing USDT offline coordinator required')
        self.coordinator = coordinator
        with coordinator._tx() as db:
            policy = self._read_policy(db)
        self._policy_payload = encode(policy)

    @staticmethod
    def _snapshot(db):
        return {'scope':'OFFLINE_ONLY', 'live_dispatch_enabled':False,
            'risk':dict(db.execute('SELECT * FROM risk WHERE id=1').fetchone()),
            **{table:[dict(row) for row in db.execute('SELECT * FROM '+table)]
               for table in ('balances','positions','orders','fills','unmatched_fills','stops','daily')}}

    @staticmethod
    def _store_scope(coordinator, db):
        metadata = dict(db.execute('SELECT key,value FROM metadata'))
        try:
            if (metadata['scope'] != 'OFFLINE_ONLY' or metadata['schema'] != '1'
                    or metadata['account'] != coordinator.account or metadata['quote'] != 'USDT'
                    or digest(json.loads(metadata['limits'])) != digest(dict(coordinator.limits))):
                raise ControlError('offline store metadata changed')
        except (KeyError, ValueError, TypeError) as exc:
            raise ControlError('valid bound offline metadata required') from exc
        return dict(account=coordinator.account, quote=coordinator.quote,
                    limits_sha256=digest(dict(coordinator.limits)))

    def _read_policy(self, db):
        try:
            row = db.execute('SELECT payload,fingerprint FROM aibs_reinvestment_policy WHERE id=1').fetchone()
        except sqlite3.Error as exc:
            raise ControlError('explicit reinvestment registration required') from exc
        if row is None:
            raise ControlError('missing immutable reinvestment policy')
        policy = _decoded(row['payload'])
        fields = {'schema','scope','account','quote','limits_sha256','baseline',
                  'seed_budget_usdt','max_entry_budget_usdt'}
        if (policy.keys() != fields or type(policy['schema']) is not int or policy['schema'] != 1
                or policy['scope'] != 'OFFLINE_REINVESTMENT_PREPARATION'
                or digest(policy) != row['fingerprint']):
            raise ControlError('reinvestment policy changed')
        baseline = _validated_baseline(policy['baseline'])
        scope = self._store_scope(self.coordinator, db)
        seed, cap = number(policy['seed_budget_usdt']), number(policy['max_entry_budget_usdt'])
        if (any(policy[key] != value for key,value in scope.items())
                or baseline['account'] != self.coordinator.account or seed <= 0 or cap < seed
                or cap > number(self.coordinator.limits['max_order_quote'])
                or (hasattr(self, '_policy_payload') and encode(policy) != self._policy_payload)):
            raise ControlError('reinvestment account, baseline, limits or policy differs')
        return policy

    @classmethod
    def create(cls, coordinator, baseline, *, seed_budget_usdt, max_entry_budget_usdt):
        if not isinstance(coordinator, OfflineExecutionCoordinator) or coordinator.quote != 'USDT':
            raise ControlError('existing USDT offline coordinator required')
        baseline = _validated_baseline(baseline)
        seed, cap = number(seed_budget_usdt), number(max_entry_budget_usdt)
        if (baseline['account'] != coordinator.account or seed <= 0 or cap < seed
                or cap > number(coordinator.limits['max_order_quote'])):
            raise ControlError('positive explicit seed and bounded entry cap required')
        with coordinator._tx() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name IN ('aibs_reinvestment_policy','aibs_reinvestment_entries')").fetchone():
                raise ControlError('reinvestment policy already exists; reopen without resetting')
            snapshot = cls._snapshot(db)
            if snapshot['orders'] or snapshot['fills'] or snapshot['positions']:
                raise ControlError('new dedicated trial store required')
            _project_trial_snapshot(coordinator, baseline, snapshot, trial_client_ids=[],
                now_ms=baseline['started_ms'], loss_budget_usdt='1',
                proposed_loss_reserve_usdt='0', coverage_complete=False)
            cash = next((row['total'] for row in snapshot['balances'] if row['asset']=='USDT'), '0')
            if _accounting_number(cash) < seed:
                raise ControlError('explicit seed exceeds available offline cash')
            policy = dict(schema=1, scope='OFFLINE_REINVESTMENT_PREPARATION',
                **cls._store_scope(coordinator, db), baseline=baseline,
                seed_budget_usdt=text_decimal(seed), max_entry_budget_usdt=text_decimal(cap))
            db.execute('CREATE TABLE aibs_reinvestment_policy(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')
            db.execute('CREATE TABLE aibs_reinvestment_entries(client_id TEXT PRIMARY KEY REFERENCES orders(client_id),request TEXT NOT NULL,request_sha256 TEXT NOT NULL,receipt TEXT NOT NULL,receipt_sha256 TEXT NOT NULL)')
            db.execute('INSERT INTO aibs_reinvestment_policy VALUES(1,?,?)',(encode(policy),digest(policy)))
        return cls(coordinator)

    @staticmethod
    def _result(intent, receipt, new):
        return {'scope':'OFFLINE_REINVESTMENT_INTENT_PREPARATION_ONLY', 'intent':intent,
            'receipt':receipt, 'new_reservation':new, 'submission_started':False,
            'live_dispatch_enabled':False, 'ready_for_live':False,
            'daily_cutoff_enforced':False, 'orders_sent':0}

    def reserve_entry(self, client_id, *, limit_price, hard_stop, now_ms):
        client_id = identifier(client_id)
        price, stop = number(limit_price), number(hard_stop)
        now_ms = stamp(now_ms)
        if price <= 0 or not 0 < stop < price:
            raise ControlError('positive entry and lower hard stop required')
        with self.coordinator._tx() as db, localcontext() as context:
            context.prec = 96
            policy = self._read_policy(db);baseline = policy['baseline']
            if not baseline['started_ms'] <= now_ms < baseline['day_start_ms'] + DAY_MS:
                raise ControlError('explicit current-day trial baseline required')
            request = dict(client_id=client_id, limit_price=text_decimal(price),
                hard_stop=text_decimal(stop), baseline_sha256=baseline['baseline_sha256'])
            old = db.execute('SELECT * FROM aibs_reinvestment_entries WHERE client_id=?',(client_id,)).fetchone()
            if old:
                recorded, receipt = _decoded(old['request']), _decoded(old['receipt'])
                if (digest(recorded) != old['request_sha256'] or recorded != request
                        or digest(receipt) != old['receipt_sha256'] or receipt.get('client_id') != client_id):
                    raise ControlError('immutable reinvestment intent or receipt differs')
                intent = dict(self.coordinator._order(db, client_id))
                expected = dict(symbol='CRO/USDT',side='buy',quantity=receipt['quantity_cro'],
                    limit_price=request['limit_price'],hard_stop=request['hard_stop'],trailing_bps='0',protective=False)
                if _decoded(intent['request']) != expected or intent['fingerprint'] != digest(expected):
                    raise ControlError('reserved parent intent differs from allocation')
                return self._result(intent, receipt, False)
            snapshot = self._snapshot(db)
            projection = _project_trial_snapshot(self.coordinator, baseline, snapshot,
                trial_client_ids=[row['client_id'] for row in snapshot['orders']], now_ms=now_ms,
                loss_budget_usdt='1', proposed_loss_reserve_usdt='0', coverage_complete=False)
            if (any(row['state'] in ACTIVE for row in snapshot['orders'])
                    or _accounting_number(projection['open_loss_reserve_usdt']) != 0
                    or any(row['quantity'] != '0' for row in snapshot['positions'])):
                raise ControlError('finish entry/exit reconciliation, including residual inventory, before reinvesting')
            receipts = db.execute('SELECT * FROM aibs_reinvestment_entries ORDER BY rowid').fetchall()
            registered = set()
            for row in receipts:
                if digest(_decoded(row['receipt'])) != row['receipt_sha256']:
                    raise ControlError('prior immutable allocation receipt changed')
                registered.add(row['client_id'])
            if any(_decoded(row['request'])['side']=='buy' and row['client_id'] not in registered
                   for row in snapshot['orders']):
                raise ControlError('unattributed entry cannot fund managed reinvestment')
            net = _accounting_number(snapshot['positions'][0]['realized'], signed=True) if snapshot['positions'] else number('0')
            seed = number(policy['seed_budget_usdt'])
            capital = max(seed + net, 0)
            cash = _accounting_number(next((row['total'] for row in snapshot['balances'] if row['asset']=='USDT'),'0'))
            budget = min(capital, number(policy['max_entry_budget_usdt']), cash,
                         number(self.coordinator.limits['max_order_quote']))
            market = db.execute("SELECT * FROM markets WHERE symbol='CRO/USDT'").fetchone()
            if market is None:
                raise ControlError('current instrument/market required')
            spec = _decoded(market['instrument'])
            step = number(spec['quantity_step'])
            fee = number(self.coordinator.limits['max_fee_bps']) / 10000
            def quantity_for(value):
                return (value / (price * (1 + fee)) / step).to_integral_value(rounding=ROUND_DOWN) * step
            quantity = quantity_for(budget)
            if quantity <= 0:
                raise ControlError('working capital cannot fund one quantity step')
            previous_quantity = number(_decoded(receipts[-1]['receipt'])['quantity_cro']) if receipts else quantity
            receipt = dict(client_id=client_id, baseline_sha256=baseline['baseline_sha256'],
                prepared_ms=now_ms, seed_budget_usdt=text_decimal(seed),
                net_realized_pnl_usdt=text_decimal(net), working_capital_usdt=text_decimal(capital),
                budget_cap_usdt=text_decimal(budget), limit_price=text_decimal(price),
                quantity_cro=text_decimal(quantity), maximum_quote_reservation_usdt=text_decimal(quantity*price*(1+fee)),
                profit_supported_additional_cro=text_decimal(max(quantity-quantity_for(seed),0)),
                additional_quantity_reference='SAME_SEED_AT_THIS_NEXT_ENTRY_PRICE_NOT_PREVIOUS_HOLDINGS',
                quantity_change_from_previous_entry_cro=text_decimal(quantity-previous_quantity),
                source_fill_checkpoint_sha256=digest(projection['source_fills']),
                independently_verified_exchange_coverage=False)
            intent = self.coordinator._prepare(db, client_id, 'CRO/USDT', 'buy',
                text_decimal(quantity), text_decimal(price), now_ms, text_decimal(stop), '0', protective=False)
            db.execute('INSERT INTO aibs_reinvestment_entries VALUES(?,?,?,?,?)',
                (client_id,encode(request),digest(request),encode(receipt),digest(receipt)))
            self.coordinator._event(db,'OFFLINE_REINVESTMENT_INTENT_RESERVED',
                {'client_id':client_id,'receipt_sha256':digest(receipt)})
            return self._result(intent, receipt, True)
