"""Exchange-neutral execution controls, usable ONLY with explicit offline stores.

No default database, exchange adapter, network, daemon registration or live-enable
switch. Legacy dispatch remains unconditionally held in crypto_execution_safety.
Facts supplied here are test/replay facts, never exchange reconciliation proof.
Money is decimal TEXT; every account mutation uses BEGIN IMMEDIATE. An order
acknowledgement is not a fill, and elapsed time never releases a reservation.
"""
from contextlib import contextmanager, closing
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, localcontext, ROUND_DOWN, ROUND_CEILING
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ("INTENT", "SUBMITTING", "UNKNOWN", "OPEN", "PARTIAL")
TERMINAL = ("FILLED", "CANCELLED", "REJECTED")
ZERO = Decimal(0)
BPS = Decimal(10000)


class ControlError(ValueError):
    pass


class Held(ControlError):
    """A durable integrity/breaker latch was written before this exception."""


def number(value):
    """Bound provider/config inputs, rejecting binary floats and ambiguous values."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ControlError("decimal string or integer required")
    if len(str(value)) > 100:
        raise ControlError("numeric input too long")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ControlError("invalid decimal") from exc
    if (not result.is_finite() or result < 0 or result > Decimal("1e18")
            or result.as_tuple().exponent < -18 or len(result.as_tuple().digits) > 36):
        raise ControlError("decimal outside supported nonnegative precision")
    return result


def dec(value):
    return Decimal(value)


def fee_number(value):
    """Retain bounded negative rebate facts for explicit pending review."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)) or len(str(value)) > 100:
        raise ControlError("decimal fee required")
    try:
        value = Decimal(value)
    except InvalidOperation as exc:
        raise ControlError("invalid decimal fee") from exc
    magnitude = number(value.copy_abs())
    return -magnitude if value.is_signed() else magnitude


def text_decimal(value):
    # normalize() uses the caller's decimal context; format does not round.
    s = format(value, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", value):
        raise ControlError("invalid identifier")
    return value


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(encode(value).encode("utf-8")).hexdigest()


def stamp(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10**15:
        raise ControlError("invalid timestamp/sequence")
    return value


@dataclass(frozen=True)
class Instrument:
    base: str
    quote: str
    quantity_step: str = "0.00000001"
    price_tick: str = "0.00000001"
    minimum_quantity: str = "0.00000001"
    minimum_notional: str = "0.01"

    def normalized(self):
        result = {"base": identifier(self.base), "quote": identifier(self.quote)}
        if self.base == self.quote:
            raise ControlError("identical instrument currencies")
        for key in ("quantity_step", "price_tick", "minimum_quantity", "minimum_notional"):
            val = number(getattr(self, key))
            if val <= 0:
                raise ControlError("instrument bounds must be positive")
            result[key] = text_decimal(val)
        return result


@dataclass(frozen=True)
class RiskLimits:
    max_order_quote: str = "100"
    max_position_quote: str = "500"
    max_gross_quote: str = "1000"
    max_daily_quote: str = "2000"
    max_slippage_bps: str = "50"
    max_fee_bps: str = "100"
    max_drawdown_bps: str = "2000"
    max_open_orders: int = 8
    rejection_threshold: int = 3
    quote_max_age_ms: int = 5000

    def normalized(self):
        result = {}
        for key, value in asdict(self).items():
            if key in ("max_open_orders", "rejection_threshold", "quote_max_age_ms"):
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1000000:
                    raise ControlError("invalid integer limit")
                result[key] = value
            else:
                n = number(value)
                if n <= 0 or (key.endswith("bps") and n >= BPS):
                    raise ControlError("invalid risk limit")
                result[key] = text_decimal(n)
        return result


@dataclass(frozen=True)
class Fill:
    fill_id: str
    client_id: str
    exchange_order_id: str
    symbol: str
    side: str
    quantity: str
    cost: str
    # Every fee currency must be explicit. Empty tuple means confirmed zero fees.
    fees: tuple
    sequence: int
    occurred_ms: int
    fees_complete: bool = True


class OfflineExecutionCoordinator:
    """One offline account per store. Instances/workers share its durable limits."""

    def __init__(self, path):
        self.path = self._path(path, exists=True)
        with closing(self._connect()) as db:
            try:
                meta = dict(db.execute("SELECT key,value FROM metadata"))
                if meta.get("schema") != "1" or meta.get("scope") != "OFFLINE_ONLY":
                    raise ControlError("not an offline execution store")
                self.account = identifier(meta["account"])
                self.quote = identifier(meta["quote"])
                self.limits = MappingProxyType(json.loads(meta["limits"]))
                # Do not silently initialize a missing/damaged safety table.
                for table in ("risk", "orders", "fills", "unmatched_fills", "positions", "balances", "stops", "markets", "daily", "events"):
                    db.execute("SELECT * FROM " + table + " LIMIT 1").fetchone()
                if db.execute("SELECT COUNT(*) FROM risk WHERE id=1").fetchone()[0] != 1:
                    raise ControlError("missing circuit breaker")
                if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ControlError("execution store integrity failure")
            except (sqlite3.Error, KeyError, json.JSONDecodeError) as exc:
                raise ControlError("invalid execution store") from exc

    @staticmethod
    def _path(path, *, exists):
        p = Path(path).absolute()
        # Refuse canonical/live DBs, links and implicit creation when reopening.
        if any(part.is_symlink() for part in (p, *p.parents)):
            raise ControlError("linked stores are forbidden")
        resolved = p.resolve()
        temp = Path(tempfile.gettempdir()).resolve()
        if not resolved.is_relative_to(temp) or resolved.is_relative_to(ROOT):
            raise ControlError("explicit OS-temporary offline store required")
        if exists and (not p.is_file() or p.stat().st_nlink != 1):
            raise ControlError("missing or hard-linked offline store")
        if not exists and p.exists():
            raise ControlError("creation requires a new store")
        return resolved

    @classmethod
    def create(cls, path, *, account, quote, cash, limits=None):
        p = cls._path(path, exists=False)
        policy = (limits or RiskLimits()).normalized()
        account, quote, cash = identifier(account), identifier(quote), number(cash)
        if cash <= 0:
            raise ControlError("explicit positive offline seed cash required")
        # Exclusive creation avoids turning an existing database into a fixture.
        with p.open("xb"):
            pass
        with closing(sqlite3.connect(p, timeout=5, isolation_level=None)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE balances(asset TEXT PRIMARY KEY,total TEXT NOT NULL);
                CREATE TABLE risk(id INTEGER PRIMARY KEY CHECK(id=1),rejections INTEGER NOT NULL,
                    halted INTEGER NOT NULL,reason TEXT NOT NULL,peak_equity TEXT NOT NULL,last_sequence INTEGER NOT NULL,
                    submission_sequence INTEGER NOT NULL);
                CREATE TABLE markets(symbol TEXT PRIMARY KEY,instrument TEXT NOT NULL,bid TEXT NOT NULL,
                    ask TEXT NOT NULL,observed_ms INTEGER NOT NULL);
                CREATE TABLE positions(symbol TEXT PRIMARY KEY,quantity TEXT NOT NULL,basis TEXT NOT NULL,
                    realized TEXT NOT NULL);
                CREATE TABLE orders(client_id TEXT PRIMARY KEY,request TEXT NOT NULL,fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,exchange_id TEXT UNIQUE,filled_quantity TEXT NOT NULL,filled_cost TEXT NOT NULL,
                    reserve_asset TEXT NOT NULL,reserve_amount TEXT NOT NULL,risk_notional TEXT NOT NULL,
                    created_ms INTEGER NOT NULL,rejection_counted INTEGER NOT NULL DEFAULT 0,submission_sequence INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE fills(fill_id TEXT PRIMARY KEY,client_id TEXT NOT NULL REFERENCES orders(client_id),
                    payload TEXT NOT NULL,fingerprint TEXT NOT NULL,state TEXT NOT NULL,reason TEXT NOT NULL);
                CREATE TABLE unmatched_fills(fill_id TEXT PRIMARY KEY,payload TEXT NOT NULL,fingerprint TEXT NOT NULL);
                CREATE TABLE daily(day INTEGER PRIMARY KEY,turnover TEXT NOT NULL);
                CREATE TABLE stops(symbol TEXT PRIMARY KEY,hard_stop TEXT NOT NULL,trailing_bps TEXT NOT NULL,
                    high_water TEXT NOT NULL,effective_stop TEXT NOT NULL,triggered INTEGER NOT NULL,
                    exit_id TEXT,generation INTEGER NOT NULL,status TEXT NOT NULL);
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,payload TEXT NOT NULL);
                COMMIT;
            """)
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT INTO metadata VALUES(?,?)", [("schema", "1"), ("scope", "OFFLINE_ONLY"),
                ("account", account), ("quote", quote), ("limits", encode(policy))])
            db.execute("INSERT INTO balances VALUES(?,?)", (quote, text_decimal(cash)))
            db.execute("INSERT INTO risk VALUES(1,0,0,'',?,0,0)", (text_decimal(cash),))
            db.execute("COMMIT")
        return cls(p)

    def _connect(self):
        self._path(self.path, exists=True)
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @contextmanager
    def _tx(self):
        with localcontext() as context, closing(self._connect()) as db:
            context.prec = 96
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except Held:
                # Held is raised only after a safety latch, outside finance savepoints.
                db.execute("COMMIT")
                raise
            except BaseException:
                db.execute("ROLLBACK")
                raise
            else:
                db.execute("COMMIT")

    @staticmethod
    def _event(db, kind, data):
        db.execute("INSERT INTO events(kind,payload) VALUES(?,?)", (kind, encode(data)))

    def _hold(self, db, reason):
        db.execute("UPDATE risk SET halted=1,reason=? WHERE id=1", (reason,))
        self._event(db, "HELD", {"reason": reason})

    def halt(self):
        with self._tx() as db:
            self._hold(db, "OPERATOR_HALT")

    def _gate(self, db):
        risk = db.execute("SELECT * FROM risk WHERE id=1").fetchone()
        if risk is None or risk["halted"]:
            raise ControlError("account circuit breaker held")
        if db.execute("SELECT 1 FROM orders WHERE state IN ('SUBMITTING','UNKNOWN') LIMIT 1").fetchone():
            raise ControlError("unresolved submission requires lookup; never resend")

    def _order(self, db, client_id):
        row = db.execute("SELECT * FROM orders WHERE client_id=?", (identifier(client_id),)).fetchone()
        if row is None:
            raise ControlError("unknown client order")
        return row

    @staticmethod
    def _balance(db, asset):
        row = db.execute("SELECT total FROM balances WHERE asset=?", (asset,)).fetchone()
        return dec(row[0]) if row else ZERO

    def _set_balance(self, db, asset, value):
        if value < 0:
            raise ControlError("negative balance")
        db.execute("INSERT INTO balances VALUES(?,?) ON CONFLICT(asset) DO UPDATE SET total=excluded.total",
                   (asset, text_decimal(value)))

    def _reserved(self, db, asset, exclude=""):
        return sum((dec(row[0]) for row in db.execute(
            "SELECT reserve_amount FROM orders WHERE reserve_asset=? AND client_id<>?", (asset, exclude))), ZERO)

    def _fresh(self, row, now_ms):
        age = now_ms - row["observed_ms"]
        if not 0 <= age <= self.limits["quote_max_age_ms"]:
            raise ControlError("stale or future market quote")

    def quote_market(self, instrument, *, bid, ask, observed_ms, now_ms):
        spec = instrument.normalized()
        symbol = spec["base"] + "/" + spec["quote"]
        bid, ask = number(bid), number(ask)
        stamp(now_ms), stamp(observed_ms)
        if spec["quote"] != self.quote or not ZERO < bid <= ask:
            raise ControlError("unsupported quote currency or invalid market")
        self._fresh({"observed_ms": observed_ms}, now_ms)
        with self._tx() as db:
            old = db.execute("SELECT * FROM markets WHERE symbol=?", (symbol,)).fetchone()
            if old and old["instrument"] != encode(spec):
                raise ControlError("instrument metadata changed")
            if old and observed_ms <= old["observed_ms"]:
                if (observed_ms, text_decimal(bid), text_decimal(ask)) == (old["observed_ms"], old["bid"], old["ask"]):
                    return
                raise ControlError("out-of-order market quote")
            db.execute("INSERT INTO markets VALUES(?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
                "bid=excluded.bid,ask=excluded.ask,observed_ms=excluded.observed_ms",
                (symbol, encode(spec), text_decimal(bid), text_decimal(ask), observed_ms))
            # Every accepted quote must persist protection before a later quote
            # can replace its peak or hide a threshold crossing. No order I/O.
            self._observe_stop(db, symbol, bid)
            # Persist peaks independently of whether an order passes risk checks.
            # A multi-symbol account needs a fresh complete valuation first.
            try:
                equity, _, _ = self._equity_and_exposure(db, now_ms)
            except ControlError:
                return
            peak = dec(db.execute("SELECT peak_equity FROM risk WHERE id=1").fetchone()[0])
            if equity > peak:
                db.execute("UPDATE risk SET peak_equity=? WHERE id=1", (text_decimal(equity),))
            elif peak and (peak - equity) * BPS >= peak * dec(self.limits["max_drawdown_bps"]):
                self._hold(db, "DRAWDOWN_LIMIT")

    def _equity_and_exposure(self, db, now_ms):
        equity, gross, by_symbol = self._balance(db, self.quote), ZERO, {}
        for pos in db.execute("SELECT * FROM positions"):
            qty = dec(pos["quantity"])
            if qty == 0:
                continue
            market = db.execute("SELECT * FROM markets WHERE symbol=?", (pos["symbol"],)).fetchone()
            self._fresh(market, now_ms)
            mark = qty * dec(market["bid"])
            exposure = max(mark, dec(pos["basis"]))
            equity += mark
            gross += exposure
            by_symbol[pos["symbol"]] = exposure
        for order in db.execute("SELECT request,risk_notional FROM orders"):
            request = json.loads(order["request"])
            if request["side"] == "buy":
                exposure = dec(order["risk_notional"])
                gross += exposure
                by_symbol[request["symbol"]] = by_symbol.get(request["symbol"], ZERO) + exposure
        return equity, gross, by_symbol

    def prepare(self, client_id, *, symbol, side, quantity, limit_price, now_ms,
                hard_stop=None, trailing_bps="0"):
        with self._tx() as db:
            return self._prepare(db, client_id, symbol, side, quantity, limit_price, now_ms,
                                 hard_stop, trailing_bps, protective=False)

    def _prepare(self, db, client_id, symbol, side, quantity, limit_price, now_ms,
                 hard_stop, trailing_bps, *, protective):
        client_id, symbol = identifier(client_id), identifier(symbol)
        qty, price, trail = number(quantity), number(limit_price), number(trailing_bps)
        stop = number(hard_stop) if hard_stop is not None else None
        stamp(now_ms)
        if side not in ("buy", "sell") or qty <= 0 or price <= 0 or trail >= BPS:
            raise ControlError("invalid order")
        request = {"symbol": symbol, "side": side, "quantity": text_decimal(qty),
            "limit_price": text_decimal(price), "hard_stop": text_decimal(stop) if stop is not None else None,
            "trailing_bps": text_decimal(trail), "protective": protective}
        old = db.execute("SELECT * FROM orders WHERE client_id=?", (client_id,)).fetchone()
        if old:
            if old["fingerprint"] != digest(request):
                self._hold(db, "INTENT_ID_CONFLICT")
                raise Held("immutable client order identifier reused")
            return dict(old)
        self._gate(db)
        market = db.execute("SELECT * FROM markets WHERE symbol=?", (symbol,)).fetchone()
        if not market:
            raise ControlError("verified instrument and market required")
        self._fresh(market, now_ms)
        spec = json.loads(market["instrument"])
        if (qty % dec(spec["quantity_step"]) or price % dec(spec["price_tick"])
                or qty < dec(spec["minimum_quantity"]) or qty * price < dec(spec["minimum_notional"])):
            raise ControlError("order violates instrument precision/minimum")
        if qty * price > dec(self.limits["max_order_quote"]):
            raise ControlError("maximum order size exceeded")
        slippage = dec(self.limits["max_slippage_bps"]) / BPS
        if ((side == "buy" and price > dec(market["ask"]) * (1 + slippage)) or
                (side == "sell" and price < dec(market["bid"]) * (1 - slippage))):
            raise ControlError("limit exceeds slippage boundary")
        protection = db.execute("SELECT * FROM stops WHERE symbol=?", (symbol,)).fetchone()
        if side == "buy":
            if stop is None or not ZERO < stop < price:
                raise ControlError("long entry requires a hard stop below entry")
            if protection and protection["status"] != "CLOSED" and (protection["triggered"] or
                    stop < dec(protection["hard_stop"]) or (dec(protection["trailing_bps"]) and
                    (not trail or trail > dec(protection["trailing_bps"])))):
                raise ControlError("entry would bypass or loosen existing protection")
        fee = dec(self.limits["max_fee_bps"]) / BPS
        asset = self.quote if side == "buy" else spec["base"]
        reserve = (qty * price if side == "buy" else qty) * (1 + fee)
        if self._balance(db, asset) - self._reserved(db, asset) < reserve:
            raise ControlError("insufficient unreserved balance")
        if db.execute("SELECT COUNT(*) FROM orders WHERE state IN (?,?,?,?,?)", ACTIVE).fetchone()[0] >= self.limits["max_open_orders"]:
            raise ControlError("maximum outstanding orders exceeded")
        equity, gross, exposure = self._equity_and_exposure(db, now_ms)
        peak = dec(db.execute("SELECT peak_equity FROM risk WHERE id=1").fetchone()[0])
        if equity > peak:
            peak = equity
            db.execute("UPDATE risk SET peak_equity=? WHERE id=1", (text_decimal(peak),))
        drawdown = peak and (peak - equity) * BPS / peak
        if drawdown >= dec(self.limits["max_drawdown_bps"]):
            self._hold(db, "DRAWDOWN_LIMIT")
            raise Held("account drawdown circuit breaker")
        notional = qty * price
        prospective_exposure = notional * (1 + fee) if side == "buy" else notional
        if side == "buy" and (gross + prospective_exposure > dec(self.limits["max_gross_quote"]) or
                exposure.get(symbol, ZERO) + prospective_exposure > dec(self.limits["max_position_quote"])):
            raise ControlError("shared position/exposure limit exceeded")
        turnover = db.execute("SELECT turnover FROM daily WHERE day=?", (now_ms // 86400000,)).fetchone()
        daily = dec(turnover[0]) if turnover else ZERO
        pending = sum((dec(r[0]) for r in db.execute("SELECT risk_notional FROM orders")), ZERO)
        if not protective and daily + pending + prospective_exposure > dec(self.limits["max_daily_quote"]):
            raise ControlError("shared daily turnover limit exceeded")
        db.execute("INSERT INTO orders VALUES(?,?,?,'INTENT',NULL,'0','0',?,?,?,?,0,0)",
            (client_id, encode(request), digest(request), asset, text_decimal(reserve), text_decimal(prospective_exposure), now_ms))
        self._event(db, "INTENT_RESERVED", {"client_id": client_id})
        return dict(self._order(db, client_id))

    def begin_submission(self, client_id, *, now_ms):
        """Persist before hypothetical transport. This module supplies no transport."""
        with self._tx() as db:
            stamp(now_ms)
            self._gate(db)
            order = self._order(db, client_id)
            if order["state"] != "INTENT":
                raise ControlError("order cannot be submitted again")
            if now_ms < order["created_ms"]:
                raise ControlError("submission timestamp predates intent")
            request = json.loads(order["request"])
            market = db.execute("SELECT * FROM markets WHERE symbol=?", (request["symbol"],)).fetchone()
            self._fresh(market, now_ms)
            price = dec(request["limit_price"])
            slippage = dec(self.limits["max_slippage_bps"]) / BPS
            if ((request["side"] == "buy" and price > dec(market["ask"]) * (1 + slippage)) or
                    (request["side"] == "sell" and price < dec(market["bid"]) * (1 - slippage))):
                raise ControlError("market moved beyond reserved slippage boundary")
            equity, gross, exposure = self._equity_and_exposure(db, now_ms)
            peak = dec(db.execute("SELECT peak_equity FROM risk WHERE id=1").fetchone()[0])
            if peak and (peak - equity) * BPS >= peak * dec(self.limits["max_drawdown_bps"]):
                self._hold(db, "DRAWDOWN_LIMIT")
                raise Held("drawdown changed after intent reservation")
            if request["side"] == "buy":
                protection = db.execute("SELECT triggered FROM stops WHERE symbol=?", (request["symbol"],)).fetchone()
                if protection and protection[0]:
                    raise ControlError("entry protection has triggered")
                if gross > dec(self.limits["max_gross_quote"]) or exposure[request["symbol"]] > dec(self.limits["max_position_quote"]):
                    raise ControlError("exposure changed after intent reservation")
            if not request["protective"]:
                row = db.execute("SELECT turnover FROM daily WHERE day=?", (now_ms // 86400000,)).fetchone()
                daily = dec(row[0]) if row else ZERO
                pending = sum((dec(r[0]) for r in db.execute("SELECT risk_notional FROM orders")), ZERO)
                if daily + pending > dec(self.limits["max_daily_quote"]):
                    raise ControlError("daily turnover changed after intent reservation")
            db.execute("UPDATE risk SET submission_sequence=submission_sequence+1 WHERE id=1")
            db.execute("UPDATE orders SET state='SUBMITTING',submission_sequence="
                       "(SELECT submission_sequence FROM risk WHERE id=1) WHERE client_id=?", (client_id,))
            self._event(db, "SUBMISSION_STARTED", {"client_id": client_id})

    def mark_unknown(self, client_id, reason):
        if reason not in ("TIMEOUT", "CONNECTION_LOST", "HTTP_429", "HTTP_503"):
            raise ControlError("unsupported ambiguity code")
        with self._tx() as db:
            order = self._order(db, client_id)
            if order["state"] not in ("SUBMITTING", "UNKNOWN", "OPEN", "PARTIAL"):
                raise ControlError("order has no uncertain transport")
            db.execute("UPDATE orders SET state='UNKNOWN' WHERE client_id=?", (client_id,))
            self._event(db, "LOOKUP_REQUIRED", {"client_id": client_id, "reason": reason})

    def reconcile(self, client_id, *, exchange_order_id, state, cumulative_quantity, authoritative):
        """Explicit normalized offline lookup result; never queries/resends orders."""
        if exchange_order_id is not None:
            exchange_order_id = identifier(exchange_order_id)
        cumulative = number(cumulative_quantity)
        if authoritative is not True or state not in ("OPEN", "PARTIAL", *TERMINAL):
            raise ControlError("authoritative normalized order state required")
        if exchange_order_id is None and (state != "REJECTED" or cumulative != 0):
            raise ControlError("only a definitive zero-fill rejection may lack an exchange id")
        with self._tx() as db:
            order = self._order(db, client_id)
            request = json.loads(order["request"])
            if order["state"] == "INTENT":
                raise ControlError("order was never submitted")
            if order["exchange_id"] and order["exchange_id"] != exchange_order_id:
                self._hold(db, "ORDER_ID_CONFLICT")
                raise Held("exchange order identifier changed")
            duplicate = db.execute("SELECT client_id FROM orders WHERE exchange_id=?", (exchange_order_id,)).fetchone()
            if duplicate and duplicate[0] != client_id:
                self._hold(db, "ORDER_ID_CONFLICT")
                raise Held("exchange identifier belongs to another intent")
            missing = db.execute("SELECT 1 FROM fills WHERE client_id=? AND state='PENDING'", (client_id,)).fetchone()
            if (missing or cumulative != dec(order["filled_quantity"]) or
                    (state == "FILLED" and cumulative != dec(request["quantity"])) or
                    (state == "REJECTED" and cumulative != 0) or
                    (state == "OPEN" and cumulative != 0) or
                    (state == "PARTIAL" and not ZERO < cumulative < dec(request["quantity"]))):
                db.execute("UPDATE orders SET state='UNKNOWN',exchange_id=? WHERE client_id=?", (exchange_order_id, client_id))
                self._hold(db, "ORDER_FILL_RECONCILIATION_REQUIRED")
                raise Held("terminal/ack quantity is inconsistent with recorded fills")
            if order["state"] in TERMINAL:
                if state == order["state"]:
                    return
                self._hold(db, "TERMINAL_STATE_CONFLICT")
                raise Held("terminal order state changed")
            db.execute("UPDATE orders SET state=?,exchange_id=? WHERE client_id=?", (state, exchange_order_id, client_id))
            if state in TERMINAL:
                db.execute("UPDATE orders SET reserve_amount='0',risk_notional='0' WHERE client_id=?", (client_id,))
            if state == "REJECTED" and not order["rejection_counted"]:
                db.execute("UPDATE orders SET rejection_counted=1 WHERE client_id=?", (client_id,))
                db.execute("UPDATE risk SET rejections=rejections+1 WHERE id=1")
                count = db.execute("SELECT rejections FROM risk WHERE id=1").fetchone()[0]
                if count >= self.limits["rejection_threshold"]:
                    self._hold(db, "CONSECUTIVE_REJECTIONS")
            else:
                self._submission_succeeded(db, order)
            self._event(db, "ORDER_RECONCILED", {"client_id": client_id, "state": state})

    @staticmethod
    def _submission_succeeded(db, order):
        # Polling an old OPEN order must never reset newer rejected submissions.
        latest = db.execute("SELECT submission_sequence FROM risk WHERE id=1").fetchone()[0]
        if order["submission_sequence"] == latest and latest > 0:
            db.execute("UPDATE risk SET rejections=0 WHERE id=1")

    def _normalize_fill(self, fill):
        if fill.side not in ("buy", "sell") or type(fill.fees_complete) is not bool:
            raise ControlError("invalid normalized fill")
        quantity, cost = number(fill.quantity), number(fill.cost)
        if quantity <= 0 or cost <= 0:
            raise ControlError("fill quantity/cost must be positive")
        fees = {}
        for currency, amount in fill.fees:
            currency, amount = identifier(currency), fee_number(amount)
            fees[currency] = fees.get(currency, ZERO) + amount
        return {"fill_id": identifier(fill.fill_id), "client_id": identifier(fill.client_id),
            "receipt_key": encode([identifier(fill.symbol), identifier(fill.fill_id)]),
            "exchange_order_id": identifier(fill.exchange_order_id), "symbol": identifier(fill.symbol),
            "side": fill.side, "quantity": text_decimal(quantity), "cost": text_decimal(cost),
            "fees": {key: text_decimal(value) for key, value in sorted(fees.items())},
            "fees_complete": fill.fees_complete, "sequence": stamp(fill.sequence),
            "occurred_ms": stamp(fill.occurred_ms)}

    def apply_fill(self, fill):
        with self._tx() as db:
            payload = self._normalize_fill(fill)
            fid, cid = payload["receipt_key"], payload["client_id"]
            previous = db.execute("SELECT * FROM fills WHERE fill_id=?", (fid,)).fetchone()
            if previous and previous["fingerprint"] != digest(payload):
                self._hold(db, "FILL_ID_CONFLICT")
                raise Held("exchange fill identity reused with changed facts")
            order = db.execute("SELECT * FROM orders WHERE client_id=?", (cid,)).fetchone()
            if order is None:
                previous = db.execute("SELECT fingerprint FROM unmatched_fills WHERE fill_id=?", (fid,)).fetchone()
                if not previous:
                    db.execute("INSERT INTO unmatched_fills VALUES(?,?,?)", (fid, encode(payload), digest(payload)))
                self._hold(db, "UNMATCHED_FILL" if not previous or previous[0] == digest(payload) else "FILL_ID_CONFLICT")
                raise Held("unmatched fill retained; no order or balance invented")
            if db.execute("SELECT 1 FROM unmatched_fills WHERE fill_id=?", (fid,)).fetchone():
                self._hold(db, "UNMATCHED_FILL_REVIEW_REQUIRED")
                raise Held("unmatched receipt requires explicit reconciliation")
            if previous:
                if previous["fingerprint"] != digest(payload):
                    self._hold(db, "FILL_ID_CONFLICT")
                    raise Held("exchange fill identity reused with changed facts")
                if previous["state"] == "APPLIED":
                    return False
            else:
                db.execute("INSERT INTO fills VALUES(?,?,?,?,'PENDING','')", (fid, cid, encode(payload), digest(payload)))
            # Keep the inbox fact even if financial application fails. Financial
            # mutations, reservation changes, stop arming and audit event are atomic.
            db.execute("SAVEPOINT finance")
            try:
                self._apply_finance(db, order, payload)
            except ControlError:
                db.execute("ROLLBACK TO finance")
                db.execute("RELEASE finance")
                db.execute("UPDATE fills SET reason='RECONCILIATION_REQUIRED' WHERE fill_id=?", (fid,))
                self._hold(db, "UNAPPLIED_FILL")
                raise Held("fill retained pending reconciliation; balances unchanged")
            db.execute("RELEASE finance")
            return True

    def _apply_finance(self, db, order, fill):
        request = json.loads(order["request"])
        if fill["occurred_ms"] < order["created_ms"]:
            raise ControlError("fill predates immutable intent")
        if (fill["symbol"] != request["symbol"] or fill["side"] != request["side"] or
                order["state"] == "INTENT" or (order["exchange_id"] and
                order["exchange_id"] != fill["exchange_order_id"])):
            raise ControlError("fill/order identity mismatch")
        other = db.execute("SELECT client_id FROM orders WHERE exchange_id=?", (fill["exchange_order_id"],)).fetchone()
        if other and other[0] != fill["client_id"]:
            raise ControlError("fill exchange identity collision")
        risk = db.execute("SELECT last_sequence FROM risk WHERE id=1").fetchone()
        if fill["sequence"] != risk[0] + 1:
            raise ControlError("fill sequence gap or out-of-order event")
        market = db.execute("SELECT instrument FROM markets WHERE symbol=?", (request["symbol"],)).fetchone()
        spec = json.loads(market[0])
        if (not fill["fees_complete"] or any(k not in (spec["base"], self.quote) for k in fill["fees"])
                or any(dec(v) < 0 for v in fill["fees"].values())):
            raise ControlError("missing fees or unsupported fee valuation currency")
        qty, cost = dec(fill["quantity"]), dec(fill["cost"])
        filled = dec(order["filled_quantity"]) + qty
        remaining = dec(request["quantity"]) - filled
        if remaining < 0:
            raise ControlError("overfill")
        limit = dec(request["limit_price"])
        if ((request["side"] == "buy" and cost > qty * limit) or
                (request["side"] == "sell" and cost < qty * limit)):
            raise ControlError("fill exceeds limit/slippage boundary")
        base_fee = dec(fill["fees"].get(spec["base"], "0"))
        quote_fee = dec(fill["fees"].get(self.quote, "0"))
        fee_cap = dec(self.limits["max_fee_bps"]) / BPS
        if base_fee * cost + quote_fee * qty > fee_cap * qty * cost:
            raise ControlError("actual fee exceeds reserved budget")
        position = db.execute("SELECT * FROM positions WHERE symbol=?", (request["symbol"],)).fetchone()
        held_qty, basis, realized = ((dec(position[k]) for k in ("quantity", "basis", "realized"))
                                      if position else (ZERO, ZERO, ZERO))
        base, cash = self._balance(db, spec["base"]), self._balance(db, self.quote)
        if request["side"] == "buy":
            net = qty - base_fee
            if net <= 0:
                raise ControlError("nonpositive net fill")
            base += net
            cash -= cost + quote_fee
            held_qty += net
            basis += cost + quote_fee
        else:
            removed = qty + base_fee
            if removed > held_qty:
                raise ControlError("sell exceeds accounted inventory")
            removed_basis = basis if removed == held_qty else basis * removed / held_qty
            held_qty -= removed
            basis -= removed_basis
            realized += cost - quote_fee - removed_basis
            base -= removed
            cash += cost - quote_fee
        reserve = remaining * (limit if request["side"] == "buy" else 1) * (1 + fee_cap)
        if (base < self._reserved(db, spec["base"], order["client_id"]) + (reserve if request["side"] == "sell" else ZERO) or
                cash < self._reserved(db, self.quote, order["client_id"]) + (reserve if request["side"] == "buy" else ZERO)):
            raise ControlError("fill would consume another order's reservation")
        self._set_balance(db, spec["base"], base)
        self._set_balance(db, self.quote, cash)
        db.execute("INSERT INTO positions VALUES(?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
            "quantity=excluded.quantity,basis=excluded.basis,realized=excluded.realized",
            (request["symbol"], text_decimal(held_qty), text_decimal(basis), text_decimal(realized)))
        # Terminal cancellation does not suppress a late fill. Re-open its safety
        # state for authoritative lookup, and hold all new dispatch for review.
        late = order["state"] in ("CANCELLED", "REJECTED")
        state = "UNKNOWN" if late else ("FILLED" if not remaining else "PARTIAL")
        db.execute("UPDATE orders SET state=?,exchange_id=?,filled_quantity=?,filled_cost=?,"
            "reserve_amount=?,risk_notional=? WHERE client_id=?", (state, fill["exchange_order_id"],
            text_decimal(filled), text_decimal(dec(order["filled_cost"]) + cost), text_decimal(reserve),
            text_decimal(remaining * limit * (1 + fee_cap) if request["side"] == "buy" else remaining * limit), order["client_id"]))
        day = fill["occurred_ms"] // 86400000
        turnover = db.execute("SELECT turnover FROM daily WHERE day=?", (day,)).fetchone()
        db.execute("INSERT INTO daily VALUES(?,?) ON CONFLICT(day) DO UPDATE SET turnover=excluded.turnover",
                   (day, text_decimal((dec(turnover[0]) if turnover else ZERO) + cost)))
        if request["side"] == "buy":
            self._arm_stop(db, request, fill_price=cost / qty, fill_ms=fill["occurred_ms"])
        elif held_qty == 0:
            db.execute("UPDATE stops SET status='CLOSED' WHERE symbol=?", (request["symbol"],))
        db.execute("UPDATE fills SET state='APPLIED',reason='' WHERE fill_id=?", (fill["receipt_key"],))
        db.execute("UPDATE risk SET last_sequence=? WHERE id=1", (fill["sequence"],))
        if not late:
            self._submission_succeeded(db, order)
        self._event(db, "FILL_APPLIED", {"fill_id": fill["fill_id"], "client_id": order["client_id"]})
        if late:
            self._hold(db, "LATE_FILL_AFTER_TERMINAL")

    def _arm_stop(self, db, request, *, fill_price, fill_ms):
        stop, trail = dec(request["hard_stop"]), dec(request["trailing_bps"])
        row = db.execute("SELECT * FROM stops WHERE symbol=?", (request["symbol"],)).fetchone()
        if row and row["status"] != "CLOSED":
            stop = max(stop, dec(row["hard_stop"]), dec(row["effective_stop"]))
            trail = min(trail, dec(row["trailing_bps"])) if trail and dec(row["trailing_bps"]) else max(trail, dec(row["trailing_bps"]))
            db.execute("UPDATE stops SET hard_stop=?,effective_stop=?,trailing_bps=? WHERE symbol=?",
                       (text_decimal(stop), text_decimal(stop), text_decimal(trail), request["symbol"]))
        else:
            generation = row["generation"] if row else 0
            db.execute("INSERT OR REPLACE INTO stops VALUES(?,?,?,'0',?,0,NULL,?,'ARMED')",
                       (request["symbol"], text_decimal(stop), text_decimal(trail), text_decimal(stop), generation))
        # Anchor protection immediately to an actual fill, including a first
        # post-entry decline. A quote preceding that fill cannot set its peak.
        self._observe_stop(db, request["symbol"], fill_price)
        market = db.execute("SELECT bid,observed_ms FROM markets WHERE symbol=?", (request["symbol"],)).fetchone()
        if market and fill_ms <= market["observed_ms"] <= fill_ms + self.limits["quote_max_age_ms"]:
            self._observe_stop(db, request["symbol"], dec(market["bid"]))

    @staticmethod
    def _observe_stop(db, symbol, bid):
        row = db.execute("SELECT * FROM stops WHERE symbol=?", (symbol,)).fetchone()
        if row is None or row["status"] == "CLOSED":
            return row
        high = max(bid, dec(row["high_water"]))
        effective = max(dec(row["effective_stop"]), dec(row["hard_stop"]),
                        high * (1 - dec(row["trailing_bps"]) / BPS) if dec(row["trailing_bps"]) else ZERO)
        db.execute("UPDATE stops SET high_water=?,effective_stop=?,triggered=? WHERE symbol=?",
                   (text_decimal(high), text_decimal(effective), int(bool(row["triggered"]) or bid <= effective), symbol))
        return db.execute("SELECT * FROM stops WHERE symbol=?", (symbol,)).fetchone()

    def evaluate_stop(self, symbol, *, now_ms):
        """Latch protection and reserve one limit exit atomically; never dispatch."""
        stamp(now_ms)
        with self._tx() as db:
            row = db.execute("SELECT * FROM stops WHERE symbol=?", (identifier(symbol),)).fetchone()
            if not row or row["status"] == "CLOSED":
                return None
            market = db.execute("SELECT * FROM markets WHERE symbol=?", (symbol,)).fetchone()
            self._fresh(market, now_ms)
            bid = dec(market["bid"])
            row = self._observe_stop(db, symbol, bid)
            if not row["triggered"]:
                return None
            if row["exit_id"]:
                previous = self._order(db, row["exit_id"])
                if previous["state"] in ACTIVE:
                    return dict(previous)
            spec = json.loads(market["instrument"])
            available = self._balance(db, spec["base"]) - self._reserved(db, spec["base"])
            fee = dec(self.limits["max_fee_bps"]) / BPS
            tick, step = dec(spec["price_tick"]), dec(spec["quantity_step"])
            limit = (bid * (1 - dec(self.limits["max_slippage_bps"]) / BPS) / tick).to_integral_value(rounding=ROUND_CEILING) * tick
            qty = (min(available / (1 + fee), dec(self.limits["max_order_quote"]) / limit) / step).to_integral_value(rounding=ROUND_DOWN) * step
            generation = row["generation"] + 1
            client_id = "stop-" + digest(symbol)[:16] + "-" + str(generation)
            db.execute("SAVEPOINT stop_intent")
            try:
                order = self._prepare(db, client_id, symbol, "sell", text_decimal(qty), text_decimal(limit),
                                      now_ms, None, "0", protective=True)
            except Held:
                db.execute("RELEASE stop_intent")
                db.execute("UPDATE stops SET status='TRIGGERED_HELD' WHERE symbol=?", (symbol,))
                raise
            except ControlError:
                db.execute("ROLLBACK TO stop_intent")
                db.execute("RELEASE stop_intent")
                db.execute("UPDATE stops SET status='TRIGGERED_HELD' WHERE symbol=?", (symbol,))
                return None
            db.execute("RELEASE stop_intent")
            db.execute("UPDATE stops SET exit_id=?,generation=?,status='EXIT_RESERVED' WHERE symbol=?",
                       (client_id, generation, symbol))
            return order

    def snapshot(self):
        with self._tx() as db:
            return {"scope": "OFFLINE_ONLY", "live_dispatch_enabled": False,
                "risk": dict(db.execute("SELECT * FROM risk WHERE id=1").fetchone()),
                **{table: [dict(row) for row in db.execute("SELECT * FROM " + table)]
                   for table in ("balances", "positions", "orders", "fills", "unmatched_fills", "stops", "daily")}}

    def recovery_orders(self):
        with self._tx() as db:
            return [{**dict(row), "recovery_action": "LOOKUP_ONLY_NEVER_RESEND"} for row in
                    db.execute("SELECT * FROM orders WHERE state IN ('SUBMITTING','UNKNOWN','OPEN','PARTIAL')")]
