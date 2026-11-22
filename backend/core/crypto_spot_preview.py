"""Stateless CRO/USDT arithmetic preview; no account, ledger or order authority."""
from decimal import localcontext, ROUND_DOWN, ROUND_CEILING

from .crypto_execution_controls import ControlError, number, text_decimal


def preview_cro_spot(*, budget_usdt, bid, ask, quantity_step, price_tick,
                     minimum_notional_usd, usdt_usd_index, entry_fee_bps, exit_fee_bps,
                     target_price=None, stop_price=None, max_exposure_usdt=None,
                     daily_loss_budget_usdt=None):
    values = {name: number(value) for name, value in {
        'budget': budget_usdt, 'bid': bid, 'ask': ask, 'quantity_step': quantity_step,
        'price_tick': price_tick, 'minimum_usd': minimum_notional_usd,
        'usd_index': usdt_usd_index, 'entry_bps': entry_fee_bps, 'exit_bps': exit_fee_bps}.items()}
    if any(values[name] <= 0 for name in ('budget', 'bid', 'ask', 'quantity_step', 'price_tick', 'minimum_usd', 'usd_index')):
        raise ControlError('positive budget, prices, ticks, minimum and USD index required')
    with localcontext() as context:
        context.prec = 96
        if (values['entry_bps'] >= 10000 or values['exit_bps'] >= 10000
                or values['bid'] >= values['ask']
                or values['bid'] % values['price_tick'] or values['ask'] % values['price_tick']):
            raise ControlError('uncrossed tick-aligned book and fee fractions below1 required')
    optional = {name: number(value) if value is not None else None for name, value in {
        'target': target_price, 'stop': stop_price, 'exposure_cap': max_exposure_usdt,
        'daily_loss_budget': daily_loss_budget_usdt}.items()}
    if any(value is not None and value <= 0 for value in optional.values()):
        raise ControlError('provided risk choices must be positive')
    with localcontext() as context:
        context.prec = 96
        for name in ('target', 'stop'):
            price = optional[name]
            if price is not None and (price % values['price_tick']
                    or (name == 'target' and price <= values['bid'])
                    or (name == 'stop' and price >= values['bid'])):
                raise ControlError('target must exceed entry and stop must be below entry on price ticks')

    with localcontext() as context:
        context.prec = 96
        budget, entry, step, tick = (values[k] for k in ('budget', 'bid', 'quantity_step', 'price_tick'))
        buy_fee, sell_fee = values['entry_bps'] / 10000, values['exit_bps'] / 10000
        def floor_step(value):
            return (value / step).to_integral_value(rounding=ROUND_DOWN) * step
        def ceil_tick(value):
            return (value / tick).to_integral_value(rounding=ROUND_CEILING) * tick
        # One conservative entry quantity fits the all-in budget even when fees
        # are deducted in quote. Never round up above funds to meet a minimum.
        quantity = number(text_decimal(floor_step(budget / (entry * (1 + buy_fee)))))
        notional = quantity * entry
        if quantity <= 0 or notional * values['usd_index'] < values['minimum_usd']:
            raise ControlError('budget cannot fund the tick-rounded minimum plus entry fee')
        blockers = ['ACCOUNT_EXPOSURE_UNVERIFIED', 'TRIAL_OPENING_STATE_UNVERIFIED', 'DAILY_LOSS_STATE_UNVERIFIED',
                    'NATIVE_PROTECTION_UNVERIFIED', 'FEE_CURRENCY_UNVERIFIED',
                    'MARKET_AND_RULE_PROVENANCE_UNVERIFIED']
        for name, value in optional.items():
            if value is None:
                blockers.append('MISSING_' + name.upper())
        maximum_debit = notional * (1 + buy_fee)
        if optional['exposure_cap'] is not None and maximum_debit > optional['exposure_cap']:
            blockers.append('PROPOSED_EXPOSURE_CAP_EXCEEDED')
        scenarios = []
        stop_equity_losses, stop_cash_shortfalls = [], []
        for buy_asset in ('USDT', 'CRO'):
            acquired = quantity * (1 - buy_fee) if buy_asset == 'CRO' else quantity
            entry_cash = notional if buy_asset == 'CRO' else maximum_debit
            for sell_asset in ('USDT', 'CRO'):
                sell_quantity = floor_step(acquired / (1 + sell_fee) if sell_asset == 'CRO' else acquired)
                residual = acquired - sell_quantity * (1 + sell_fee if sell_asset == 'CRO' else 1)
                factor = 1 - sell_fee if sell_asset == 'USDT' else 1
                cash_break_even = ceil_tick(entry_cash / (sell_quantity * factor)) if sell_quantity else None
                levels = []
                for name, price in (('flat', entry), ('target', optional['target']), ('stop', optional['stop'])):
                    if price is None:
                        continue
                    gross = sell_quantity * price
                    cash = gross * factor
                    dust_value = residual * price
                    if name == 'stop':
                        stop_cash_shortfalls.append(max(entry_cash - cash, 0))
                        stop_equity_losses.append(max(entry_cash - cash - dust_value, 0))
                    levels.append({'assumed_execution': name, 'price': text_decimal(price),
                        'gross_sell_notional_usdt': text_decimal(gross),
                        'cash_received_usdt': text_decimal(cash),
                        'cash_pnl_excluding_residual_value_usdt': text_decimal(cash - entry_cash),
                        'residual_mark_value_usdt': text_decimal(dust_value),
                        'equity_pnl_including_unsold_residual_usdt': text_decimal(cash + dust_value - entry_cash),
                        'meets_minimum_at_assumed_execution_price': sell_quantity > 0 and gross * values['usd_index'] >= values['minimum_usd']})
                scenarios.append({'entry_fee_asset': buy_asset, 'exit_fee_asset': sell_asset,
                    'entry_cash_debit_usdt': text_decimal(entry_cash),
                    'base_received_cro': text_decimal(acquired), 'sell_quantity_cro': text_decimal(sell_quantity),
                    'residual_cro_after_assumed_exit': text_decimal(residual),
                    'cash_break_even_price_excluding_residual': text_decimal(cash_break_even) if cash_break_even else None,
                    'levels': levels})
        if any(not level['meets_minimum_at_assumed_execution_price'] for case in scenarios for level in case['levels']):
            blockers.append('SOME_EXIT_SCENARIOS_BELOW_MINIMUM')
        if optional['target'] is not None and any(
                number(level['cash_received_usdt']) <= number(case['entry_cash_debit_usdt'])
                for case in scenarios for level in case['levels'] if level['assumed_execution'] == 'target'):
            blockers.append('TARGET_CASH_PROFIT_NOT_POSITIVE_IN_SOME_FEE_SCENARIOS')
        if (optional['daily_loss_budget'] is not None and stop_equity_losses
                and max(stop_equity_losses) > optional['daily_loss_budget']):
            blockers.append('ONE_STOP_SCENARIO_EXCEEDS_DAILY_LOSS_BUDGET')
        return {'scope': 'ARITHMETIC_PREVIEW_NOT_ACCOUNT_OR_ORDER', 'symbol': 'CRO/USDT',
            'live_dispatch_enabled': False, 'ready_for_live': False, 'orders_sent': 0,
            'supplied_facts_independently_verified': False, 'protection_verified': False,
            'entry_mode_assumption': 'POST_ONLY_LIMIT_AT_SUPPLIED_BID_NO_FILL_GUARANTEE',
            'risk_choices': {key: text_decimal(value) if value is not None else None for key, value in optional.items()},
            'risk_budget_evaluation': {
                'maximum_stop_equity_loss_under_supplied_assumptions_usdt': text_decimal(max(stop_equity_losses)) if stop_equity_losses else None,
                'maximum_stop_cash_shortfall_under_supplied_assumptions_usdt': text_decimal(max(stop_cash_shortfalls)) if stop_cash_shortfalls else None,
                'current_day_losses_and_remaining_budget_verified': False,
                'daily_cutoff_enforced': False},
            'fee_assumptions': {'entry_bps': text_decimal(values['entry_bps']), 'exit_bps': text_decimal(values['exit_bps']),
                'credits_rebates_or_third_fee_currency_supported': False},
            'entry': {'budget_all_in_usdt': text_decimal(budget), 'limit_price': text_decimal(entry),
                'quantity_cro': text_decimal(quantity), 'gross_notional_usdt': text_decimal(notional),
                'maximum_quote_debit_usdt': text_decimal(maximum_debit),
                'remaining_budget_usdt': text_decimal(budget - maximum_debit)},
            'fee_currency_scenarios': scenarios, 'blocking_checks': sorted(blockers),
            'assumed_exit_prices_are_not_guaranteed_fills_or_maximum_losses': True,
            'loss_or_profit_forecast': False}
