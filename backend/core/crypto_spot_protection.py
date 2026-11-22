"""Current-trial protection review from existing arithmetic; never an order."""
from decimal import localcontext
from .crypto_execution_controls import ControlError, number, text_decimal


def review_cro_protection(preview, *, stop_type=None, trigger_reference_type=None,
                          stop_limit_price=None, price_tick=None,
                          minimum_notional_usd=None, usdt_usd_index=None):
    if stop_type is not None and (type(stop_type) is not str or stop_type not in ('STOP_LOSS','STOP_LIMIT')):
        raise ControlError('supported draft stop type required')
    if trigger_reference_type is not None and (type(trigger_reference_type) is not str
            or trigger_reference_type not in ('LAST_PRICE','MARK_PRICE','INDEX_PRICE')):
        raise ControlError('supported draft trigger reference required')
    if stop_limit_price is not None and stop_type != 'STOP_LIMIT':
        raise ControlError('limit price belongs only to a stop-limit draft')
    execution_minimum, index = None, None
    if minimum_notional_usd is not None or usdt_usd_index is not None:
        if minimum_notional_usd is None or usdt_usd_index is None:
            raise ControlError('both modeled minimum and USD index required')
        execution_minimum, index = number(minimum_notional_usd), number(usdt_usd_index)
        if execution_minimum <= 0 or index <= 0:
            raise ControlError('positive modeled minimum and USD index required')
    if (not isinstance(preview, dict) or preview.get('scope') != 'ARITHMETIC_PREVIEW_NOT_ACCOUNT_OR_ORDER'
            or preview.get('symbol') != 'CRO/USDT' or preview.get('ready_for_live') is not False
            or preview.get('live_dispatch_enabled') is not False or type(preview.get('orders_sent')) is not int
            or preview['orders_sent'] != 0):
        raise ControlError('held CRO/USDT arithmetic preview required')
    try:
        entry, risk, scenarios = preview['entry'], preview['risk_choices'], preview['fee_currency_scenarios']
        budget, entry_price = number(entry['budget_all_in_usdt']), number(entry['limit_price'])
        stop = number(risk['stop']) if risk['stop'] is not None else None
        target = number(risk['target']) if risk['target'] is not None else None
        daily = number(risk['daily_loss_budget']) if risk['daily_loss_budget'] is not None else None
        if (budget <= 0 or entry_price <= 0 or (stop is not None and not 0 < stop < entry_price)
                or (target is not None and target <= entry_price) or (daily is not None and daily <= 0)
                or not isinstance(scenarios, list) or len(scenarios) != 4):
            raise ControlError('valid current-trial arithmetic choices required')
        cases, seen = [], set()
        for scenario in scenarios:
            assets = (scenario['entry_fee_asset'], scenario['exit_fee_asset'])
            if assets in seen or assets not in {('USDT','USDT'),('USDT','CRO'),('CRO','USDT'),('CRO','CRO')}:
                raise ControlError('four unique modeled fee-asset cases required')
            seen.add(assets)
            quantity = number(scenario['sell_quantity_cro'])
            residual = number(scenario['residual_cro_after_assumed_exit'])
            stops = [level for level in scenario['levels'] if level['assumed_execution'] == 'stop']
            minimum = None
            if stop is None:
                if stops:
                    raise ControlError('unexpected stop scenario')
            else:
                if (len(stops) != 1 or number(stops[0]['price']) != stop
                        or type(stops[0]['meets_minimum_at_assumed_execution_price']) is not bool):
                    raise ControlError('matching stop scenario and minimum fact required')
                minimum = stops[0]['meets_minimum_at_assumed_execution_price']
            cases.append({'entry_fee_asset':assets[0], 'exit_fee_asset':assets[1],
                'sell_quantity_cro':text_decimal(quantity),
                'residual_cro_after_assumed_exit':text_decimal(residual),
                'stop_minimum_at_assumed_price':minimum})
    except (KeyError, TypeError, IndexError) as error:
        raise ControlError('complete modeled protection facts required') from error
    limit = None
    if stop_limit_price is not None:
        limit = number(stop_limit_price)
        tick = number(price_tick)
        with localcontext() as context:
            context.prec = 96
            if limit <= 0 or tick <= 0 or stop is None or limit > stop or limit % tick:
                raise ControlError('positive tick-aligned stop limit at or below trigger required')
    for case in cases:
        eligible = None
        if stop_type == 'STOP_LIMIT' and limit is not None and execution_minimum is not None:
            with localcontext() as context:
                context.prec = 96
                eligible = number(case['sell_quantity_cro']) * limit * index >= execution_minimum
        case['stop_limit_minimum_at_assumed_price'] = eligible
    blockers = ['CURRENT_TRIAL_OPENING_STATE_UNVERIFIED', 'ACTUAL_FILL_QUANTITY_AND_FEES_UNVERIFIED',
        'PARTIAL_FILL_PROTECTION_UNVERIFIED', 'NATIVE_STOP_ACCEPTANCE_UNVERIFIED',
        'DAILY_CUTOFF_NOT_ENFORCED']
    if stop_type is None:
        blockers.append('STOP_TYPE_SELECTION_REQUIRED')
    if trigger_reference_type is None:
        blockers.append('TRIGGER_REFERENCE_SELECTION_REQUIRED')
    if stop_type == 'STOP_LIMIT' and limit is None:
        blockers.append('MISSING_STOP_LIMIT_PRICE')
    if stop_type == 'STOP_LIMIT' and execution_minimum is None:
        blockers.append('STOP_LIMIT_EXECUTION_MINIMUM_UNVERIFIED')
    if any(case['stop_limit_minimum_at_assumed_price'] is False for case in cases):
        blockers.append('STOP_LIMIT_EXECUTION_BELOW_MINIMUM_IN_SOME_SCENARIOS')
    if stop is None:
        blockers.append('MISSING_STOP_TRIGGER')
    if daily is None:
        blockers.append('MISSING_DAILY_LOSS_BUDGET')
    if any(case['stop_minimum_at_assumed_price'] is False for case in cases):
        blockers.append('PROTECTIVE_EXIT_BELOW_MINIMUM_IN_SOME_SCENARIOS')
    return {'scope':'PROTECTION_REVIEW_NOT_AN_ORDER', 'symbol':'CRO/USDT',
        'budget_all_in_usdt':text_decimal(budget), 'trigger_price':text_decimal(stop) if stop is not None else None,
        'target_price':text_decimal(target) if target is not None else None,
        'daily_loss_budget_usdt':text_decimal(daily) if daily is not None else None,
        'selected_stop_type':stop_type, 'trigger_reference_type':trigger_reference_type,
        'stop_limit_minimum_rule_inputs_supplied':execution_minimum is not None,
        'trigger_minimum_is_not_limit_minimum':stop_type == 'STOP_LIMIT',
        'stop_options':[
            {'type':'STOP_LOSS','description':'Triggers a market order; execution price and complete fill are not guaranteed.'},
            {'type':'STOP_LIMIT','limit_price':text_decimal(limit) if limit is not None else None,'description':'Triggers a limit order; it may remain unfilled while price continues falling.'}],
        'fee_currency_cases':cases,
        'static_quantity_candidate_cro':text_decimal(min(number(case['sell_quantity_cro']) for case in cases)),
        'static_quantity_is_full_position_coverage':False,
        'quantity_policy':'Reconcile actual fills and fee currency before sizing; a conservative static quantity can leave unprotected residual.',
        'partial_fill_policy':'Entry partial fills may be below the exit minimum; separate entry/stop submission leaves an unprotected interval.',
        'historical_profit_review_required':False, 'opening_state_required':True,
        'opening_state_scope':'Current balances, ordinary/advanced orders, positions/liabilities and activity after an explicit trial start.',
        'daily_cutoff_enforced':False, 'full_position_protection_verified':False,
        'partial_fill_protection_verified':False, 'native_order_accepted':False,
        'guaranteed_maximum_loss':False, 'live_dispatch_enabled':False,
        'ready_for_live':False, 'orders_sent':0, 'blocking_checks':blockers}
