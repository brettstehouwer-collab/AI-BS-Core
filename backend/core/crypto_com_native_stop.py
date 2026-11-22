"""Pure unsigned STOP_LOSS/LAST_PRICE SELL draft, never Exchange acceptance.

Contract: official REST private/advanced/create-order, reviewed 2026-11-15.
Caller facts and receipt hashes do not authenticate their provenance. This module
has no transport, credentials, persistence, or dispatch authority. Trigger-price
minimum arithmetic cannot guarantee execution notional, fills, or maximum loss.
"""
from decimal import localcontext
import re
from uuid import UUID

from .crypto_execution_controls import ControlError, digest, identifier, number, text_decimal


DOC_URL = 'https://exchange-developer.crypto.com/exchange/v1/docs/api/rest/private-advanced-create-order'


def build_native_stop_draft(*, account, instrument_name, client_oid, net_inventory,
        available_base, quantity, quantity_tick, price_tick, minimum_quantity,
        minimum_notional_quote, trigger_price, last_price, fee_asset, fee_reserve,
        available_fee, actual_fill_fees_complete, reconciliation_complete,
        unresolved_orders, provenance_sha256):
    """Validate explicit supplied reconciled facts; refuse missing or unsafe facts.

Net inventory must already subtract actual entry base fees. Reserve is an explicit
exit-fee amount in fee_asset, not a guessed rate. Only base/quote fees supported.
For base fees available_fee must describe the same available_base balance.
No rounding or minimum upsize occurs. Partial entry fills require a fresh draft.
"""
    facts = dict(locals())
    identifier(account)
    if (type(instrument_name) is not str
            or not re.fullmatch(r'[A-Z0-9]{1,20}_[A-Z0-9]{1,20}', instrument_name)):
        raise ControlError('explicit spot BASE_QUOTE instrument required')
    base, quote = instrument_name.split('_')
    if base == quote or fee_asset not in (base, quote):
        raise ControlError('distinct spot assets and explicit supported fee asset required')
    if (actual_fill_fees_complete is not True or reconciliation_complete is not True
            or unresolved_orders is not False):
        raise ControlError('complete reconciled actual fills/fees and no unresolved orders required')
    if type(provenance_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', provenance_sha256):
        raise ControlError('explicit lowercase reconciliation receipt SHA-256 required')
    try:
        if type(client_oid) is not str or str(UUID(client_oid)) != client_oid:
            raise ValueError('noncanonical client UUID')
    except (ValueError, AttributeError) as exc:
        raise ControlError('canonical client UUID required') from exc
    inventory, available, qty, qtick, ptick, minqty, minnotional, trigger, last, reserve, fee_cash = (
        number(value) for value in (net_inventory, available_base, quantity, quantity_tick,
            price_tick, minimum_quantity, minimum_notional_quote, trigger_price,
            last_price, fee_reserve, available_fee))
    for key, value in zip(('net_inventory','available_base','quantity','quantity_tick',
            'price_tick','minimum_quantity','minimum_notional_quote','trigger_price',
            'last_price','fee_reserve','available_fee'),
            (inventory,available,qty,qtick,ptick,minqty,minnotional,trigger,last,reserve,fee_cash)):
        facts[key] = text_decimal(value)
    with localcontext() as context:
        context.prec = 96
        if min(inventory, available, qty, qtick, ptick, minqty, minnotional, trigger, last) <= 0:
            raise ControlError('positive inventory, order, ticks, minimums and reference required')
        if qty % qtick or trigger % ptick or trigger >= last:
            raise ControlError('tick-aligned quantity/trigger below current LAST_PRICE required')
        if qty < minqty or qty * trigger < minnotional:
            raise ControlError('draft below supplied minimum at trigger; never upsize')
        if qty > min(inventory, available) or reserve > fee_cash:
            raise ControlError('insufficient reconciled net inventory or available fee balance')
        if fee_asset == base and (fee_cash != available or qty + reserve > min(inventory, available)):
            raise ControlError('base exit fee must fit same reconciled available inventory')
        residual = inventory - qty
    params = dict(instrument_name=instrument_name, side='SELL', type='STOP_LOSS',
        quantity=text_decimal(qty), client_oid=client_oid, ref_price=text_decimal(trigger),
        ref_price_type='LAST_PRICE', fee_instrument_name=fee_asset)
    return dict(scope='UNSIGNED_LOCALLY_VALIDATED_NATIVE_STOP_DRAFT',
        draft={'method':'private/advanced/create-order','params':params},
        facts_sha256=digest(facts), provenance_sha256=provenance_sha256,
        provenance_authenticated=False, docs_url=DOC_URL,
        unsold_inventory=text_decimal(residual), exit_fee_reserved=text_decimal(reserve),
        minimum_checked_at_trigger_only=True, full_position_protection_verified=False,
        partial_fill_protection_verified=False, daily_cutoff_enforced=False,
        guaranteed_maximum_loss=False, native_order_accepted=False,
        live_dispatch_enabled=False, ready_for_live=False, orders_sent=0)
