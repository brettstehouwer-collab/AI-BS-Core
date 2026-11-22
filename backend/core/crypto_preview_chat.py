"""Explicit current-turn public-market preview; no model, account or trade I/O."""
import asyncio
import json
import re

TOOL_NAME = 'preview_crypto_spot'
FIELDS = ('budget_usdt', 'stop_percent', 'target_percent', 'max_exposure_usdt',
          'daily_loss_budget_usdt', 'entry_fee_bps', 'exit_fee_bps',
          'stop_type', 'trigger_reference_type', 'stop_limit_price')


def crypto_preview_declarations():
    return [{'name': TOOL_NAME,
             'description': 'Read-only CRO/USDT arithmetic from public quotes and scenario fee/risk assumptions. Never accesses an account or sends orders.',
             'parameters': {'type': 'object', 'properties': {name: {'type': 'string', 'maxLength': 100} for name in FIELDS},
                            'required': [], 'additionalProperties': False}}]


def _arguments(text):
    tail = text.strip()[len('/crypto-preview'):].strip()
    if not tail:
        return {}
    if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', tail):
        return {'budget_usdt': tail}
    if len(tail) > 4096:
        raise ValueError('Bounded preview arguments required')
    from core.crypto_com_acknowledgements import _json
    args = _json(tail.encode('utf-8'))
    if (type(args) is not dict or not set(args).issubset(FIELDS)
            or any(type(value) is not str or len(value) > 100 for value in args.values())):
        raise ValueError('Explicit decimal preview fields required')
    return args


def _format(result):
    if result.get('status') != 'preview':
        return 'Crypto preview unavailable or authorization refused. No account was accessed and no orders were sent.'
    preview, market = result['preview'], result['market']
    entry, risk = preview['entry'], preview['risk_choices']
    lines = ['**CRO/USDT arithmetic preview — no order sent**',
        f"Public quote observed: {market['observed_at_utc']}",
        f"Bid / ask: {market['bid']} / {market['ask']} USDT",
        f"All-in budget: {entry['budget_all_in_usdt']} USDT; draft post-only quantity: {entry['quantity_cro']} CRO at {entry['limit_price']}.",
        f"Maximum modeled quote debit: {entry['maximum_quote_debit_usdt']} USDT.",
        f"Draft stop scenario: {risk['stop']}; target: {risk['target'] or 'unset'} USDT.",
        f"Daily loss-budget choice: {risk['daily_loss_budget']} USDT (not enforced).",
        f"Scenario fees: {preview['fee_assumptions']['entry_bps']} bps entry / {preview['fee_assumptions']['exit_bps']} bps exit.",
        f"Stop-scenario equity loss estimate: {preview['risk_budget_evaluation']['maximum_stop_equity_loss_under_supplied_assumptions_usdt']} USDT; cash shortfall excluding unsold residual: {preview['risk_budget_evaluation']['maximum_stop_cash_shortfall_under_supplied_assumptions_usdt']} USDT.",
        'Fee rates are scenario inputs, not authenticated account rates. USDT/USD index is assumed1.',
        '', '| Fee assets (buy / sell) | Sellable CRO | Residual CRO | Cash break-even price |',
        '|---|---:|---:|---:|']
    for case in preview['fee_currency_scenarios']:
        lines.append(f"| {case['entry_fee_asset']} / {case['exit_fee_asset']} | {case['sell_quantity_cro']} | {case['residual_cro_after_assumed_exit']} | {case['cash_break_even_price_excluding_residual'] or 'unavailable'} |")
    protection = result.get('protection_review')
    if isinstance(protection, dict):
        selection = ('Stop type and trigger reference remain unselected.'
            if protection['selected_stop_type'] is None and protection['trigger_reference_type'] is None
            else f"Draft stop type: {protection['selected_stop_type'] or 'unselected'}; trigger reference: {protection['trigger_reference_type'] or 'unselected'}.")
        lines += ['', '**Protection review — draft, not armed**', selection,
            'STOP_LOSS triggers a market order with execution-price risk; STOP_LIMIT requires a separate limit price and may remain unfilled.',
            f"Conservative static quantity across modeled fee cases: {protection['static_quantity_candidate_cro']} CRO. This can leave unprotected residual; size must follow actual fills and fees.",
            'Partial entry fills can fall below the exit minimum. Separate entry/stop submission leaves an unprotected interval; native acceptance and partial-fill coverage remain unverified.',
            'Checks concern current balances, open orders, positions/liabilities and activity after an explicit trial start. Historical profit review is not required.',
            f"Daily loss-budget choice: {protection['daily_loss_budget_usdt']} USDT; cutoff is not enforced."]
        if protection['selected_stop_type'] == 'STOP_LIMIT':
            option = next(row for row in protection['stop_options'] if row['type'] == 'STOP_LIMIT')
            eligible = sum(row.get('stop_limit_minimum_at_assumed_price') is True for row in protection['fee_currency_cases'])
            lines.append(f"Draft limit price: {option['limit_price'] or 'unset'}. Limit-price minimum met in {eligible}/4 modeled fee cases; trigger-price eligibility does not prove limit-price eligibility.")
    lines += ['', 'Residual assets are not spendable cash. Stop prices do not guarantee fills or maximum loss.',
              'Unverified: current trial opening state, account exposure, actual fee currency, current rule/index provenance and native protection. Live readiness is false.']
    return '\n'.join(lines)


async def crypto_preview_reply(body):
    raw = body.get('user_prompt')
    raw = raw if isinstance(raw, str) else body.get('prompt')
    if not isinstance(raw, str) or not re.match(r'^\s*/crypto-preview(?:\s|$)', raw, re.IGNORECASE):
        return None
    try:
        args = _arguments(raw)
    except (ValueError, UnicodeError):
        response = 'Use `/crypto-preview 2` or `/crypto-preview {"budget_usdt":"2","target_percent":"3"}`. Preview only; no account access or orders.'
    else:
        from tools.tool_registry import ToolRegistry
        result = await asyncio.to_thread(ToolRegistry.execute_tool, TOOL_NAME, args)
        response = _format(result)
    return {'response': response, 'provider': 'local', 'model': 'crypto-arithmetic-preview',
            'device': 'Local calculation with public market data'}
