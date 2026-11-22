"""Crypto.com Exchange v1 spot preparation/replay over the OFFLINE_ONLY store.

No HTTP, signing, keys, worker registration or live enable. Caller retains original
response bytes; normalized facts do not establish authentication or history coverage.
Contract: current get-trades fees/fee_instrument_name/fee_credits fields, not legacy
fee/fee_currency. See the official v1 get-trades and asynchronous trading workflow.
"""
import json
import re
from decimal import localcontext
from uuid import UUID

from .crypto_execution_controls import (
    ControlError, Fill, OfflineExecutionCoordinator, encode, fee_number,
    identifier, number, stamp, text_decimal,
)

CONTRACT = 'CRYPTOCOM_EXCHANGE_V1_SPOT_REPLAY_1'


def _client_id(value):
    if not isinstance(value, str):
        raise ControlError('explicit UUID client_oid required')
    try:
        parsed = UUID(value)
    except ValueError:
        raise ControlError('explicit UUID client_oid required') from None
    if str(parsed) != value:
        raise ControlError('canonical UUID client_oid required')
    return value


def _exchange_id(value):
    # JSON int64 may arrive as exact Python int or a lossless decimal string.
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', value):
        raise ControlError('positive lossless exchange identifier required')
    if int(value) > 9223372036854775807:
        raise ControlError('exchange identifier exceeds int64')
    return value


def _instrument(symbol):
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{1,20}/[A-Z0-9]{1,20}', symbol):
        raise ControlError('explicit spot BASE/QUOTE symbol required')
    return symbol.replace('/', '_')


def _result(response, method, request_id):
    if (type(request_id) is not int or request_id < 0 or request_id > 9223372036854775807
            or not isinstance(response, dict) or type(response.get('id')) is not int
            or response['id'] != request_id or response.get('method') != method
            or type(response.get('code')) is not int or response['code'] != 0
            or not isinstance(response.get('result'), dict)):
        raise ControlError('matching successful Exchange v1 response required')
    return response['result']


class CryptoComOfflineAdapter:
    """Opt-in preparation only; all mutations remain inside the existing temp store."""
    def __init__(self, coordinator, *, exchange_account_id):
        if not isinstance(coordinator, OfflineExecutionCoordinator):
            raise ControlError('existing offline coordinator required')
        self.account_id = identifier(exchange_account_id)
        if coordinator.account != 'cryptocom-exchange:' + self.account_id:
            raise ControlError('exchange account does not match offline store')
        self.coordinator = coordinator

    def _order(self, client_id):
        client_id = _client_id(client_id)
        snapshot = self.coordinator.snapshot()
        order = next((row for row in snapshot['orders'] if row['client_id'] == client_id), None)
        if order is None:
            raise ControlError('prepared immutable intent required')
        return order, json.loads(order['request']), snapshot

    def stage_limit(self, client_id, *, now_ms):
        order, intent, _ = self._order(client_id)
        params = {'instrument_name': _instrument(intent['symbol']),
                  'side': intent['side'].upper(), 'type': 'LIMIT',
                  'quantity': text_decimal(number(intent['quantity'])),
                  'price': text_decimal(number(intent['limit_price'])),
                  'client_oid': client_id, 'time_in_force': 'GOOD_TILL_CANCEL'}
        # Durable SUBMITTING before any future transport; no transport exists here.
        self.coordinator.begin_submission(client_id, now_ms=now_ms)
        return {'contract': CONTRACT, 'method': 'private/create-order', 'params': params,
                'account_id': self.account_id, 'live_dispatch_enabled': False}

    def inspect_acknowledgement(self, client_id, response, *, request_id):
        order, _, _ = self._order(client_id)
        if order['state'] not in ('SUBMITTING', 'UNKNOWN', 'OPEN', 'PARTIAL'):
            raise ControlError('submitted intent required for acknowledgement')
        result = _result(response, 'private/create-order', request_id)
        if result.get('client_oid') != client_id:
            raise ControlError('acknowledgement client identity mismatch')
        exchange_id = _exchange_id(result.get('order_id'))
        if order['exchange_id'] and order['exchange_id'] != exchange_id:
            raise ControlError('acknowledgement exchange identity mismatch')
        # Receipt is returned for caller preservation; never infer OPEN or a fill.
        return {'client_id': client_id, 'exchange_order_id': exchange_id,
                'matching_engine_acceptance_verified': False,
                'recovery_action': 'LOOKUP_ONLY_NEVER_RESEND', 'contract': CONTRACT}

    def replay_order_detail(self, client_id, response, *, request_id):
        order, intent, _ = self._order(client_id)
        detail = _result(response, 'private/get-order-detail', request_id)
        if (detail.get('account_id') != self.account_id or detail.get('client_oid') != client_id
                or detail.get('instrument_name') != _instrument(intent['symbol'])
                or detail.get('side') != intent['side'].upper()
                or detail.get('order_type') != 'LIMIT'
                or number(detail.get('quantity')) != number(intent['quantity'])
                or number(detail.get('limit_price')) != number(intent['limit_price'])):
            raise ControlError('order detail does not match immutable account/intent')
        exchange_id = _exchange_id(detail.get('order_id'))
        quantity = number(detail.get('cumulative_quantity'))
        cost = number(detail.get('cumulative_value'))
        if cost != number(order['filled_cost']):
            raise ControlError('order value differs from recorded fills; reservation retained')
        status = detail.get('status')
        if status in ('PENDING', 'NEW'):
            if quantity != 0 or order['state'] not in ('SUBMITTING', 'UNKNOWN'):
                raise ControlError('pending order status conflicts with recorded progress')
            return {'state': 'PENDING_ACCEPTANCE', 'recovery_action': 'LOOKUP_ONLY_NEVER_RESEND'}
        states = {'ACTIVE': 'OPEN' if quantity == 0 else 'PARTIAL',
                  'FILLED': 'FILLED', 'CANCELED': 'CANCELLED', 'REJECTED': 'REJECTED'}
        if status not in states:
            raise ControlError('unsupported order lifecycle status; reservation retained')
        # Offline source facts only; actual private-response authority is not supplied here.
        self.coordinator.reconcile(client_id, exchange_order_id=exchange_id,
                                   state=states[status], cumulative_quantity=text_decimal(quantity),
                                   authoritative=True)
        return {'state': states[status], 'exchange_order_id': exchange_id, 'contract': CONTRACT}

    def replay_trade(self, client_id, trade):
        order, intent, snapshot = self._order(client_id)
        if not isinstance(trade, dict):
            raise ControlError('trade object required')
        if (trade.get('account_id') != self.account_id
                or trade.get('client_oid') != client_id
                or trade.get('instrument_name') != _instrument(intent['symbol'])
                or trade.get('side') != intent['side'].upper()
                or trade.get('journal_type') != 'TRADING'
                or trade.get('isolation_id') or trade.get('isolation_type')):
            raise ControlError('trade account/intent/spot identity mismatch')
        exchange_id, fill_id = _exchange_id(trade.get('order_id')), _exchange_id(trade.get('trade_id'))
        if order['exchange_id'] and exchange_id != order['exchange_id']:
            raise ControlError('trade exchange order mismatch')
        occurred = trade.get('create_time')
        stamp(occurred)
        if 'create_time_ns' in trade:
            ns = trade['create_time_ns']
            if type(ns) is not int or ns < 0 or ns // 1000000 != occurred:
                raise ControlError('trade timestamp units conflict')
        quantity, price = number(trade.get('traded_quantity')), number(trade.get('traded_price'))
        if quantity <= 0 or price <= 0:
            raise ControlError('positive executed quantity and price required')
        # Signed balance delta: negative fees mean deductions; positive is a rebate.
        # Rebates/credits/third currencies are retained pending by the coordinator.
        fee_currency = identifier(trade.get('fee_instrument_name'))
        with localcontext() as context:
            context.prec = 96
            fee = fee_number(trade.get('fees')).copy_negate()
            complete = 'fee_credits' in trade and fee_number(trade['fee_credits']) == 0
        key = encode([intent['symbol'], fill_id])
        previous = next((row for row in snapshot['fills'] if row['fill_id'] == key), None)
        sequence = json.loads(previous['payload'])['sequence'] if previous else snapshot['risk']['last_sequence'] + 1
        with localcontext() as context:
            context.prec = 96
            cost = text_decimal(number(text_decimal(quantity * price)))
        fill = Fill(fill_id=fill_id, client_id=client_id, exchange_order_id=exchange_id,
                    symbol=intent['symbol'], side=intent['side'], quantity=text_decimal(quantity),
                    cost=cost, fees=((fee_currency, text_decimal(fee)),),
                    sequence=sequence, occurred_ms=occurred, fees_complete=complete)
        return self.coordinator.apply_fill(fill)
