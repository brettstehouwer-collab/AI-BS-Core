import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import time
import math
import random
from typing import Dict, List, Optional, Any, Set
import ccxt.pro as ccxtpro
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.technical_indicators import CryptoTechnicals

from core.crypto_execution_safety import (
    execute_trade_protocol, execution_status, require_reconciled_execution,
)
from core.crypto_ledger_io import read_ledger, write_ledger


def log_trade_entry(*args, **kwargs):
    require_reconciled_execution()
    from core.cro_quantitative_ledger import log_trade_entry as log
    return log(*args, **kwargs)


def log_price_snapshot(*args, **kwargs):
    from core.cro_quantitative_ledger import log_price_snapshot as log
    return log(*args, **kwargs)


SCRIPT_DIR = Path(__file__).resolve().parent

def decrypt_vault_key(val):
    if val and val.startswith("gAAAAA"):
        try:
            from cryptography.fernet import Fernet
            key_path = SCRIPT_DIR / "vault_master.key"
            if not key_path.exists():
                key_path = SCRIPT_DIR.parent / "vault_master.key"
            if key_path.exists():
                with open(key_path, "rb") as f:
                    master_key = f.read()
                return Fernet(master_key).decrypt(val.encode()).decode()
            raise ValueError("Vault master key unavailable")
        except Exception as e:
            logger.error("Vault credential decryption failed; credential disabled")
            return ""
    return val


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CryptoTraderBot")

# --- SHM Bridge Setup ---
try:
    from shm_bridge import ShmBridge, TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY
except ImportError:

    class ShmBridge:
        def push_topic_event(self, topic, flags, data):
            return 0

    TOPIC_HEURISTICS_TELEMETRY = 0x0003
    FLAG_HIGH_PRIORITY = 0x02


class ShmTelemetry:
    def __init__(self):
        self.bridge = ShmBridge()

    def push_alert(self, msg: str):
        payload = f"CRYPTO_BOT|{msg}"
        self.bridge.push_topic_event(
            TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY, payload.encode("utf-8")[:60]
        )
        logger.info(f"SHM Push: {payload}")
        
        # Asynchronously dispatch to Discord webhook if configured
        webhook_url = keys.get("DISCORD_WEBHOOK_URL")
        if webhook_url and webhook_url.startswith("http"):
            try:
                import requests
                color = 0x3498db
                title = "⚡ AI-BS Crypto Scalp Event"
                if "PROFIT" in msg.upper():
                    color = 0xf1c40f
                    title = "💰 Take Profit Executed!"
                elif "BUY" in msg.upper() or "DCA" in msg.upper():
                    color = 0x2ecc71
                    title = "🎯 Dip Buy Executed!"
                elif "LIMIT" in msg.upper():
                    color = 0x9b59b6
                    title = "💧 Resting Dip Limit Set"

                embed_payload = {
                    "embeds": [{
                        "title": title,
                        "description": f"**Event:** `{msg}`",
                        "color": color,
                        "footer": {"text": "AI-BS Ultra-Fast Scalp Engine • Port 8007"}
                    }]
                }
                requests.post(webhook_url, json=embed_payload, timeout=3)
            except Exception as d_err:
                logger.debug(f"Discord alert dispatch note: {d_err}")

        # Windows system audio chime for fun trading feedback
        try:
            import winsound
            if "PROFIT" in msg.upper():
                winsound.Beep(2000, 100)
                winsound.Beep(2800, 150)
            else:
                winsound.Beep(1200, 100)
        except Exception:
            pass


shm = ShmTelemetry()

# --- Configuration: Resolve .env relative to this script's directory ---
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR.parent / ".env"
BACKEND_ENV_FILE = SCRIPT_DIR / ".env"

keys = {}
for env_path in [ENV_FILE, BACKEND_ENV_FILE]:
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    keys[k] = decrypt_vault_key(v.strip('"'))

LEDGER_FILE = Path(__file__).resolve().parent / "crypto_ledger.json"

WATCHER_SYMBOLS = [s.strip() for s in keys.get("WATCHER_SYMBOLS", "CRO/USD,CRO/USDT").split(",") if s.strip()]
TRADE_USD_AMOUNT = float(keys.get("TRADE_USD_AMOUNT", 1.10))
TAKE_PROFIT_PCT = float(keys.get("TAKE_PROFIT_PCT", 0.0085))
DCA_DIP_PCT = float(keys.get("BUY_DIP_PCT", keys.get("DCA_DIP_PCT", 0.0075)))
MACRO_SUPPORT_CEILING = float(keys.get("MACRO_SUPPORT_CEILING", 0.08500))
DUAL_STRATEGY_SPLIT = float(keys.get("DUAL_STRATEGY_SPLIT", 1.00))
REINVESTMENT_RATIO = float(keys.get("REINVESTMENT_RATIO", 1.00))
COMPOUND_EVERY_X_TRADES = int(keys.get("COMPOUND_EVERY_X_TRADES", 2))
MIN_COMPOUND_USD = float(keys.get("MIN_COMPOUND_USD", 1.05))
HOURLY_WINDOW_SEC = int(keys.get("HOURLY_WINDOW_MINUTES", 60)) * 60
FAST_SCALP_WINDOW_SEC = int(keys.get("FAST_SCALP_WINDOW_SEC", 30))
ACTION_COOLDOWN_SEC = float(keys.get("ACTION_COOLDOWN_SEC", 45.0))
hunting_eval_counter = 0
hunting_eval_start = time.time()

hourly_price_history = {}
fast_price_history = {}

def update_hourly_and_check_dip(symbol: str, current_price: float):
    now_ts = time.time()
    if symbol not in hourly_price_history:
        hourly_price_history[symbol] = []
    if symbol not in fast_price_history:
        fast_price_history[symbol] = []
    
    hourly_price_history[symbol].append((now_ts, current_price))
    hourly_price_history[symbol] = [
        (t, p) for t, p in hourly_price_history[symbol] if now_ts - t <= HOURLY_WINDOW_SEC
    ]

    fast_price_history[symbol].append((now_ts, current_price))
    fast_price_history[symbol] = [
        (t, p) for t, p in fast_price_history[symbol] if now_ts - t <= FAST_SCALP_WINDOW_SEC
    ]
    
    prices = [p for _, p in hourly_price_history[symbol]]
    fast_prices = [p for _, p in fast_price_history[symbol]]
    if not prices:
        return current_price, current_price, False, False
        
    hourly_avg = sum(prices) / len(prices)
    hourly_min = min(prices)
    hourly_max = max(prices)

    fast_avg = sum(fast_prices) / len(fast_prices) if fast_prices else current_price
    fast_max = max(fast_prices) if fast_prices else current_price

    hourly_range_pct = (hourly_max - hourly_min) / hourly_min if hourly_min > 0 else 0.0

    is_true_dip = current_price <= hourly_avg * (1.0 - DCA_DIP_PCT)
    is_fast_dip = current_price <= fast_avg * (1.0 - DCA_DIP_PCT)
    is_at_support = current_price <= MACRO_SUPPORT_CEILING
    is_hourly_dip = (is_true_dip or is_fast_dip) and is_at_support
    return hourly_avg, hourly_min, hourly_max, is_hourly_dip, is_fast_dip, hourly_range_pct

exchange_instance = None
bot_tasks = []
override_signals = []  # Queue of overrides
live_reference_prices = {}
latest_orderbooks: Dict[str, dict] = {}
last_dca_attempt_ts: Dict[str, float] = {}
tech_engine = CryptoTechnicals()

# --- 5 Production Measures: Climax & Volatility Protection States ---
trailing_profit_states: Dict[str, dict] = {}
climax_protection_telemetry: Dict[str, dict] = {}


# --- Real-Time WebSocket Orderbook Streaming Manager (Port 8007) ---
class OrderbookConnectionManager:
    """Manages active WebSocket subscribers for live market orderbook feeds on Port 8007."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscriptions: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, symbol: Optional[str] = None):
        origin = websocket.headers.get("origin")
        if origin and origin not in TRUSTED_ORIGINS:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            if symbol:
                norm_sym = symbol.replace("-", "/").upper()
                if norm_sym not in self.symbol_subscriptions:
                    self.symbol_subscriptions[norm_sym] = []
                self.symbol_subscriptions[norm_sym].append(websocket)
            logger.info(f"[WS 8007] Client connected. Total active: {len(self.active_connections)} (Target: {symbol or 'ALL'})")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            for sym, conns in list(self.symbol_subscriptions.items()):
                if websocket in conns:
                    conns.remove(websocket)
            logger.info(f"[WS 8007] Client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast_orderbook(self, symbol: str, orderbook: dict):
        if not self.active_connections:
            return

        norm_sym = symbol.replace("-", "/").upper()
        bids = orderbook.get("bids", [])[:15]
        asks = orderbook.get("asks", [])[:15]
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        mid_price = round((best_bid + best_ask) / 2.0, 5) if (best_bid and best_ask) else None
        spread = round(best_ask - best_bid, 5) if (best_bid and best_ask) else None
        
        bid_vol = sum(b[1] for b in bids)
        ask_vol = sum(a[1] for a in asks)
        imbalance = round(ask_vol / bid_vol, 3) if bid_vol > 0 else 1.0

        frame = {
            "type": "orderbook_tick",
            "symbol": norm_sym,
            "timestamp": time.time(),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "spread": spread,
            "imbalance_ratio": imbalance,
            "bids": bids,
            "asks": asks,
        }

        # Gather targets: dedicated subscribers + general subscribers
        targets: Set[WebSocket] = set()
        async with self._lock:
            if norm_sym in self.symbol_subscriptions:
                targets.update(self.symbol_subscriptions[norm_sym])
            for ws in self.active_connections:
                is_dedicated = any(ws in sym_list for sym_list in self.symbol_subscriptions.values())
                if not is_dedicated:
                    targets.add(ws)

        results = await asyncio.gather(
            *(asyncio.wait_for(ws.send_json(frame), timeout=1.0) for ws in targets),
            return_exceptions=True,
        )
        for ws, result in zip(targets, results):
            if isinstance(result, BaseException):
                await self.disconnect(ws)



ws_manager = OrderbookConnectionManager()


# --- Ledger Management (In-Memory Cached & Resilient Flush) ---
_ledger_cache = None
_last_ledger_read = 0.0

def load_ledger(force_reload=False):
    # Never substitute empty/cached holdings for unreadable authoritative bytes.
    global _ledger_cache, _last_ledger_read
    ledger = read_ledger(LEDGER_FILE)
    _ledger_cache = ledger
    _last_ledger_read = time.time()
    return ledger


def save_ledger(ledger):
    global _ledger_cache, _last_ledger_read
    write_ledger(LEDGER_FILE, ledger)
    _ledger_cache = ledger
    _last_ledger_read = time.time()


# --- Worker for a single symbol ---
last_limit_order_check = {}

async def evaluate_market_tick(exchange, symbol, best_bid, best_ask, orderbook=None, current_signals=None):
    if not execution_status()["dispatch_enabled"]:
        return
    if not best_bid or not best_ask:
        return

    # Option 2: Order Book Imbalance & Velocity Knife (Micro-Alpha & Falling Knife Protection)
    is_falling_knife = False
    bid_vol = 0.0
    ask_vol = 0.0
    if orderbook and len(orderbook.get("bids", [])) > 0 and len(orderbook.get("asks", [])) > 0:
        bids = orderbook["bids"][:10]
        asks = orderbook["asks"][:10]
        bid_vol = sum(b[1] for b in bids)
        ask_vol = sum(a[1] for a in asks)
        if bid_vol > 0 and ask_vol > 0 and (ask_vol / bid_vol >= 3.0):
            is_falling_knife = True

    # Measure 3 (Anti-Falling-Knife): Velocity Drop Check across fast window
    fast_prices = [p for _, p in fast_price_history.get(symbol, [])]
    if len(fast_prices) >= 4:
        fast_high = max(fast_prices)
        if fast_high > 0 and (fast_high - (best_bid + best_ask) / 2.0) / fast_high >= 0.012:
            is_falling_knife = True

    ledger = load_ledger()
    mid_price = (best_bid + best_ask) / 2.0
    if "reference_prices" not in ledger:
        ledger["reference_prices"] = {}
    ledger["reference_prices"][symbol] = mid_price
    live_reference_prices[symbol] = mid_price

    # Check active pending dip buy for this symbol (from prior profit trades)
    pending_dips = ledger.get("pending_dip_buys", {})
    if symbol in pending_dips:
        p_dip = pending_dips[symbol]
        lim_id = p_dip.get("limit_order_id")
        dip_target = p_dip.get("dip_target_price", 0.0)
        dip_amt = p_dip.get("buy_amount", 0.0)
        profit_src = p_dip.get("profit_reinvested", 0.0)

        is_dip_filled = False
        now_ts = time.time()
        last_check = last_limit_order_check.get(symbol, 0.0)
        should_check_order = (now_ts - last_check > 0.5) or (best_ask and best_ask <= dip_target * 1.002)

        if lim_id and exchange and should_check_order:
            last_limit_order_check[symbol] = now_ts
            try:
                ord_check = await exchange.fetch_order(lim_id, symbol)
                if ord_check.get("status") == "closed":
                    is_dip_filled = True
            except Exception as e:
                logger.debug(f"Limit order fetch note for {lim_id}: {e}")
                if best_ask and best_ask <= dip_target:
                    is_dip_filled = True
        elif best_ask and best_ask <= dip_target:
            try:
                await execute_trade_protocol(exchange, symbol, "buy", dip_amt)
                is_dip_filled = True
            except Exception as e:
                logger.error(f"Watcher dip buy error: {e}")

        if is_dip_filled:
            logger.info(f"POST-PROFIT DIP BUY FILLED for {symbol}: {dip_amt} @ ${dip_target:.5f}")
            shm.push_alert(f"DIP BUY FILLED {symbol}")
            curr_pos = ledger["positions"].get(symbol, {"amount": 0.0, "avg_buy_price": 0.0, "long_term_vault": 0.0})
            old_amt = curr_pos.get("amount", 0.0)
            old_price = curr_pos.get("avg_buy_price", 0.0)
            vault = curr_pos.get("long_term_vault", 0.0)

            tot_cost = (old_amt * old_price) + (dip_amt * dip_target)
            new_total_amt = old_amt + dip_amt
            new_avg_px = tot_cost / new_total_amt if new_total_amt > 0 else dip_target

            ledger["positions"][symbol] = {
                "amount": new_total_amt,
                "avg_buy_price": new_avg_px,
                "long_term_vault": vault
            }
            del ledger["pending_dip_buys"][symbol]
            ledger["last_action"] = f"DIP_BUY_FILLED {symbol}: {dip_amt} CRO @ ${dip_target:.5f} (Profits Reinvested: +${profit_src:.3f})"
            save_ledger(ledger)
            log_trade_entry(
                trade_type="BUY",
                price=dip_target,
                amount=dip_amt,
                symbol=symbol,
                strategy_trigger="POST_PROFIT_DIP_FILLED",
                notes=f"Post-profit dip buy filled and absorbed into position (New Avg: ${new_avg_px:.5f})"
            )

    # Track rolling window for dip and micro-scalp detection
    hourly_avg, hourly_min, hourly_max, is_hourly_dip, is_fast_dip, hourly_range_pct = update_hourly_and_check_dip(symbol, mid_price)

    # Measure 5: Climax & High-Velocity Volatility Circuit Breaker Detection
    is_climax_volatility = hourly_range_pct >= 0.035
    effective_cooldown = max(ACTION_COOLDOWN_SEC * 2.0, 90.0) if is_climax_volatility else ACTION_COOLDOWN_SEC

    # Compounding Reinvestment Engine: Base $1.10 + 100% of accumulated profit
    reinvest_boost = ledger.get("total_profit_usd", 0.0) * REINVESTMENT_RATIO
    base_trade_size = max(1.10, TRADE_USD_AMOUNT + reinvest_boost)
    effective_trade_size = max(1.05, base_trade_size * 0.70) if is_climax_volatility else base_trade_size

    # Technical Signals & Live Confluence
    atr_pct = float(current_signals.get("atr_pct", 0.012)) if current_signals else 0.012
    rsi = float(current_signals.get("rsi", 50.0)) if current_signals else 50.0
    bb_status = current_signals.get("bb", "NORMAL") if current_signals else "NORMAL"
    macd_status = current_signals.get("macd", "NEUTRAL") if current_signals else "NEUTRAL"

    # Measure 2: Volatility-Adaptive Target Auto-Scaling
    adaptive_tp = max(TAKE_PROFIT_PCT, atr_pct * 1.20)
    if rsi > 68 or bb_status == "OVERBOUGHT_BB":
        adaptive_tp = max(adaptive_tp, 0.0180)  # Allow runners in strong momentum expansion
    dynamic_take_profit = min(max(adaptive_tp, 0.0075), 0.0400)

    adaptive_dip = max(DCA_DIP_PCT, atr_pct * 1.50)
    dynamic_dca_dip = min(max(adaptive_dip, 0.0075), 0.0500)

    # Measure 3: Reversal Confirmation Check for Dip Buying
    fast_min = min(fast_prices) if fast_prices else best_ask
    has_reversal_confirmation = (
        (best_ask >= fast_min * 1.0005)
        or (rsi >= 30 and macd_status != "BEARISH")
        or (bid_vol > 0 and ask_vol > 0 and bid_vol >= ask_vol * 1.15)
    )

    # Telemetry Cache for Port 8007
    climax_protection_telemetry[symbol] = {
        "trailing_stop_active": trailing_profit_states.get(symbol, {}).get("active", False),
        "trailing_peak_price": trailing_profit_states.get(symbol, {}).get("peak_price", 0.0),
        "trailing_buffer_pct": trailing_profit_states.get(symbol, {}).get("trail_buffer_pct", 0.0050),
        "dynamic_take_profit": round(dynamic_take_profit, 4),
        "dynamic_dca_dip": round(dynamic_dca_dip, 4),
        "atr_pct": round(atr_pct, 4),
        "hourly_volatility_pct": round(hourly_range_pct * 100, 2),
        "is_climax_volatility": is_climax_volatility,
        "reversal_confirmed": has_reversal_confirmation,
        "is_knife": is_falling_knife,
        "effective_cooldown_sec": effective_cooldown,
    }

    # --- Fast Scalping & Take Profit Execution ---
    if symbol in ledger["positions"] and ledger["positions"][symbol].get("amount", 0.0) > 0:
        pos = ledger["positions"][symbol]
        avg_buy_price = pos["avg_buy_price"]
        amount = pos["amount"]

        # Measure 1: Autonomous Trailing Profit Lock
        if symbol not in trailing_profit_states:
            trailing_profit_states[symbol] = {
                "active": False,
                "peak_price": 0.0,
                "peak_gain_pct": 0.0,
                "armed_at": 0.0,
                "trail_buffer_pct": 0.0050,
            }
        t_state = trailing_profit_states[symbol]

        current_gain_pct = (best_bid - avg_buy_price) / avg_buy_price if avg_buy_price > 0 else 0.0
        should_take_profit = False
        tp_reason = ""

        # Check if minimum profit threshold is crossed to arm or update trailing lock
        if avg_buy_price > 0 and current_gain_pct >= dynamic_take_profit:
            trail_buffer = min(max(atr_pct * 0.45, 0.0040), 0.0120)

            if not t_state.get("active", False):
                t_state["active"] = True
                t_state["peak_price"] = best_bid
                t_state["peak_gain_pct"] = current_gain_pct
                t_state["armed_at"] = time.time()
                t_state["trail_buffer_pct"] = trail_buffer
                logger.info(
                    f"🎯 TRAILING PROFIT LOCK ARMED for {symbol} @ ${best_bid:.5f}! Gain: +{current_gain_pct*100:.2f}% (Target: {dynamic_take_profit*100:.2f}%, Trail Buffer: {trail_buffer*100:.2f}%)"
                )
                shm.push_alert(f"TRAIL ARMED {symbol} +{current_gain_pct*100:.1f}%")
            else:
                if best_bid > t_state.get("peak_price", 0.0):
                    t_state["peak_price"] = best_bid
                    t_state["peak_gain_pct"] = current_gain_pct
                    t_state["trail_buffer_pct"] = trail_buffer
                    logger.info(
                        f"📈 TRAIL HIGH WATERMARK for {symbol}: Peak ${best_bid:.5f} (+{current_gain_pct*100:.2f}%)"
                    )

        # Check rollover/harvest condition if trailing stop is active
        if t_state.get("active", False):
            peak_px = t_state.get("peak_price", best_bid)
            buffer = t_state.get("trail_buffer_pct", 0.0050)
            trail_stop_price = peak_px * (1.0 - buffer)
            min_locked_price = avg_buy_price * (1.0 + max(0.0040, dynamic_take_profit * 0.50))

            if best_bid <= trail_stop_price:
                should_take_profit = True
                tp_reason = f"Trailing Rollover (${peak_px:.5f} -> ${best_bid:.5f}, -{buffer*100:.2f}%)"
            elif best_bid <= min_locked_price:
                should_take_profit = True
                tp_reason = f"Minimum Guaranteed Profit Floor (${min_locked_price:.5f})"
            elif rsi > 82 and best_bid < peak_px * 0.998:
                should_take_profit = True
                tp_reason = f"Parabolic Climax Exhaustion (RSI {rsi:.1f})"

        # Execute harvest on trailing trigger
        if should_take_profit:
            t_state["active"] = False
            t_state["peak_price"] = 0.0
            logger.info(
                f"TAKING PROFIT ON {symbol}! Reason: {tp_reason} | Best bid ${best_bid:.5f} (+{current_gain_pct*100:.2f}% above avg ${avg_buy_price:.5f})"
            )
            try:
                raw_sell = amount * DUAL_STRATEGY_SPLIT
                sell_amount = float(exchange.amount_to_precision(symbol, raw_sell)) if exchange else raw_sell
                
                # CRITICAL NOTIONAL CHECK FOR CRYPTO.COM:
                # If selling 50% is < $1.00 USD, but the total position is >= $1.00 USD,
                # sell the full position so Crypto.com doesn't reject with MIN_NOTIONAL!
                if sell_amount * best_bid < 1.00 and amount * best_bid >= 1.00:
                    sell_amount = float(exchange.amount_to_precision(symbol, amount)) if exchange else amount

                kept_amount = amount - sell_amount

                if sell_amount > 0:
                    await execute_trade_protocol(exchange, symbol, "sell", sell_amount)
                    shm.push_alert(f"TAKE PROFIT {symbol}")
                    # Account for round-trip exchange fees (~0.15% = 0.075% buy fee + 0.075% sell fee)
                    est_fees = (avg_buy_price * sell_amount * 0.00075) + (best_bid * sell_amount * 0.00075)
                    gross_profit_usd = (best_bid - avg_buy_price) * sell_amount
                    profit_usd = max(0.0, round(gross_profit_usd - est_fees, 4))
                    ledger["total_profit_usd"] = round(ledger.get("total_profit_usd", 0.0) + profit_usd, 4)
                    
                    # Track cycle profit for house-money CRO compounding
                    ledger["cycle_profit_usd"] = round(ledger.get("cycle_profit_usd", 0.0) + profit_usd, 4)
                    ledger["trades_since_compound"] = ledger.get("trades_since_compound", 0) + 1
                else:
                    profit_usd = 0.0

                if kept_amount > 0:
                    ledger["positions"][symbol] = {
                        "amount": kept_amount,
                        "avg_buy_price": avg_buy_price,
                        "long_term_vault": round(ledger.get("positions", {}).get(symbol, {}).get("long_term_vault", 0.0) + kept_amount, 4)
                    }
                    ledger["last_action"] = f"TAKE_PROFIT {symbol} (+${profit_usd:.3f}) | STACKED {kept_amount:.2f} CRO"
                else:
                    if symbol in ledger["positions"]:
                        vault = ledger["positions"][symbol].get("long_term_vault", 0.0)
                        ledger["positions"][symbol] = {
                            "amount": 0.0,
                            "avg_buy_price": 0.0,
                            "long_term_vault": vault
                        }
                    ledger["last_action"] = f"TAKE_PROFIT {symbol} +${profit_usd:.3f}"

                ledger["strategy_layer"] = "High-Frequency Fast Scalp & Harvest Engine"
                save_ledger(ledger)
                log_trade_entry(
                    trade_type="TAKE_PROFIT",
                    price=best_bid,
                    amount=sell_amount,
                    symbol=symbol,
                    strategy_trigger="HOURLY_TAKE_PROFIT_HARVEST",
                    notes=f"Realized +${profit_usd:.3f} USD profit; Reinvested into Compounding Pool"
                )

                # --- Measure 4: Autonomous Post-Profit Dip Buy Setup with Climax Protection ---
                is_climax_high = (rsi > 68) or (best_bid >= hourly_avg * 1.025) or (bb_status == "OVERBOUGHT_BB")
                if is_climax_high and hourly_avg > 0:
                    safe_climax_dip = min(best_bid * (1.0 - dynamic_dca_dip * 1.8), hourly_avg * 0.998)
                    dip_price = float(exchange.price_to_precision(symbol, safe_climax_dip)) if exchange else round(safe_climax_dip, 5)
                    logger.info(
                        f"🛡️ CLIMAX HARVEST PROTECTION: Anchored post-profit dip to mean ${dip_price:.5f} (Avoided peak re-entry at ${best_bid * (1.0 - dynamic_dca_dip):.5f})"
                    )
                else:
                    dip_price = float(exchange.price_to_precision(symbol, best_bid * (1.0 - dynamic_dca_dip))) if exchange else round(best_bid * (1.0 - dynamic_dca_dip), 5)
                dip_trade_size = max(1.00, TRADE_USD_AMOUNT + profit_usd)
                raw_dip_amt = dip_trade_size / dip_price
                dip_buy_amt = float(exchange.amount_to_precision(symbol, raw_dip_amt)) if exchange else round(raw_dip_amt, 2)
                if dip_buy_amt * dip_price < 1.00:
                    dip_buy_amt = float(exchange.amount_to_precision(symbol, dip_buy_amt + 1.0)) if exchange else dip_buy_amt + 1.0

                limit_placed = False
                limit_order_id = None
                try:
                    if exchange and dip_buy_amt > 0 and dip_price > 0:
                        order_res = await execute_trade_protocol(exchange, symbol, "buy", dip_buy_amt, price=dip_price)
                        limit_order_id = order_res.get("id")
                        limit_placed = True
                        logger.info(f"POST-PROFIT LIMIT DIP BUY PLACED: {dip_buy_amt} {symbol} @ ${dip_price:.5f} (Order ID: {limit_order_id})")
                        shm.push_alert(f"LIMIT DIP BUY {symbol} @ {dip_price}")
                except Exception as limit_err:
                    logger.warning(f"Resting limit buy fallback to watcher: {limit_err}")

                if "pending_dip_buys" not in ledger:
                    ledger["pending_dip_buys"] = {}
                ledger["pending_dip_buys"][symbol] = {
                    "dip_target_price": dip_price,
                    "allocated_usd": dip_trade_size,
                    "profit_reinvested": profit_usd,
                    "buy_amount": dip_buy_amt,
                    "limit_order_id": limit_order_id,
                    "status": "resting_limit" if limit_placed else "watcher_trigger",
                    "set_at_ts": time.time(),
                    "set_at_price": best_bid
                }
                ledger["last_action"] += f" | DIP BUY SET @ ${dip_price:.5f} (${dip_trade_size:.2f})"
                save_ledger(ledger)

                log_trade_entry(
                    trade_type="LIMIT_ORDER" if limit_placed else "DIP_TARGET_SET",
                    price=dip_price,
                    amount=dip_buy_amt,
                    symbol=symbol,
                    strategy_trigger="POST_PROFIT_DIP_COMPOUND",
                    notes=f"Next Dip Buy Set using +${profit_usd:.3f} profit (Target: ${dip_price:.5f}, Size: ${dip_trade_size:.2f})"
                )

                # --- Autonomous Profit-Compounded CRO Build (When Accumulated Profit >= $1.05 USD) ---
                cycle_profits = ledger.get("cycle_profit_usd", 0.0)
                if cycle_profits >= MIN_COMPOUND_USD:
                    try:
                        balance = await exchange.fetch_balance()
                        quote_ccy = symbol.split("/")[1] if "/" in symbol else "USD"
                        quote_free = float(balance.get(quote_ccy, {}).get("free", 0.0))
                        if quote_free >= cycle_profits and best_ask and best_ask > 0:
                            raw_comp_amt = cycle_profits / best_ask
                            comp_amt = float(exchange.amount_to_precision(symbol, raw_comp_amt)) if exchange else round(raw_comp_amt, 2)
                            if comp_amt * best_ask < 1.00:
                                comp_amt = float(exchange.amount_to_precision(symbol, comp_amt + 1.0)) if exchange else comp_amt + 1.0
                                
                            if comp_amt > 0:
                                logger.info(f"PROFIT ACCUMULATION TRIGGER: Buying {comp_amt} {symbol} using ${cycle_profits:.2f} accumulated house-money profits!")
                                await execute_trade_protocol(exchange, symbol, "buy", comp_amt)
                                shm.push_alert(f"PROFIT STACKED: +{comp_amt} CRO")
                                
                                pos_vault = ledger["positions"].get(symbol, {}).get("long_term_vault", 0.0)
                                if symbol not in ledger["positions"]:
                                    ledger["positions"][symbol] = {"amount": 0.0, "avg_buy_price": 0.0, "long_term_vault": 0.0}
                                ledger["positions"][symbol]["long_term_vault"] = round(pos_vault + comp_amt, 4)
                                ledger["total_compounded_cro"] = round(ledger.get("total_compounded_cro", 0.0) + comp_amt, 4)
                                ledger["cycle_profit_usd"] = 0.0
                                ledger["trades_since_compound"] = 0
                                ledger["last_action"] = f"PROFIT_COMPOUND_STACK: +{comp_amt:.2f} CRO built from house money!"
                                save_ledger(ledger)
                                
                                log_trade_entry(
                                    trade_type="BUY",
                                    price=best_ask,
                                    amount=comp_amt,
                                    symbol=symbol,
                                    strategy_trigger="PROFIT_MILESTONE_ACCUMULATOR",
                                    notes=f"Autonomous Profit Compounding: Deployed ${cycle_profits:.2f} accumulated profit to stack +{comp_amt} CRO into vault"
                                )
                    except Exception as comp_err:
                        logger.error(f"Profit compounding buy failed: {comp_err}")

            except Exception as e:
                logger.error(f"Failed to take profit on {symbol}: {e}")

        # Layer 1: DCA on Genuine Dips (Requires price to be at least dynamic_dca_dip below entry with Reversal Confirmation)
        elif (
            avg_buy_price > 0
            and ((best_ask - avg_buy_price) / avg_buy_price <= -dynamic_dca_dip)
            and (is_hourly_dip or is_fast_dip or best_ask <= hourly_min * 1.002)
            and has_reversal_confirmation
            and not is_falling_knife
            and (time.time() - last_dca_attempt_ts.get(symbol, 0.0) > effective_cooldown)
            and (time.time() - ledger.get("last_trade_ts", 0.0) > effective_cooldown)
        ):
            if is_falling_knife:
                logger.warning(f"DCA REJECTED for {symbol}: Falling Knife detected!")
            else:
                logger.info(
                    f"HOURLY DIP DCA TRIGGERED for {symbol}! Best ask {best_ask} (Hourly Avg: {hourly_avg:.5f}, Min: {hourly_min:.5f}, Size: ${effective_trade_size:.2f})"
                )
            try:
                balance = await exchange.fetch_balance()
                quote_ccy = symbol.split("/")[1] if "/" in symbol else "USD"
                quote_balance = float(balance.get(quote_ccy, {}).get("free", 0.0))
                if quote_balance >= effective_trade_size:
                    raw_amt = effective_trade_size / best_ask
                    buy_amt = float(exchange.amount_to_precision(symbol, raw_amt))
                    if buy_amt * best_ask < 1.00:
                        buy_amt = float(exchange.amount_to_precision(symbol, math.ceil(raw_amt)))
                    if buy_amt > 0:
                        await execute_trade_protocol(exchange, symbol, "buy", buy_amt)
                        shm.push_alert(f"HOURLY DIP BOUGHT {symbol}")
                        total_cost = (avg_buy_price * amount) + (best_ask * buy_amt)
                        new_amount = amount + buy_amt
                        existing_vault = ledger["positions"][symbol].get("long_term_vault", 0.0)
                        ledger["positions"][symbol] = {
                            "amount": new_amount,
                            "avg_buy_price": total_cost / new_amount,
                            "long_term_vault": existing_vault,
                        }
                        ledger["last_trade_ts"] = time.time()
                        last_dca_attempt_ts[symbol] = time.time()
                        ledger["last_action"] = f"HOURLY_DIP_BUY {symbol} (${effective_trade_size:.2f})"
                        ledger["strategy_layer"] = "High-Frequency Fast Scalp & Harvest Engine"
                        save_ledger(ledger)
                        log_trade_entry(
                            trade_type="DCA_IN",
                            price=best_ask,
                            amount=buy_amt,
                            symbol=symbol,
                            strategy_trigger="HOURLY_LOWEST_DIP_COMPOUND",
                            notes=f"Hourly Dip Buy (Size: ${effective_trade_size:.2f} USD, Hourly Avg: {hourly_avg:.5f})"
                        )
                else:
                    last_dca_attempt_ts[symbol] = time.time()
                    logger.info(f"DCA pending for {symbol}: Awaiting cash or take-profit harvest (${quote_balance:.2f} free USD, ${effective_trade_size:.2f} required)")
                    ledger["last_trade_ts"] = time.time()
                    save_ledger(ledger)
            except Exception as e:
                logger.error(f"Failed to DCA {symbol}: {e}")
    else:
        # Fast Scalp Micro-Entry when position is 0
        last_action_ts = ledger.get("last_trade_ts", 0.0)
        is_eligible_price = best_ask <= MACRO_SUPPORT_CEILING
        has_scalp_trigger = (
            (is_hourly_dip or is_fast_dip or (current_signals and (current_signals.get("rsi", 50) < 50 or current_signals.get("macd") == "BULLISH")))
            and has_reversal_confirmation
            and not is_falling_knife
        )

        if is_eligible_price and has_scalp_trigger and not is_falling_knife and (time.time() - last_action_ts > effective_cooldown):
            logger.info(
                f"⚡ FAST SCALP BUY TRIGGERED for {symbol}! Best ask ${best_ask:.5f} (Size: ${effective_trade_size:.2f})"
            )
            try:
                balance = await exchange.fetch_balance()
                quote_ccy = symbol.split("/")[1] if "/" in symbol else "USD"
                quote_balance = float(balance.get(quote_ccy, {}).get("free", 0.0))
                if quote_balance >= effective_trade_size:
                    raw_amt = effective_trade_size / best_ask
                    buy_amt = float(exchange.amount_to_precision(symbol, raw_amt))
                    if buy_amt * best_ask < 1.00:
                        buy_amt = float(exchange.amount_to_precision(symbol, math.ceil(raw_amt)))
                    if buy_amt > 0:
                        await execute_trade_protocol(exchange, symbol, "buy", buy_amt)
                        shm.push_alert(f"FAST SCALP BUY {symbol} @ ${best_ask:.5f}")
                        existing_vault = ledger.get("positions", {}).get(symbol, {}).get("long_term_vault", 0.0)
                        ledger["positions"][symbol] = {
                            "amount": buy_amt,
                            "avg_buy_price": best_ask,
                            "long_term_vault": existing_vault,
                        }
                        ledger["last_trade_ts"] = time.time()
                        ledger["last_action"] = f"FAST_SCALP_BUY {symbol}: {buy_amt} CRO @ ${best_ask:.5f} (${effective_trade_size:.2f})"
                        ledger["strategy_layer"] = "High-Frequency Fast Scalp & Harvest Engine"
                        save_ledger(ledger)
                        log_trade_entry(
                            trade_type="BUY",
                            price=best_ask,
                            amount=buy_amt,
                            symbol=symbol,
                            strategy_trigger="FAST_SCALP_MICRO_ENTRY",
                            notes=f"Fast Scalp Entry for active cycle profit (${effective_trade_size:.2f} USD)"
                        )
                else:
                    logger.warning(f"Not enough USD to buy {symbol} (balance: ${quote_balance:.2f}, required: ${effective_trade_size:.2f})")
            except Exception as e:
                logger.error(f"Failed fast scalp entry for {symbol}: {e}")


async def watch_symbol_loop(exchange, symbol):
    logger.info(f"Starting continuous WS & REST hybrid watcher for {symbol}...")
    last_tech_fetch = 0
    current_signals = None
    retry_delay = 1.0

    while True:
        try:
            # Periodically fetch technicals every 60 seconds
            if time.time() - last_tech_fetch > 60:
                try:
                    current_signals = await tech_engine.get_all_signals(symbol)
                except Exception as tech_err:
                    logger.debug(f"Technicals fetch note on {symbol}: {tech_err}")
                last_tech_fetch = time.time()

            # 1. Real-time CCXT Pro WebSocket streaming with 10-second watchdog timeout
            try:
                orderbook = await asyncio.wait_for(exchange.watch_order_book(symbol), timeout=10.0)
                latest_orderbooks[symbol] = orderbook
                await ws_manager.broadcast_orderbook(symbol, orderbook)
                best_bid = orderbook["bids"][0][0] if len(orderbook["bids"]) > 0 else None
                best_ask = orderbook["asks"][0][0] if len(orderbook["asks"]) > 0 else None
                if best_bid and best_ask:
                    await evaluate_market_tick(exchange, symbol, best_bid, best_ask, orderbook, current_signals)
            except asyncio.TimeoutError:
                # REST fallback retrieves real depth; missing data must not synthesize liquidity.
                try:
                    orderbook = await asyncio.wait_for(exchange.fetch_order_book(symbol), timeout=10.0)
                    bids, asks = orderbook.get("bids", []), orderbook.get("asks", [])
                    if not bids or not asks:
                        raise ValueError("Empty REST orderbook")
                    latest_orderbooks[symbol] = orderbook
                    await ws_manager.broadcast_orderbook(symbol, orderbook)
                    await evaluate_market_tick(exchange, symbol, bids[0][0], asks[0][0], orderbook, current_signals)
                except Exception:
                    raise

            retry_delay = 1.0

            global hunting_eval_counter
            hunting_eval_counter += 1
            await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            raise
        except Exception as error:
            # CCXT classifies network, timeout, 429 and 503 errors. Never retry orders.
            logger.warning("Market feed unavailable for %s (%s); backing off", symbol, type(error).__name__)
            await asyncio.sleep(retry_delay + random.uniform(0, retry_delay * 0.2))
            retry_delay = min(60.0, retry_delay * 2.0)



# --- Master Override Loop (Layer 3) ---
async def master_strategy_loop(exchange):
    logger.info("Starting Master Strategy & Alpha Override Loop...")
    while True:
        try:
            ledger = load_ledger()

            if override_signals:
                action, symbol = override_signals.pop(0)
                logger.warning(f"EXECUTING ALPHA OVERRIDE: {action} {symbol}")
                ledger["last_action"] = f"ALPHA OVERRIDE: {action} {symbol}"
                ledger["strategy_layer"] = "Agent-Driven Alpha"
                save_ledger(ledger)

                if action == "MARKET_BUY":
                    try:
                        ticker = await exchange.fetch_ticker(symbol)
                        price = ticker["last"]
                        if price and price > 0:
                            buy_amt = float(
                                exchange.amount_to_precision(
                                    symbol, TRADE_USD_AMOUNT / price
                                )
                            )
                            if buy_amt > 0:
                                await execute_trade_protocol(exchange, symbol, "buy", buy_amt)
                                shm.push_alert(f"ALPHA BOUGHT {symbol}")

                                # Track in ledger immediately
                                pos = ledger["positions"].get(
                                    symbol, {"amount": 0.0, "avg_buy_price": 0.0}
                                )
                                total_cost = (pos["avg_buy_price"] * pos["amount"]) + (
                                    price * buy_amt
                                )
                                new_amount = pos["amount"] + buy_amt
                                ledger["positions"][symbol] = {
                                    "amount": new_amount,
                                    "avg_buy_price": total_cost / new_amount,
                                }
                                save_ledger(ledger)

                    except Exception as e:
                        logger.error(f"Alpha buy failed: {e}")

            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Master loop error: {e}")
            await asyncio.sleep(5)


# --- TWAP / Drip Engine (Layer 5) ---
async def process_twap_tick(exchange, ledger):
    twap_orders = ledger.get("twap_orders", [])
    modified = False

    active_twaps = []
    for twap in twap_orders:
        if twap["remaining_usd"] <= 0:
            continue # Completed

        now = time.time()
        if now - twap["last_drip_time"] >= twap["drip_interval_seconds"]:
            # Time to drip
            symbol = twap["symbol"]
            drip_size = min(twap["drip_size_usd"], twap["remaining_usd"])
            
            try:
                ticker = await exchange.fetch_ticker(symbol)
                price = ticker["last"]
                if price and price > 0:
                    buy_amt = float(exchange.amount_to_precision(symbol, drip_size / price))
                    if buy_amt > 0:
                        await execute_trade_protocol(exchange, symbol, "buy", buy_amt)
                        shm.push_alert(f"TWAP DRIP BOUGHT {symbol}")
                        
                        twap["remaining_usd"] -= drip_size
                        twap["last_drip_time"] = now
                        modified = True
                        
                        # Track in standard ledger positions
                        pos = ledger["positions"].get(symbol, {"amount": 0.0, "avg_buy_price": 0.0})
                        total_cost = (pos["avg_buy_price"] * pos["amount"]) + (price * buy_amt)
                        new_amount = pos["amount"] + buy_amt
                        ledger["positions"][symbol] = {
                            "amount": new_amount,
                            "avg_buy_price": total_cost / new_amount,
                        }
                        
                        ledger["last_action"] = f"TWAP DRIP {symbol} ${drip_size:.2f} (Rem: ${twap['remaining_usd']:.2f})"
                        ledger["strategy_layer"] = "TWAP Time-Weighted Entry"
                        logger.info(f"TWAP Executed: Bought {buy_amt} {symbol} for ${drip_size:.2f}")
            except Exception as e:
                logger.error(f"TWAP drip failed for {symbol}: {e}")
                
        if twap["remaining_usd"] > 0:
            active_twaps.append(twap)
            
    if modified:
        ledger["twap_orders"] = active_twaps
        
    return modified, ledger


async def twap_engine_loop(exchange):
    logger.info("Starting TWAP / Drip Engine Loop...")
    while True:
        try:
            ledger = load_ledger()
            modified, ledger = await process_twap_tick(exchange, ledger)
            
            if modified:
                save_ledger(ledger)

            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"TWAP Engine loop error: {e}")
            await asyncio.sleep(5)


async def resilient_worker(coro_fn, *args, name="worker"):
    while True:
        try:
            await coro_fn(*args)
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error(f"ResilientWorker [{name}] crashed: {err}. Auto-restarting in 3s...", exc_info=True)
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global exchange_instance, bot_tasks
    print("[INIT] Initializing Crypto Trader ccxt.pro Instance...", flush=True)
    try:
        exchange_instance = ccxtpro.cryptocom(
            {
                "apiKey": keys.get("CRYPTO_COM_API_KEY", ""),
                "secret": keys.get("CRYPTO_COM_SECRET_KEY", ""),
                "enableRateLimit": True,
                "timeout": 10000,
                "verbose": False,
            }
        )
        exchange_instance.has["fetchCurrencies"] = False
        app.state.exchange_instance = exchange_instance

        try:
            await exchange_instance.load_markets()
            print("[INIT] Market structures loaded successfully.", flush=True)
        except Exception as e:
            print(f"[INIT NOTE] Market init note: {e}", flush=True)

        # Reconciliation hold: start market feeds only, no order/override/TWAP workers.

        for symbol in WATCHER_SYMBOLS:
            symbol = symbol.strip()
            bot_tasks.append(
                asyncio.create_task(resilient_worker(watch_symbol_loop, exchange_instance, symbol, name=f"WatchLoop_{symbol}"))
            )
    except Exception as init_err:
        import traceback
        print(f"[ERROR] Lifespan init failed: {init_err}", flush=True)
        traceback.print_exc()

    yield

    print("[SHUTDOWN] Shutting down Crypto Trader Daemon", flush=True)
    for task in bot_tasks:
        task.cancel()
    if bot_tasks:
        await asyncio.gather(*bot_tasks, return_exceptions=True)
    bot_tasks.clear()
    if exchange_instance:
        try:
            await exchange_instance.close()
        except Exception:
            pass
    if tech_engine:
        try:
            await tech_engine.close()
        except Exception:
            pass



TRUSTED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8080"]

async def reject_crypto_mutation():
    raise HTTPException(status_code=503, detail=execution_status())

app = FastAPI(title="Unified HFT Crypto Trader", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=TRUSTED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Real-Time Orderbook WebSocket Endpoints (Port 8007) ---
@app.websocket("/ws/orderbook")
async def websocket_orderbook_feed(websocket: WebSocket):
    """Real-time WebSocket market orderbook feed across all active trading pairs."""
    await ws_manager.connect(websocket)
    try:
        # Emit initial snapshots for all cached symbols
        for sym, ob in list(latest_orderbooks.items()):
            await ws_manager.broadcast_orderbook(sym, ob)
        while True:
            # Maintain connection and listen for heartbeat / ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"[WS] Connection closed: {e}")
        await ws_manager.disconnect(websocket)


@app.websocket("/ws/orderbook/{symbol:path}")
async def websocket_orderbook_symbol(websocket: WebSocket, symbol: str):
    """Dedicated low-latency WebSocket orderbook stream for a specific pair (e.g. CRO-USD or CRO/USD)."""
    norm_sym = symbol.replace("-", "/").replace("%2F", "/").replace("%2f", "/").upper()
    await ws_manager.connect(websocket, symbol=norm_sym)
    try:
        if norm_sym in latest_orderbooks:
            await ws_manager.broadcast_orderbook(norm_sym, latest_orderbooks[norm_sym])
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"[WS] Connection closed on {symbol}: {e}")
        await ws_manager.disconnect(websocket)


@app.get("/api/v1/orderbook/{symbol:path}")
async def get_orderbook_snapshot_endpoint(symbol: str):
    """HTTP REST fallback snapshot of current orderbook depth and mid-price."""
    norm_sym = symbol.replace("-", "/").replace("%2F", "/").replace("%2f", "/").upper()
    if norm_sym in latest_orderbooks:
        ob = latest_orderbooks[norm_sym]
        bids = ob.get("bids", [])[:20]
        asks = ob.get("asks", [])[:20]
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        mid = round((best_bid + best_ask) / 2.0, 5) if (best_bid and best_ask) else None
        spread = round(best_ask - best_bid, 5) if (best_bid and best_ask) else None
        return {
            "status": "success",
            "symbol": norm_sym,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid,
            "spread": spread,
            "bids": bids,
            "asks": asks,
            "timestamp": time.time()
        }
    return {
        "status": "initializing",
        "symbol": norm_sym,
        "message": "Orderbook feed streaming. Snapshot will be ready momentarily."
    }


@app.get("/api/v1/orderbooks")
async def get_all_orderbooks_snapshot():
    """Returns snapshots for all actively monitored market orderbooks."""
    res = {}
    for sym, ob in latest_orderbooks.items():
        bids = ob.get("bids", [])[:10]
        asks = ob.get("asks", [])[:10]
        res[sym] = {
            "best_bid": bids[0][0] if bids else None,
            "best_ask": asks[0][0] if asks else None,
            "bids": bids,
            "asks": asks,
        }
    return {"status": "success", "orderbooks": res, "count": len(res), "timestamp": time.time()}


@app.get("/api/v1/ledger")
async def get_ledger():
    return load_ledger()


@app.get("/healthz")
async def healthz():
    # Local liveness must not call private exchange endpoints or read the ledger.
    return {"status": "alive", **execution_status()}


@app.get("/api/v1/telemetry")
@app.get("/api/crypto/telemetry")
async def get_telemetry():
    elapsed_min = max(0.05, (time.time() - hunting_eval_start) / 60.0)
    return {
        "status": "held", **execution_status(), "usd_balance": None,
        "balance_source": "unverified", "ledger": load_ledger(),
        "hunting_rate_per_min": round(hunting_eval_counter / elapsed_min),
        "trade_usd_amount": TRADE_USD_AMOUNT, "take_profit_pct": TAKE_PROFIT_PCT,
        "buy_dip_pct": DCA_DIP_PCT, "action_cooldown_sec": ACTION_COOLDOWN_SEC,
    }


@app.post("/api/crypto/set-parameters", dependencies=[Depends(reject_crypto_mutation)])
@app.post("/api/v1/settings", dependencies=[Depends(reject_crypto_mutation)])
@app.post("/settings", dependencies=[Depends(reject_crypto_mutation)])
async def set_parameters(payload: dict):
    global TRADE_USD_AMOUNT, TAKE_PROFIT_PCT, DCA_DIP_PCT, MACRO_SUPPORT_CEILING, COMPOUND_EVERY_X_TRADES, MIN_COMPOUND_USD, ACTION_COOLDOWN_SEC, FAST_SCALP_WINDOW_SEC
    if "trade_usd_amount" in payload:
        TRADE_USD_AMOUNT = max(1.0, float(payload["trade_usd_amount"]))
    elif "TRADE_USD_AMOUNT" in payload:
        TRADE_USD_AMOUNT = max(1.0, float(payload["TRADE_USD_AMOUNT"]))
        
    if "take_profit_pct" in payload:
        TAKE_PROFIT_PCT = float(payload["take_profit_pct"]) / 100.0 if float(payload["take_profit_pct"]) > 0.5 else float(payload["take_profit_pct"])
    elif "TAKE_PROFIT_PCT" in payload:
        TAKE_PROFIT_PCT = float(payload["TAKE_PROFIT_PCT"]) / 100.0 if float(payload["TAKE_PROFIT_PCT"]) > 0.5 else float(payload["TAKE_PROFIT_PCT"])
        
    if "buy_dip_pct" in payload:
        DCA_DIP_PCT = float(payload["buy_dip_pct"]) / 100.0 if float(payload["buy_dip_pct"]) > 0.5 else float(payload["buy_dip_pct"])
    elif "BUY_DIP_PCT" in payload:
        DCA_DIP_PCT = float(payload["BUY_DIP_PCT"]) / 100.0 if float(payload["BUY_DIP_PCT"]) > 0.5 else float(payload["BUY_DIP_PCT"])
        
    if "macro_support_ceiling" in payload:
        MACRO_SUPPORT_CEILING = float(payload["macro_support_ceiling"])
    elif "MACRO_SUPPORT_CEILING" in payload:
        MACRO_SUPPORT_CEILING = float(payload["MACRO_SUPPORT_CEILING"])

    if "compound_every_x_trades" in payload:
        COMPOUND_EVERY_X_TRADES = max(1, int(payload["compound_every_x_trades"]))
    elif "COMPOUND_EVERY_X_TRADES" in payload:
        COMPOUND_EVERY_X_TRADES = max(1, int(payload["COMPOUND_EVERY_X_TRADES"]))

    if "min_compound_usd" in payload:
        MIN_COMPOUND_USD = max(1.0, float(payload["min_compound_usd"]))
    elif "MIN_COMPOUND_USD" in payload:
        MIN_COMPOUND_USD = max(1.0, float(payload["MIN_COMPOUND_USD"]))

    if "action_cooldown_sec" in payload:
        ACTION_COOLDOWN_SEC = max(0.1, float(payload["action_cooldown_sec"]))
    elif "ACTION_COOLDOWN_SEC" in payload:
        ACTION_COOLDOWN_SEC = max(0.1, float(payload["ACTION_COOLDOWN_SEC"]))

    if "fast_scalp_window_sec" in payload:
        FAST_SCALP_WINDOW_SEC = max(10, int(payload["fast_scalp_window_sec"]))
    elif "FAST_SCALP_WINDOW_SEC" in payload:
        FAST_SCALP_WINDOW_SEC = max(10, int(payload["FAST_SCALP_WINDOW_SEC"]))
        
    return {
        "status": "success",
        "trade_usd_amount": TRADE_USD_AMOUNT,
        "take_profit_pct": TAKE_PROFIT_PCT,
        "buy_dip_pct": DCA_DIP_PCT,
        "macro_support_ceiling": MACRO_SUPPORT_CEILING,
        "compound_every_x_trades": COMPOUND_EVERY_X_TRADES,
        "min_compound_usd": MIN_COMPOUND_USD,
        "action_cooldown_sec": ACTION_COOLDOWN_SEC,
        "fast_scalp_window_sec": FAST_SCALP_WINDOW_SEC,
        "BUY_DIP_PCT": DCA_DIP_PCT,
        "TAKE_PROFIT_PCT": TAKE_PROFIT_PCT,
        "TRADE_USD_AMOUNT": TRADE_USD_AMOUNT,
        "MAX_POSITION_USD": 50.0,
        "COMPOUND_EVERY_X_TRADES": COMPOUND_EVERY_X_TRADES,
    }


@app.get("/api/v1/settings")
@app.get("/settings")
async def get_settings():
    return {
        "BUY_DIP_PCT": DCA_DIP_PCT,
        "TAKE_PROFIT_PCT": TAKE_PROFIT_PCT,
        "TRADE_USD_AMOUNT": TRADE_USD_AMOUNT,
        "MAX_POSITION_USD": 50.0,
        "MACRO_SUPPORT_CEILING": MACRO_SUPPORT_CEILING,
        "COMPOUND_EVERY_X_TRADES": COMPOUND_EVERY_X_TRADES,
        "MIN_COMPOUND_USD": MIN_COMPOUND_USD,
    }


@app.get("/api/crypto/cro/predict")
async def get_cro_prediction():
    raise HTTPException(status_code=503, detail="Prediction unavailable; historical ledger is unreconciled")


@app.post("/api/v1/trigger_override", dependencies=[Depends(reject_crypto_mutation)])
async def trigger_override(payload: dict):
    # Expects {"action": "MARKET_BUY", "symbol": "BTC/USD"}
    action = payload.get("action")
    symbol = payload.get("symbol")
    if action and symbol:
        override_signals.append((action, symbol))
        return {"status": "accepted", "message": f"Override {action} {symbol} queued."}
    return {"status": "error", "message": "Invalid payload"}


@app.post("/api/v1/drip_trade", dependencies=[Depends(reject_crypto_mutation)])
async def start_drip_trade(payload: dict):
    symbol = payload.get("symbol")
    total_usd = float(payload.get("total_usd", 0))
    drip_interval_seconds = int(payload.get("drip_interval_seconds", 3600))
    drip_size_usd = float(payload.get("drip_size_usd", 0))
    
    if not symbol or total_usd <= 0 or drip_size_usd <= 0:
        return {"status": "error", "message": "Invalid parameters"}
        
    ledger = load_ledger()
    if "twap_orders" not in ledger:
        ledger["twap_orders"] = []
        
    twap_order = {
        "symbol": symbol,
        "total_usd": total_usd,
        "remaining_usd": total_usd,
        "drip_interval_seconds": drip_interval_seconds,
        "drip_size_usd": drip_size_usd,
        "last_drip_time": 0  # 0 triggers immediately on next loop
    }
    
    ledger["twap_orders"].append(twap_order)
    save_ledger(ledger)
    return {"status": "accepted", "message": f"TWAP Drip started for {symbol}. Total: ${total_usd}"}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8007,
        log_level="info",
    )

