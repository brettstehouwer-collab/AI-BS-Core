"""Project one dedicated offline trial's applied fills into loss-budget facts.

This reads the existing coordinator snapshot; it neither applies fills nor adds
an admission gate. Pre-existing or unattributed inventory is refused, not given
an invented cost. Full principal remains reserved until protective execution is
qualified. This is a local bookkeeping projection, never Exchange coverage proof.
"""
from decimal import localcontext
import json

from .crypto_execution_controls import (
    ACTIVE, ControlError, OfflineExecutionCoordinator, digest, encode,
    identifier, number, stamp, text_decimal,
)
from .crypto_trial_budget import assess_daily_budget

_SYMBOL = 'CRO/USDT'
_FILL_FIELDS = frozenset(('fill_id', 'client_id', 'receipt_key', 'exchange_order_id',
    'symbol', 'side', 'quantity', 'cost', 'fees', 'fees_complete', 'sequence', 'occurred_ms'))


def _decoded(raw):
    if type(raw) is not str or len(raw) > 10000:
        raise ControlError('bounded canonical coordinator record required')
    try:
        value = json.loads(raw)
        if type(value) is not dict or encode(value) != raw:
            raise ValueError('noncanonical object')
    except (ValueError, TypeError) as exc:
        raise ControlError('canonical coordinator object required') from exc
    return value


def _project_trial_snapshot(coordinator, baseline, snapshot, *, trial_client_ids, now_ms,
                         loss_budget_usdt, proposed_loss_reserve_usdt,
                         coverage_complete=False):
    """Read a temporary dedicated trial store; keep all dispatch authority held.

    Closed outcomes mirror the coordinator's weighted-average cost basis per
    applied sell fill. Entry fees are capitalized once; exit quote fees remain
    explicit. Original fill identities/hashes are retained alongside outcomes.
    Snapshot consistency is local only; coverage remains a caller assertion.
    """
    if not isinstance(coordinator, OfflineExecutionCoordinator) or coordinator.quote != 'USDT':
        raise ControlError('existing USDT offline coordinator required')
    # Reuse the baseline/time/numeric validator before reading the store.
    assess_daily_budget(baseline, now_ms=now_ms, account=coordinator.account,
        loss_budget_usdt=loss_budget_usdt, closed_outcomes=[],
        open_loss_reserve_usdt=None, pending_loss_reserve_usdt=None,
        proposed_loss_reserve_usdt=proposed_loss_reserve_usdt,
        coverage_complete=coverage_complete)
    if type(trial_client_ids) not in (list, tuple) or len(trial_client_ids) > 10000:
        raise ControlError('bounded explicit trial membership required')
    members = [identifier(value) for value in trial_client_ids]
    if len(set(members)) != len(members):
        raise ControlError('duplicate trial intent membership')
    if (snapshot['scope'] != 'OFFLINE_ONLY' or snapshot['live_dispatch_enabled'] is not False
            or snapshot['risk']['halted'] or snapshot['unmatched_fills']):
        raise ControlError('unresolved or held offline accounting')
    if len(snapshot['fills']) > 10000 or len(snapshot['orders']) > 10000:
        raise ControlError('trial projection exceeds bounded record count')
    orders = {row['client_id']: row for row in snapshot['orders']}
    if len(orders) != len(snapshot['orders']) or set(orders) != set(members):
        raise ControlError('trial membership must cover the dedicated store exactly')
    requests, totals = {}, {}
    for client_id, row in orders.items():
        request = _decoded(row['request'])
        if (digest(request) != row['fingerprint'] or request.get('symbol') != _SYMBOL
                or request.get('side') not in ('buy', 'sell')
                or row['state'] not in (*ACTIVE, 'FILLED', 'CANCELLED', 'REJECTED')
                or row['state'] in ('SUBMITTING', 'UNKNOWN')
                or not baseline['started_ms'] <= stamp(row['created_ms']) <= now_ms):
            raise ControlError('unresolved or unattributed trial order')
        quantity, price = number(request.get('quantity')), number(request.get('limit_price'))
        if quantity <= 0 or price <= 0:
            raise ControlError('positive trial order quantity and price required')
        requests[client_id] = request
        totals[client_id] = [number('0'), number('0')]
    fills, keys, sequences = [], set(), set()
    for row in snapshot['fills']:
        fill = _decoded(row['payload'])
        if (fill.keys() != _FILL_FIELDS or row['state'] != 'APPLIED'
                or fill['client_id'] != row['client_id'] or row['client_id'] not in orders
                or fill['symbol'] != _SYMBOL or fill['side'] != requests[row['client_id']]['side']
                or identifier(fill['fill_id']) != fill['fill_id']
                or fill['receipt_key'] != encode([_SYMBOL, fill['fill_id']])
                or row['fill_id'] != fill['receipt_key'] or digest(fill) != row['fingerprint']
                or fill['fees_complete'] is not True or type(fill['fees']) is not dict
                or any(asset not in ('CRO', 'USDT') for asset in fill['fees'])
                or orders[row['client_id']]['state'] == 'INTENT'
                or orders[row['client_id']]['exchange_id'] != fill['exchange_order_id']
                or not max(baseline['started_ms'], orders[row['client_id']]['created_ms'])
                    <= stamp(fill['occurred_ms']) <= now_ms):
            raise ControlError('complete attributed applied fill required')
        sequence = stamp(fill['sequence'])
        if row['fill_id'] in keys or sequence in sequences:
            raise ControlError('duplicate fill identity or application sequence')
        keys.add(row['fill_id']);sequences.add(sequence)
        fills.append((sequence, row, fill))
    if (sequences != set(range(1, len(fills) + 1))
            or stamp(snapshot['risk']['last_sequence']) != len(fills)):
        raise ControlError('complete applied sequence from the trial opening required')
    with localcontext() as context:
        context.prec = 96
        held, basis, realized = number('0'), number('0'), number('0')
        outcomes, sources = [], []
        for sequence, row, fill in sorted(fills, key=lambda item: item[0]):
            quantity, cost = number(fill['quantity']), number(fill['cost'])
            base_fee, quote_fee = (number(fill['fees'].get(asset, '0')) for asset in ('CRO', 'USDT'))
            if quantity <= 0 or cost <= 0:
                raise ControlError('positive applied quantity and cost required')
            if fill['side'] == 'buy':
                received = quantity - base_fee
                if received <= 0:
                    raise ControlError('nonpositive received trial inventory')
                held += received;basis += cost + quote_fee
            else:
                removed = quantity + base_fee
                if removed > held or held <= 0:
                    raise ControlError('trial sell consumes unattributed inventory')
                removed_basis = basis if removed == held else basis * removed / held
                gross = cost - removed_basis
                held -= removed;basis -= removed_basis
                realized += cost - quote_fee - removed_basis
                outcomes.append(dict(event_id=digest({'receipt_key': row['fill_id']}),
                    trial_id=baseline['trial_id'], account=coordinator.account,
                    closed_ms=fill['occurred_ms'], gross_pnl_usdt=text_decimal(gross),
                    fees_usdt=text_decimal(quote_fee)))
            totals[fill['client_id']][0] += quantity
            totals[fill['client_id']][1] += cost
            sources.append({'fill_id':fill['fill_id'], 'receipt_key':row['fill_id'],
                'sequence':sequence, 'fingerprint':row['fingerprint']})
        positions = snapshot['positions']
        if positions:
            if (len(positions) != 1 or positions[0]['symbol'] != _SYMBOL
                    or any(positions[0][key] != text_decimal(value)
                           for key, value in (('quantity', held), ('basis', basis), ('realized', realized)))):
                raise ControlError('position differs from attributed trial fills')
        elif held or basis or realized:
            raise ControlError('missing attributed position')
        balances = {row['asset']:row['total'] for row in snapshot['balances']}
        if (balances.get('CRO', '0') != text_decimal(held)
                or any(value != '0' for asset, value in balances.items() if asset not in ('CRO', 'USDT'))):
            raise ControlError('unattributed or pre-existing inventory in dedicated trial store')
        pending = number('0')
        fee_cap = number(coordinator.limits['max_fee_bps']) / 10000
        for client_id, row in orders.items():
            request = requests[client_id]
            quantity, price = number(request['quantity']), number(request['limit_price'])
            filled, cost = totals[client_id]
            remaining = quantity - filled
            if (remaining < 0 or row['filled_quantity'] != text_decimal(filled)
                    or row['filled_cost'] != text_decimal(cost)):
                raise ControlError('order totals differ from applied trial fills')
            buy = request['side'] == 'buy'
            reserve = remaining * (price if buy else 1) * (1 + fee_cap) if row['state'] in ACTIVE else number('0')
            if (row['reserve_asset'] != ('USDT' if buy else 'CRO')
                    or row['reserve_amount'] != text_decimal(reserve)):
                raise ControlError('order reservation differs from attributed remainder')
            if buy and row['state'] in ACTIVE:
                pending += reserve
        assessment = assess_daily_budget(baseline, now_ms=now_ms, account=coordinator.account,
            loss_budget_usdt=loss_budget_usdt, closed_outcomes=outcomes,
            open_loss_reserve_usdt=basis, pending_loss_reserve_usdt=pending,
            proposed_loss_reserve_usdt=proposed_loss_reserve_usdt,
            coverage_complete=coverage_complete)
        return {'scope':'OFFLINE_APPLIED_FILL_PROJECTION_NOT_ADMISSION',
            'baseline_sha256':baseline['baseline_sha256'], 'closed_outcomes':outcomes,
            'source_fills':sources, 'open_loss_reserve_usdt':text_decimal(basis),
            'pending_loss_reserve_usdt':text_decimal(pending), 'assessment':assessment,
            'reserve_policy':'FULL_BUY_PRINCIPAL_UNTIL_NATIVE_PROTECTION_QUALIFIED',
            'outcome_policy':'COORDINATOR_WEIGHTED_AVERAGE_BASIS_PER_APPLIED_SELL_FILL',
            'exchange_coverage_verified':False, 'daily_cutoff_enforced':False,
            'live_dispatch_enabled':False, 'ready_for_live':False, 'orders_sent':0}


def project_trial_budget(coordinator, baseline, *, trial_client_ids, now_ms,
                         loss_budget_usdt, proposed_loss_reserve_usdt,
                         coverage_complete=False):
    """Read the actual offline store; internal callers may reuse their own transaction."""
    if not isinstance(coordinator, OfflineExecutionCoordinator) or coordinator.quote != 'USDT':
        raise ControlError('existing USDT offline coordinator required')
    return _project_trial_snapshot(coordinator, baseline, coordinator.snapshot(),
        trial_client_ids=trial_client_ids, now_ms=now_ms,
        loss_budget_usdt=loss_budget_usdt,
        proposed_loss_reserve_usdt=proposed_loss_reserve_usdt,
        coverage_complete=coverage_complete)
