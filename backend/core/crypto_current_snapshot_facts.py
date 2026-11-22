"""Pure PRIVATE observations from six result objects; never funds/admission.

Official schemas: exchange-developer.crypto.com/exchange/v1/docs/api/rest-single-page/
Balance quantities/reservations are observations, not an allocated trial opening.
"""
from decimal import Decimal, InvalidOperation, localcontext
import re

_LABELS={'before','ordinary','advanced','positions','fees','after'}


def _decimal(value,*,signed=False,maximum=Decimal('1e22')):
    if type(value) not in (str,int,Decimal) or type(value) is str and (not value or len(value)>128 or value.strip()!=value):
        raise ValueError('Bounded decimal observation required')
    try:
        result=Decimal(value)
        if (not result.is_finite() or result.copy_abs()>maximum or not signed and result<0
                or len(result.as_tuple().digits)>36 or not -18<=result.as_tuple().exponent<=22):
            raise ValueError('Decimal observation outside parser bounds')
        return result
    except (InvalidOperation,TypeError,OverflowError):
        raise ValueError('Invalid decimal observation') from None


def _text(value):
    if value==0:return '0'
    return format(value,'f').rstrip('0').rstrip('.') if '.' in format(value,'f') else format(value,'f')


def _array(result):
    if type(result) is not dict or type(result.get('data')) is not list or len(result['data'])>10000:
        raise ValueError('Bounded documented result.data array required')
    if any(type(row) is not dict for row in result['data']):raise ValueError('Object observations required')
    return result['data']


def _balances(result):
    rows=_array(result);assets={};risk=[]
    for row in rows:
        values=row.get('position_balances')
        if type(values) is not list or len(values)>10000:raise ValueError('Position balances required')
        for item in values:
            if type(item) is not dict:raise ValueError('Asset observation required')
            asset=item.get('instrument_name')
            if type(asset) is not str or not re.fullmatch(r'[A-Z0-9][A-Z0-9_.-]{0,63}',asset) or asset in assets:
                raise ValueError('Unique bounded asset identity required')
            quantity,reserved=_decimal(item.get('quantity')),_decimal(item.get('reserved_qty'))
            if reserved>quantity:raise ValueError('Reserved quantity exceeds observed quantity')
            with localcontext() as ctx:
                ctx.prec=96;free=quantity-reserved
            assets[asset]={'quantity':_text(quantity),'reserved_qty':_text(reserved),'free_quantity':_text(free)}
        known=type(row.get('has_risk')) is bool and type(row.get('is_liquidating')) is bool
        try:borrow=_decimal(row.get('total_borrow'))
        except ValueError:known=False;borrow=None
        isolated=row.get('isolated_positions')
        if type(isolated) is not list:known=False
        observed_risk=(row.get('has_risk') is True or row.get('is_liquidating') is True
            or borrow is not None and borrow>0 or type(isolated) is list and bool(isolated))
        risk.append('RISK_OBSERVED' if observed_risk else 'CLEAR_OBSERVED' if known else 'UNKNOWN')
    return assets,risk


def project_current_snapshot(results):
    """Return private facts only; callers must not expose observed balances publicly."""
    if type(results) is not dict or results.keys()!=_LABELS:raise ValueError('Exact six result labels required')
    before,before_risk=_balances(results['before']);after,after_risk=_balances(results['after'])
    counts={label:len(_array(results[label])) for label in ('ordinary','advanced','positions')}
    fees=results['fees']
    if type(fees) is not dict or fees.get('instrument_name')!='CRO_USDT':raise ValueError('CRO_USDT fee observation required')
    maker=_decimal(fees.get('effective_maker_rate_bps'),signed=True,maximum=Decimal('10000'))
    taker=_decimal(fees.get('effective_taker_rate_bps'),signed=True,maximum=Decimal('10000'))
    risks=before_risk+after_risk
    liability=('RISK_OBSERVED' if 'RISK_OBSERVED' in risks else 'UNKNOWN' if not risks or 'UNKNOWN' in risks else 'CLEAR_OBSERVED')
    return dict(scope='CURRENT_CREDENTIAL_SNAPSHOT_PRIVATE_FACTS',balances_before=before,balances_after=after,
        balance_bracket_unchanged=before==after,observed_free_quote_usdt=after.get('USDT',{}).get('free_quantity'),
        trial_capital_usdt=None,preexisting_cro_quantity=after.get('CRO',{}).get('quantity'),
        preexisting_cro_basis_known=False,preexisting_cro_basis_usdt=None,realized_profit_usdt=None,
        liabilities_status=liability,liabilities_complete=False,observed_counts=counts,
        empty_observed={key:value==0 for key,value in counts.items()},all_order_families_complete=False,
        atomic_snapshot=False,effective_maker_rate_bps=_text(maker),effective_taker_rate_bps=_text(taker),
        fee_rates_scope='OBSERVED_CRO_USDT_RATES_ONLY',actual_fee_currency=None,exchange_account_id=None,
        account_identity_verified=False,admission_allowed=False,native_protection_qualified=False,
        live_dispatch_enabled=False,ready_for_live=False,orders_sent=0)
