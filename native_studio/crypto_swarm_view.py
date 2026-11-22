"""Read-only crypto observations; this client never changes order dispatch guards."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING
import urllib.request
from urllib.parse import urlsplit

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                            QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from native_studio.theme import PALETTE
if TYPE_CHECKING:
    from native_studio.engine import EngineBus

DB_PATH = Path(r'C:\AI-BS\backend\aibs_master.db')
DRIP_PATH = Path(r'C:\AI-BS\backend\drip_ledger.db')
QUOTE_URL = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,kaspa,clore-ai&vs_currencies=usd'
MAX_RESPONSE_BYTES = 64 * 1024
MAX_ROWS = 100


def _decimal(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('A finite recorded number is required.')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('A finite recorded number is required.') from None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise ValueError('A finite nonnegative recorded number is required.')
    if len(number.as_tuple().digits) > 72 or number.adjusted() > 30 or number.as_tuple().exponent < -40:
        raise ValueError('The recorded number exceeds the display precision limit.')
    return number


def _plain(value):
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def read_recorded_trades(paths=None, *, limit=MAX_ROWS):
    """Read existing ledger rows, never treating their presence as fill/on-chain proof."""
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise ValueError('A bounded ledger page is required.')
    candidates = tuple(paths) if paths is not None else (DB_PATH, DRIP_PATH)
    for candidate in candidates:
        path = Path(candidate).absolute()
        if not path.is_file() or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
            continue
        try:
            # mode=ro refuses to create a missing database and observes SQLite WAL.
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.5)) as db:
                db.execute('PRAGMA query_only=ON')
                db.execute('PRAGMA trusted_schema=OFF')
                columns = {row[1] for row in db.execute('PRAGMA table_info(trades)')}
                needed = {'id', 'timestamp', 'type', 'coin_amount', 'coin_price', 'usd_value'}
                if not needed.issubset(columns):
                    continue
                raw_rows = db.execute('SELECT id,timestamp,type,coin_amount,coin_price,usd_value '
                                      'FROM trades ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
            rows = []
            for item in raw_rows:
                rows.append({'id': str(item[0]), 'ts': str(item[1]) if item[1] is not None else 'Not recorded',
                             'type': str(item[2]).upper() if item[2] else 'UNSPECIFIED',
                             'amount': _decimal(item[3]), 'price': _decimal(item[4]), 'usd': _decimal(item[5])})
            with localcontext() as context:
                context.prec = 80
                total = sum((row['usd'] for row in rows), Decimal(0))
            return {'status': 'available', 'source': path.name, 'rows': rows,
                    'displayed_usd': total, 'execution_verified': False,
                    'scope': f'Latest {limit} recorded rows; not a 24-hour total or execution proof.'}
        except (OSError, sqlite3.Error, ValueError, InvalidOperation):
            # A present but invalid ledger must not be silently replaced by zeros.
            return {'status': 'unavailable', 'reason': 'Ledger records could not be verified for display.'}
    return {'status': 'unavailable', 'reason': 'An existing supported ledger was not observed.'}


def fetch_public_quotes():
    """One bounded public GET; no exchange credentials, order requests or retries."""
    try:
        request = urllib.request.Request(QUOTE_URL, headers={'User-Agent': 'AI-BS/Native'})
        with urllib.request.urlopen(request, timeout=6) as response:
            endpoint = urlsplit(response.geturl())
            if response.status != 200 or endpoint.scheme != 'https' or endpoint.hostname != 'api.coingecko.com':
                return None
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return None
        def reject_constant(_value):
            raise ValueError('Nonfinite JSON number')
        data = json.loads(raw.decode('utf-8'), parse_float=Decimal, parse_int=Decimal,
                          parse_constant=reject_constant)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


class CryptoSwarmNativeView(QWidget):
    """A ledger/quote monitor with live trading held, never a dispatch controller."""
    def __init__(self, bus: EngineBus, *, ledger_paths=None):
        super().__init__()
        self.bus = bus
        self._ledger_paths = tuple(ledger_paths) if ledger_paths is not None else None
        self._trades = []
        self._closed = False
        self._quotes_pending = self._ledger_pending = False
        self._init_ui()
        self._load_trades()
        self._fetch_market_prices()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._fetch_market_prices)
        self.timer.start(30000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        head = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel('Crypto Swarm • read-only observations')
        title.setStyleSheet('font-size:15pt;font-weight:bold;')
        heading.addWidget(title)
        subtitle = QLabel('Live order dispatch is held. Ledger rows do not establish execution or on-chain confirmation.')
        subtitle.setWordWrap(True)
        heading.addWidget(subtitle)
        head.addLayout(heading, 1)
        self.btn_pause = QPushButton('Live trading disabled')
        self.btn_pause.setEnabled(False)
        self.btn_pause.setToolTip('This monitor does not alter the backend dispatch hold or authorize orders.')
        self.btn_pause.clicked.connect(self._toggle_scalper)
        head.addWidget(self.btn_pause)
        self.btn_refresh = QPushButton('Refresh observations')
        self.btn_refresh.clicked.connect(self._refresh_observations)
        head.addWidget(self.btn_refresh)
        layout.addLayout(head)
        tickers = QHBoxLayout()
        for attr, name, color in [('card_btc','BITCOIN (BTC)','yellow'),('card_eth','ETHEREUM (ETH)','cyan'),
                                  ('card_sol','SOLANA (SOL)','purple'),('card_kas','KASPA (KAS)','green'),
                                  ('card_clore','CLORE.AI (CLORE)','red')]:
            card = self._create_card(name, 'Unavailable', PALETTE[color])
            setattr(self, attr, card)
            tickers.addWidget(card)
        layout.addLayout(tickers)
        self.quote_status = QLabel('Public quotes not yet observed.')
        self.quote_status.setWordWrap(True)
        layout.addWidget(self.quote_status)
        status = QHBoxLayout()
        self.card_scalper_state = self._create_card('CLIENT ORDER DISPATCH', 'HELD • read-only monitor', PALETTE['yellow'])
        self.card_trade_count = self._create_card('RECORDED ROWS DISPLAYED', 'Unavailable', PALETTE['cyan'])
        self.card_volume = self._create_card('DISPLAYED RECORDED USD', 'Unavailable', PALETTE['yellow'])
        for card in [self.card_scalper_state, self.card_trade_count, self.card_volume]:
            status.addWidget(card)
        layout.addLayout(status)
        self.ledger_status = QLabel('Ledger source not yet observed. Daemon readiness has not been tested.')
        self.ledger_status.setWordWrap(True)
        layout.addWidget(self.ledger_status)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['ID','Recorded time','Type','Coin amount','Recorded unit price','Recorded USD'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

    def _create_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f'QFrame{{background:#0c1220;border:1px solid {color};border-radius:6px;}}')
        box = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet('font-size:8pt;')
        value_label = QLabel(value)
        value_label.setObjectName('ValLabel')
        value_label.setStyleSheet(f'color:{color};font-size:11pt;font-weight:bold;')
        value_label.setWordWrap(True)
        box.addWidget(title_label)
        box.addWidget(value_label)
        return card

    def _update_card(self, card, value):
        label = card.findChild(QLabel, 'ValLabel')
        if label:
            label.setText(value)

    def _refresh_observations(self):
        self._load_trades()
        self._fetch_market_prices()

    def _fetch_market_prices(self):
        if self._closed or self._quotes_pending:
            return
        self._quotes_pending = True
        try:
            self.bus.dispatch(fetch_public_quotes, callback=self._apply_quotes,
                              on_error=lambda _message: self._apply_quotes(None))
        except Exception:
            self._apply_quotes(None)

    def _apply_quotes(self, data):
        if self._closed:
            return
        self._quotes_pending = False
        observed = 0
        for key, card in [('bitcoin',self.card_btc),('ethereum',self.card_eth),('solana',self.card_sol),
                          ('kaspa',self.card_kas),('clore-ai',self.card_clore)]:
            text = 'Unavailable'
            try:
                item = data.get(key) if isinstance(data, dict) else None
                value = item.get('usd') if isinstance(item, dict) else None
                if isinstance(value, str):
                    raise ValueError('A numeric provider quote is required.')
                number = _decimal(value, positive=True)
                text = f'${number:,.2f}' if number >= 1 else '$' + _plain(number)
                observed += 1
            except (ValueError, InvalidOperation, TypeError):
                pass
            self._update_card(card, text)
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        self.quote_status.setText(f'{observed}/5 public quotes observed at {stamp}; unavailable quotes are not estimated.'
                                  if observed else 'Public quotes unavailable; no live values are asserted.')

    def _load_trades(self):
        if self._closed or self._ledger_pending:
            return
        self._ledger_pending = True
        try:
            self.bus.dispatch(read_recorded_trades, self._ledger_paths, callback=self._apply_ledger,
                              on_error=lambda _message: self._apply_ledger(None))
        except Exception:
            self._apply_ledger(None)

    def _apply_ledger(self, data):
        if self._closed:
            return
        self._ledger_pending = False
        self._trades = []
        self.table.setRowCount(0)
        if not isinstance(data, dict) or data.get('status') != 'available':
            self._update_card(self.card_trade_count, 'Unavailable')
            self._update_card(self.card_volume, 'Unavailable')
            self.ledger_status.setText('Ledger observation unavailable; no execution count or balance is inferred.')
            return
        self._trades = data['rows']
        self._update_card(self.card_trade_count, str(len(self._trades)) + ' recorded rows')
        self._update_card(self.card_volume, f"${data['displayed_usd']:,.2f}" if self._trades else 'No rows')
        self.ledger_status.setText('Source: ' + data['source'] + '. ' + data['scope'] +
                                  ' Existing SQLite REAL values retain their stored precision.')
        self.table.setRowCount(len(self._trades))
        for index, item in enumerate(self._trades):
            values = [item['id'], item['ts'], item['type'], _plain(item['amount']),
                      '$' + _plain(item['price']), '$' + _plain(item['usd'])]
            for column, text in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(text))

    def _toggle_scalper(self):
        # Retain the legacy callback name without presenting an unauthorized resume.
        self.btn_pause.setEnabled(False)
        self._update_card(self.card_scalper_state, 'HELD • read-only monitor')

    def shutdown(self):
        self._closed = True
        if hasattr(self, 'timer'):
            self.timer.stop()
