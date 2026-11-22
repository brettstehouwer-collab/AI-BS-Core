"""Opt-in OFFLINE entry admission over the unchanged execution coordinator.

Actual local closed losses drive the entry-only daily cutoff. Stop cash reserves
are explicitly modeled scenarios, never guaranteed maximum losses or proof of
native Exchange protection. No transport is supplied or enabled by this module.
"""
from contextvars import ContextVar
from decimal import localcontext, ROUND_DOWN
import sqlite3

from .crypto_execution_controls import (
    ACTIVE, ControlError, Held, OfflineExecutionCoordinator, digest, encode,
    identifier, number, stamp, text_decimal,
)
from .crypto_reinvestment import OfflineReinvestment
from .crypto_trial_budget import DAY_MS, assess_daily_budget
from .crypto_trial_projection import _decoded, _project_trial_snapshot


_BUY_GUARDS = {
    'aibs_trial_buy_prepare_guard': """CREATE TRIGGER aibs_trial_buy_prepare_guard
BEFORE INSERT ON orders WHEN json_extract(NEW.request,'$.side')='buy'
BEGIN
SELECT CASE WHEN NOT EXISTS (
 SELECT 1 FROM events WHERE kind='OFFLINE_TRIAL_ENTRY_ADMITTED'
 AND json_extract(payload,'$.phase')='PREPARATION'
 AND json_extract(payload,'$.client_id')=NEW.client_id
 AND json_extract(payload,'$.request_sha256')=NEW.fingerprint
 AND json_extract(payload,'$.baseline_sha256')=(SELECT json_extract(payload,'$.baseline_sha256') FROM aibs_trial_admission_policy WHERE id=1)
 AND json_extract(payload,'$.last_sequence')=(SELECT last_sequence FROM risk WHERE id=1)
) THEN RAISE(ABORT,'trial buy preparation admission required') END;
END""",
    'aibs_trial_buy_submit_guard': """CREATE TRIGGER aibs_trial_buy_submit_guard
BEFORE UPDATE OF state ON orders
WHEN NEW.state='SUBMITTING' AND OLD.state!='SUBMITTING' AND json_extract(NEW.request,'$.side')='buy'
BEGIN
SELECT CASE WHEN OLD.state!='INTENT' OR NOT EXISTS (
 SELECT 1 FROM events WHERE kind='OFFLINE_TRIAL_ENTRY_ADMITTED'
 AND json_extract(payload,'$.phase')='SUBMISSION'
 AND json_extract(payload,'$.client_id')=NEW.client_id
 AND json_extract(payload,'$.request_sha256')=NEW.fingerprint
 AND json_extract(payload,'$.baseline_sha256')=(SELECT json_extract(payload,'$.baseline_sha256') FROM aibs_trial_admission_policy WHERE id=1)
 AND json_extract(payload,'$.last_sequence')=(SELECT last_sequence FROM risk WHERE id=1)
 AND json_extract(payload,'$.expected_submission_sequence')=NEW.submission_sequence
) THEN RAISE(ABORT,'trial buy submission admission required') END;
END""",
}


class TrialEntryHeld(Held):
    """Only the trial's new entries are latched; the global risk flag is untouched."""


def modeled_entry_risk(request, spec, *, max_fee_bps, max_slippage_bps):
    quantity, price, stop = (number(request.get(key)) for key in ('quantity','limit_price','hard_stop'))
    step, tick, minimum, minimum_quantity = (number(spec.get(key)) for key in ('quantity_step','price_tick','minimum_notional','minimum_quantity'))
    fee, slip = number(max_fee_bps), number(max_slippage_bps)
    with localcontext() as context:
        context.prec = 96
        if (spec.get('base') != 'CRO' or spec.get('quote') != 'USDT' or quantity <= 0
                or step <= 0 or tick <= 0 or minimum <= 0 or minimum_quantity <= 0 or not 0 < stop < price
                or fee >= 10000 or slip >= 10000 or quantity % step or price % tick or stop % tick):
            raise ControlError('valid tick-aligned CRO/USDT entry and modeled risk inputs required')
        fee, slip = fee / 10000, slip / 10000
        assumed_exit = (stop * (1-slip) / tick).to_integral_value(rounding=ROUND_DOWN) * tick
        if assumed_exit <= 0:
            raise ControlError('modeled slipped stop must remain positive')
        cases, losses = [], []
        for buy_asset in ('USDT','CRO'):
            acquired = quantity * (1-fee) if buy_asset == 'CRO' else quantity
            debit = quantity * price * (1+fee if buy_asset == 'USDT' else 1)
            for sell_asset in ('USDT','CRO'):
                sell = ((acquired / (1+fee) if sell_asset == 'CRO' else acquired) / step).to_integral_value(rounding=ROUND_DOWN) * step
                if sell <= 0 or sell < minimum_quantity or sell * assumed_exit < minimum:
                    raise ControlError('modeled protective quantity below offline instrument minimum')
                cash = sell * assumed_exit * (1-fee if sell_asset == 'USDT' else 1)
                loss = max(debit-cash,0);losses.append(loss)
                cases.append(dict(entry_fee_asset=buy_asset,exit_fee_asset=sell_asset,
                    modeled_sell_quantity_cro=text_decimal(sell),entry_cash_usdt=text_decimal(debit),
                    modeled_exit_cash_usdt=text_decimal(cash),cash_loss_reserve_usdt=text_decimal(loss)))
        return dict(scope='MODELED_STOP_CASH_SHORTFALL_NOT_NATIVE_PROTECTION',
            loss_reserve_usdt=text_decimal(max(losses)),assumed_exit_price=text_decimal(assumed_exit),
            fee_cases=cases,guaranteed_maximum_loss=False,live_dispatch_enabled=False,ready_for_live=False)


class OfflineTrialAdmission(OfflineExecutionCoordinator):
    """A new opt-in subclass; every buy gate runs inside the original writer transaction."""
    def __init__(self, path):
        super().__init__(path)
        self._submission_context = ContextVar('offline_trial_submission',default=None)
        self._reinvestment = OfflineReinvestment(self)
        with self._tx() as db:
            policy = self._read_entry_policy(db)
        self._entry_policy_payload = encode(policy)

    @classmethod
    def register(cls, coordinator, *, daily_loss_budget_usdt):
        manager = OfflineReinvestment(coordinator)
        budget = number(daily_loss_budget_usdt)
        if budget <= 0:
            raise ControlError('positive daily closed-loss budget required')
        with coordinator._tx() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name IN ('aibs_trial_admission_policy','aibs_trial_entry_hold')").fetchone():
                raise ControlError('admission already registered; reopen without resetting')
            reinvestment = manager._read_policy(db)
            policy = dict(schema=1,scope='OFFLINE_DAILY_ENTRY_ADMISSION',account=coordinator.account,
                baseline_sha256=reinvestment['baseline']['baseline_sha256'],
                reinvestment_policy_sha256=digest(reinvestment),daily_loss_budget_usdt=text_decimal(budget),
                reserve_policy='FOUR_MODELED_STOP_FEE_CASES_NOT_A_GUARANTEE',
                buy_guard_sql_sha256=digest(_BUY_GUARDS))
            db.execute('CREATE TABLE aibs_trial_admission_policy(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')
            db.execute('CREATE TABLE aibs_trial_entry_hold(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)')
            db.execute('INSERT INTO aibs_trial_admission_policy VALUES(1,?,?)',(encode(policy),digest(policy)))
            for sql in _BUY_GUARDS.values():
                db.execute(sql)
        return cls(coordinator.path)

    def _read_entry_policy(self, db):
        try:
            row = db.execute('SELECT payload,fingerprint FROM aibs_trial_admission_policy WHERE id=1').fetchone()
        except sqlite3.Error as exc:
            raise ControlError('explicit trial admission registration required') from exc
        if row is None:
            raise ControlError('missing trial entry admission policy')
        policy = _decoded(row['payload'])
        expected = {'schema','scope','account','baseline_sha256','reinvestment_policy_sha256',
                    'daily_loss_budget_usdt','reserve_policy','buy_guard_sql_sha256'}
        reinvestment = self._reinvestment._read_policy(db)
        if (policy.keys()!=expected or type(policy['schema']) is not int or policy['schema']!=1
                or policy['scope']!='OFFLINE_DAILY_ENTRY_ADMISSION'
                or policy['reserve_policy']!='FOUR_MODELED_STOP_FEE_CASES_NOT_A_GUARANTEE'
                or policy['buy_guard_sql_sha256']!=digest(_BUY_GUARDS)
                or digest(policy)!=row['fingerprint'] or policy['account']!=self.account
                or policy['baseline_sha256']!=reinvestment['baseline']['baseline_sha256']
                or policy['reinvestment_policy_sha256']!=digest(reinvestment)
                or number(policy['daily_loss_budget_usdt'])<=0
                or (hasattr(self,'_entry_policy_payload') and encode(policy)!=self._entry_policy_payload)):
            raise ControlError('immutable trial admission policy differs')
        stored = {row['name']:row['sql'] for row in db.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name IN ('aibs_trial_buy_prepare_guard','aibs_trial_buy_submit_guard')")}
        if stored != _BUY_GUARDS:
            raise ControlError('trial buy database guards missing or changed')
        return policy

    def _entry_hold(self, db, policy):
        row = db.execute('SELECT payload,fingerprint FROM aibs_trial_entry_hold WHERE id=1').fetchone()
        if row is None:
            return None
        held = _decoded(row['payload'])
        if (digest(held)!=row['fingerprint'] or held.get('baseline_sha256')!=policy['baseline_sha256']
                or held.get('daily_loss_budget_usdt')!=policy['daily_loss_budget_usdt']
                or held.get('reason')!='DAILY_CLOSED_LOSS_ALLOWANCE_EXHAUSTED'):
            raise ControlError('entry-only cutoff evidence differs')
        return held

    def _closed_review(self, db, now_ms):
        policy = self._read_entry_policy(db)
        baseline = self._reinvestment._read_policy(db)['baseline']
        now_ms=stamp(now_ms)
        if not baseline['started_ms'] <= now_ms < baseline['day_start_ms']+DAY_MS:
            raise ControlError('explicit current-day baseline required for entry admission')
        snapshot = OfflineReinvestment._snapshot(db)
        projection = _project_trial_snapshot(self,baseline,snapshot,
            trial_client_ids=[row['client_id'] for row in snapshot['orders']],now_ms=now_ms,
            loss_budget_usdt=policy['daily_loss_budget_usdt'],proposed_loss_reserve_usdt='0',coverage_complete=False)
        review = assess_daily_budget(baseline,now_ms=now_ms,account=self.account,
            loss_budget_usdt=policy['daily_loss_budget_usdt'],closed_outcomes=projection['closed_outcomes'],
            open_loss_reserve_usdt='0',pending_loss_reserve_usdt='0',proposed_loss_reserve_usdt='0',
            coverage_complete=True)
        return policy,baseline,snapshot,projection,review

    def _latch_closed_loss(self, db, policy, review, now_ms):
        if self._entry_hold(db,policy) is None and review['daily_cutoff_triggered']:
            held=dict(reason='DAILY_CLOSED_LOSS_ALLOWANCE_EXHAUSTED',baseline_sha256=policy['baseline_sha256'],
                daily_loss_budget_usdt=policy['daily_loss_budget_usdt'],
                closed_loss_usdt=review['closed_loss_usdt'],observed_ms=now_ms)
            db.execute('INSERT INTO aibs_trial_entry_hold VALUES(1,?,?)',(encode(held),digest(held)))
            self._event(db,'OFFLINE_TRIAL_NEW_ENTRIES_HELD',held)
        return self._entry_hold(db,policy)

    def refresh_entry_hold(self, *, now_ms):
        with self._tx() as db:
            policy,baseline,snapshot,projection,review=self._closed_review(db,now_ms)
            self._latch_closed_loss(db,policy,review,now_ms)
        return self.entry_status()

    def entry_status(self):
        with self._tx() as db:
            policy=self._read_entry_policy(db);held=self._entry_hold(db,policy)
            return dict(scope='OFFLINE_DAILY_ENTRY_ADMISSION',entry_held=held is not None,
                local_cutoff_enforced=True,live_daily_cutoff_enforced=False,
                daily_loss_budget_usdt=policy['daily_loss_budget_usdt'],
                native_protection_qualified=False,guaranteed_maximum_loss=False,
                live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)

    def _check_entry(self, db, client_id, request, now_ms, *, submitting):
        policy,baseline,snapshot,projection,review=self._closed_review(db,now_ms)
        if self._latch_closed_loss(db,policy,review,now_ms):
            raise TrialEntryHeld('trial new-entry daily closed-loss cutoff held; exits remain available')
        if (any(row['state'] in ACTIVE and row['client_id']!=client_id for row in snapshot['orders'])
                or any(row['quantity']!='0' or row['basis']!='0' for row in snapshot['positions'])):
            raise ControlError('single-position trial requires reconciled flat inventory and no other active order')
        if submitting:
            allocation=db.execute('SELECT * FROM aibs_reinvestment_entries WHERE client_id=?',(client_id,)).fetchone()
            order=self._order(db,client_id)
            if allocation is None or order['state']!='INTENT':
                raise ControlError('registered immutable reinvestment intent required before submission')
            receipt,recorded=_decoded(allocation['receipt']),_decoded(allocation['request'])
            expected=dict(symbol='CRO/USDT',side='buy',quantity=receipt.get('quantity_cro'),
                limit_price=recorded.get('limit_price'),hard_stop=recorded.get('hard_stop'),
                trailing_bps='0',protective=False)
            if (digest(receipt)!=allocation['receipt_sha256'] or digest(recorded)!=allocation['request_sha256']
                    or receipt.get('client_id')!=client_id or recorded.get('client_id')!=client_id
                    or recorded.get('baseline_sha256')!=baseline['baseline_sha256']
                    or receipt.get('baseline_sha256')!=baseline['baseline_sha256']
                    or request!=expected or order['fingerprint']!=digest(expected)):
                raise ControlError('allocation receipt and parent submission intent differ')
        market=db.execute("SELECT instrument FROM markets WHERE symbol='CRO/USDT'").fetchone()
        if market is None:
            raise ControlError('current offline instrument required')
        modeled=modeled_entry_risk(request,_decoded(market['instrument']),
            max_fee_bps=self.limits['max_fee_bps'],max_slippage_bps=self.limits['max_slippage_bps'])
        assessment=assess_daily_budget(baseline,now_ms=now_ms,account=self.account,
            loss_budget_usdt=policy['daily_loss_budget_usdt'],closed_outcomes=projection['closed_outcomes'],
            open_loss_reserve_usdt='0',pending_loss_reserve_usdt='0',
            proposed_loss_reserve_usdt=modeled['loss_reserve_usdt'],coverage_complete=True)
        if not assessment['proposed_fits']:
            raise ControlError('modeled stop cash shortfall exceeds remaining daily entry allowance')
        self._event(db,'OFFLINE_TRIAL_ENTRY_ADMITTED',dict(client_id=client_id,
            phase='SUBMISSION' if submitting else 'PREPARATION',checked_ms=now_ms,
            closed_loss_usdt=assessment['closed_loss_usdt'],modeled_loss_reserve_usdt=modeled['loss_reserve_usdt'],
            baseline_sha256=baseline['baseline_sha256'],guaranteed_maximum_loss=False,
            request_sha256=digest(request),last_sequence=snapshot['risk']['last_sequence'],
            expected_submission_sequence=snapshot['risk']['submission_sequence']+1 if submitting else None))

    def prepare(self, client_id, *, symbol, side, quantity, limit_price, now_ms,
                hard_stop=None, trailing_bps='0'):
        if side=='buy':
            raise ControlError('new trial buys require OfflineReinvestment.reserve_entry')
        return super().prepare(client_id,symbol=symbol,side=side,quantity=quantity,
            limit_price=limit_price,now_ms=now_ms,hard_stop=hard_stop,trailing_bps=trailing_bps)

    def _prepare(self, db, client_id, symbol, side, quantity, limit_price, now_ms,
                 hard_stop, trailing_bps, *, protective):
        if side=='buy' and not db.execute('SELECT 1 FROM orders WHERE client_id=?',(identifier(client_id),)).fetchone():
            self._check_entry(db,client_id,dict(symbol=symbol,side=side,quantity=quantity,
                limit_price=limit_price,hard_stop=hard_stop,trailing_bps=trailing_bps,protective=protective),
                now_ms,submitting=False)
        return super()._prepare(db,client_id,symbol,side,quantity,limit_price,now_ms,
            hard_stop,trailing_bps,protective=protective)

    def begin_submission(self, client_id, *, now_ms):
        token=self._submission_context.set((identifier(client_id),stamp(now_ms)))
        try:
            return super().begin_submission(client_id,now_ms=now_ms)
        finally:
            self._submission_context.reset(token)

    def _gate(self, db):
        super()._gate(db)
        context=self._submission_context.get()
        if context is not None:
            client_id,now_ms=context
            order=self._order(db,client_id);request=_decoded(order['request'])
            if request.get('side')=='buy':
                self._check_entry(db,client_id,request,now_ms,submitting=True)
