"""
Agent 2: Orderbook Scout & Depth Matrix Daemon
AI-BS Multi-Agent Crypto Pod - Intelligence Layer

Role:
- Queries public/get-book for CRO_USDT at 1.0s intervals via IPv4 socket.
- Analyzes L2 orderbook depth within +/- 1.5% of mid-price.
- Computes Depth Imbalance / Skew (Bid Volume vs Ask Volume).
- Detects significant Buy Support Shelves and Ask Resistance Walls.
- Emits real-time market microstructure signals to C:\\AI-BS\\saved_data\\orderbook_scout_signals.json
  so Agent 1 (Execution Engine) never places bids beneath sudden ask walls or buys into falling knives.
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import http.client
from datetime import datetime, timezone
from decimal import Decimal

INSTRUMENT = "CRO_USDT"
OUTPUT_SIGNAL_PATH = r"C:\AI-BS\saved_data\orderbook_scout_signals.json"
POLL_INTERVAL_SEC = 1.0
DEPTH_LEVELS = 50  # Deep orderbook inspection

class IPv4HTTPSConnection(http.client.HTTPSConnection):
    """Pin DNS queries to IPv4 socket (AF_INET) to avoid IPv6 whitelist rejection."""
    def connect(self) -> None:
        err = None
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, _, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    self.sock.settimeout(self.timeout)
                self.sock.connect(sa)
                break
            except OSError as e:
                err = e
                if self.sock:
                    self.sock.close()
        if err is not None and not getattr(self, "sock", None):
            raise err
        if self._tunnel_host:
            self._tunnel()
        server_hostname = self._tunnel_host if self._tunnel_host else self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)

def fetch_l2_book() -> dict:
    conn = IPv4HTTPSConnection("api.crypto.com", 443, timeout=3)
    try:
        conn.request("GET", f"/exchange/v1/public/get-book?instrument_name={INSTRUMENT}&depth={DEPTH_LEVELS}")
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        if parsed.get("code") == 0:
            return parsed.get("result", {}).get("data", [{}])[0]
    except Exception as e:
        pass
    finally:
        conn.close()
    return {}

def analyze_depth(data: dict) -> dict:
    bids = data.get("bids", [])
    asks = data.get("asks", [])
    if not bids or not asks:
        return {}

    best_bid = Decimal(str(bids[0][0]))
    best_ask = Decimal(str(asks[0][0]))
    mid_price = (best_bid + best_ask) / Decimal("2")
    spread = best_ask - best_bid
    spread_bps = (spread / mid_price) * Decimal("10000")

    # Analyze depth within +/- 1.5%
    lower_bound = mid_price * Decimal("0.985")
    upper_bound = mid_price * Decimal("1.015")

    total_bid_qty = Decimal("0")
    total_bid_val = Decimal("0")
    max_bid_shelf_qty = Decimal("0")
    max_bid_shelf_price = Decimal("0")

    for level in bids:
        p = Decimal(str(level[0]))
        q = Decimal(str(level[1]))
        if p >= lower_bound:
            total_bid_qty += q
            total_bid_val += (p * q)
            if q > max_bid_shelf_qty:
                max_bid_shelf_qty = q
                max_bid_shelf_price = p

    total_ask_qty = Decimal("0")
    total_ask_val = Decimal("0")
    max_ask_wall_qty = Decimal("0")
    max_ask_wall_price = Decimal("0")

    for level in asks:
        p = Decimal(str(level[0]))
        q = Decimal(str(level[1]))
        if p <= upper_bound:
            total_ask_qty += q
            total_ask_val += (p * q)
            if q > max_ask_wall_qty:
                max_ask_wall_qty = q
                max_ask_wall_price = p

    # Depth Imbalance Ratio: (Bids - Asks) / (Bids + Asks)
    tot = total_bid_qty + total_ask_qty
    imbalance = (total_bid_qty - total_ask_qty) / tot if tot > 0 else Decimal("0")

    # Classification
    if imbalance > Decimal("0.20"):
        regime = "STRONG_BID_SUPPORT"
        action_bias = "BULLISH_AGGRESSIVE"
    elif imbalance < Decimal("-0.20"):
        regime = "HEAVY_ASK_RESISTANCE"
        action_bias = "DEFENSIVE_HOLD"
    else:
        regime = "BALANCED_SPREAD"
        action_bias = "NEUTRAL_SCALP"

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "instrument": INSTRUMENT,
        "mid_price": float(mid_price),
        "best_bid": float(best_bid),
        "best_ask": float(best_ask),
        "spread_usdt": float(spread),
        "spread_bps": float(spread_bps),
        "window_1_5pct": {
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "total_bid_cro": float(total_bid_qty),
            "total_bid_usdt": float(total_bid_val),
            "total_ask_cro": float(total_ask_qty),
            "total_ask_usdt": float(total_ask_val),
            "depth_imbalance": float(imbalance)
        },
        "key_levels": {
            "major_bid_support_price": float(max_bid_shelf_price),
            "major_bid_support_qty": float(max_bid_shelf_qty),
            "major_ask_wall_price": float(max_ask_wall_price),
            "major_ask_wall_qty": float(max_ask_wall_qty)
        },
        "market_regime": regime,
        "action_bias": action_bias,
        "safe_buy_ceiling": float(min(best_bid, max_ask_wall_price - Decimal("0.00002")) if max_ask_wall_price > 0 else float(best_bid))
    }

def main():
    os.makedirs(r"C:\AI-BS\saved_data", exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent 2 (Depth Scout) started. Polling L2 depth at {POLL_INTERVAL_SEC}s...", flush=True)

    while True:
        try:
            data = fetch_l2_book()
            if data:
                signals = analyze_depth(data)
                if signals:
                    tmp = OUTPUT_SIGNAL_PATH + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(signals, f, indent=2)
                    os.replace(tmp, OUTPUT_SIGNAL_PATH)
        except Exception as e:
            pass
        time.sleep(POLL_INTERVAL_SEC)

if __name__ == "__main__":
    main()
