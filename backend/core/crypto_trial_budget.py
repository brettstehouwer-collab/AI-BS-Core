"""Offline trial loss-allowance arithmetic; no persistence or dispatch authority.

A baseline hash binds supplied facts, not their authenticity. Outcomes must be
reconciled closed lots: gross quote PnL excludes fees, fees are quote-valued once.
Deposits, withdrawals and pre-existing inventory are not closed trial outcomes.
UTC day boundaries and non-replenishing loss allowance are proposed policy only.
Supplied stop-loss reserves cannot guarantee maximum loss on a market order.
"""
from decimal import Decimal, InvalidOperation, localcontext
from uuid import UUID
import re

from .crypto_execution_controls import (
    ControlError, digest, identifier, number, stamp, text_decimal,
)

DAY_MS = 86400000
_BASELINE_FIELDS = frozenset((
    'schema', 'scope', 'trial_id', 'account', 'started_ms', 'day_start_ms',
    'opening_receipt_sha256', 'baseline_sha256',
))
_OUTCOME_FIELDS = frozenset((
    'event_id', 'trial_id', 'account', 'closed_ms', 'gross_pnl_usdt', 'fees_usdt',
))



def _accounting_number(value, *, signed=False):
    """Retain derived coordinator precision without widening order/config inputs."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)) or len(str(value)) > 200:
        raise ControlError('bounded accounting decimal required')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ControlError('invalid accounting decimal') from exc
    if (not result.is_finite() or result.copy_abs() > Decimal('1e22')
            or (not signed and result < 0) or len(result.as_tuple().digits) > 128
            or not -144 <= result.as_tuple().exponent <= 22):
        raise ControlError('accounting decimal outside supported precision')
    return result

def create_baseline(*, trial_id, account, started_ms, day_start_ms,
                    opening_receipt_sha256):
    """Bind caller-supplied current-trial facts; do not register a live epoch."""
    if type(trial_id) is not str:
        raise ControlError('canonical trial UUID required')
    try:
        if str(UUID(trial_id)) != trial_id:
            raise ValueError('noncanonical UUID')
    except ValueError as exc:
        raise ControlError('canonical trial UUID required') from exc
    account = identifier(account)
    started_ms, day_start_ms = stamp(started_ms), stamp(day_start_ms)
    if day_start_ms % DAY_MS or not day_start_ms <= started_ms < day_start_ms + DAY_MS:
        raise ControlError('trial start must belong to the supplied UTC day')
    if (type(opening_receipt_sha256) is not str
            or not re.fullmatch('[0-9a-f]{64}', opening_receipt_sha256)):
        raise ControlError('lowercase SHA-256 opening receipt reference required')
    baseline = dict(schema=1, scope='OFFLINE_TRIAL_BASELINE', trial_id=trial_id,
        account=account, started_ms=started_ms, day_start_ms=day_start_ms,
        opening_receipt_sha256=opening_receipt_sha256)
    return dict(baseline, baseline_sha256=digest(baseline))


def _validated_baseline(baseline):
    if type(baseline) is not dict or baseline.keys() != _BASELINE_FIELDS:
        raise ControlError('complete closed baseline schema required')
    expected = create_baseline(**{key: baseline[key] for key in (
        'trial_id', 'account', 'started_ms', 'day_start_ms', 'opening_receipt_sha256')})
    if (type(baseline['schema']) is not int or baseline != expected):
        raise ControlError('baseline facts or digest changed')
    return expected


def assess_daily_budget(baseline, *, now_ms, account, loss_budget_usdt,
                        closed_outcomes, open_loss_reserve_usdt,
                        pending_loss_reserve_usdt, proposed_loss_reserve_usdt,
                        coverage_complete):
    """Assess supplied loss facts; a fitting proposal never enables an order.

    coverage_complete is a caller assertion, not an Exchange coverage proof.
    Missing reserves stay unknown. A new day requires an explicit new baseline;
    callers must carry open positions and pending orders forward themselves.
    """
    baseline = _validated_baseline(baseline)
    now_ms = stamp(now_ms)
    if (identifier(account) != baseline['account']
            or not baseline['started_ms'] <= now_ms < baseline['day_start_ms'] + DAY_MS):
        raise ControlError('matching account and current baseline day required')
    if type(coverage_complete) is not bool:
        raise ControlError('explicit coverage assertion required')
    budget = number(loss_budget_usdt)
    if budget <= 0:
        raise ControlError('positive loss budget required')
    reserves = {key: _accounting_number(value) if value is not None else None for key, value in (
        ('open', open_loss_reserve_usdt), ('pending', pending_loss_reserve_usdt),
        ('proposed', proposed_loss_reserve_usdt))}
    if type(closed_outcomes) is not list or len(closed_outcomes) > 10000:
        raise ControlError('bounded list of at most 10000 closed outcomes required')
    blockers = ['MISSING_' + key.upper() + '_LOSS_RESERVE'
                for key, value in reserves.items() if value is None]
    if not coverage_complete:
        blockers.append('CURRENT_TRIAL_ACTIVITY_COVERAGE_UNVERIFIED')
    with localcontext() as context:
        context.prec = 96
        closed_loss = number('0')
        seen = set()
        for outcome in closed_outcomes:
            if type(outcome) is not dict or outcome.keys() != _OUTCOME_FIELDS:
                raise ControlError('closed trial outcome fields required; flows are not outcomes')
            event_id = identifier(outcome['event_id'])
            if event_id in seen:
                raise ControlError('duplicate closed outcome identity')
            seen.add(event_id)
            if (outcome['trial_id'] != baseline['trial_id'] or outcome['account'] != account
                    or not baseline['started_ms'] <= stamp(outcome['closed_ms']) <= now_ms):
                raise ControlError('outcome outside the current trial, account or time interval')
            gross, fees = _accounting_number(outcome['gross_pnl_usdt'], signed=True), number(outcome['fees_usdt'])
            closed_loss += max(fees - gross, 0)
        used = (closed_loss + reserves['open'] + reserves['pending']
                if reserves['open'] is not None and reserves['pending'] is not None else None)
        remaining = max(budget - used, 0) if used is not None else None
        triggered = used >= budget if used is not None else None
        if triggered:
            blockers.append('LOSS_ALLOWANCE_EXHAUSTED')
        if (remaining is not None and reserves['proposed'] is not None
                and reserves['proposed'] > remaining):
            blockers.append('PROPOSED_LOSS_RESERVE_EXCEEDS_REMAINING_ALLOWANCE')
        fits = not blockers and triggered is False
        return {
            'scope': 'OFFLINE_TRIAL_BUDGET_ASSESSMENT_NOT_ORDER_ADMISSION',
            'trial_id': baseline['trial_id'], 'baseline_sha256': baseline['baseline_sha256'],
            'day_start_ms': baseline['day_start_ms'], 'assessed_ms': now_ms,
            'policy': 'PROPOSED_UTC_GROSS_CLOSED_LOSSES_PLUS_RESERVES_NO_PROFIT_REPLENISHMENT',
            'loss_budget_usdt': text_decimal(budget),
            'closed_loss_usdt': text_decimal(closed_loss),
            'used_usdt': text_decimal(used) if used is not None else None,
            'remaining_usdt': text_decimal(remaining) if remaining is not None else None,
            'loss_reserves_usdt': {key: text_decimal(value) if value is not None else None
                                   for key, value in reserves.items()},
            'daily_cutoff_triggered': triggered, 'proposed_fits': fits,
            'blocking_checks': blockers, 'coverage_complete_asserted': coverage_complete,
            'inputs_independently_verified': False, 'daily_cutoff_enforced': False,
            'live_dispatch_enabled': False, 'ready_for_live': False, 'orders_sent': 0,
            'guaranteed_maximum_loss': False,
        }
