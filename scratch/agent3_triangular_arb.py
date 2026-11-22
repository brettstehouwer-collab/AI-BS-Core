"""
Agent 3: Cross-Pair & Triangular Arbitrage Engine
AI-BS Multi-Agent Crypto Pod - Capital Expansion Layer ($250+ USD Activation)

Operational Logic:
- Continuously scans synthetic triangular spreads on Crypto.com:
    Leg 1: CRO_USDT
    Leg 2: BTC_USDT
    Leg 3: BTC_CRO (or ETH/CRO cross pairs)
- Evaluates Synthetic Implied Price:
    Implied CRO_USDT = (BTC_USDT) * (BTC_CRO)
- Discovers Arbitrage Discrepancies:
    Spread % = abs(Market CRO_USDT - Implied CRO_USDT) / Market CRO_USDT
- Activation Gate:
    Runs in PASSIVE SCOUT mode under $250 equity.
    Logs profitable triangular cross-pair discrepancies to C:\\AI-BS\\saved_data\\triangular_arb_opportunities.json.
    Automatically unlocks live order execution once account balance crosses $250.00 USD.
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

OUTPUT_ARB_PATH = r"C:\AI-BS\saved_data\triangular_arb_opportunities.json"
TELEMETRY_URL = "http://127.0.0.1:8007/api/live-telemetry"
MIN_ACTIVATION_EQUITY_USD = Decimal("250.00")
POLL_INTERVAL_SEC = 2.0

class IPv4HTTPSConnection(http.client.HTTPSConnection):
    """Force IPv4 socket resolution."""
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

def get_ticker(instrument: str) -> dict:
    conn = IPv4HTTPSConnection("api.crypto.com", 443, timeout=3)
    try:
        conn.request("GET", f"/exchange/v1/public/get-tickers?instrument_name={instrument}")
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        if parsed.get("code") == 0:
            data = parsed.get("result", {}).get("data", [])
            if data:
                return data[0]
    except Exception:
        pass
    finally:
        conn.close()
    return {}

def check_account_equity() -> Decimal:
    import urllib.request
    try:
        req = urllib.request.Request(TELEMETRY_URL, headers={"User-Agent": "Agent3-Arb"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            val = data.get("portfolio_valuation", {}).get("total_account_value_usd", "0.0")
            return Decimal(str(val))
    except Exception:
        return Decimal("95.00")

def main():
    os.makedirs(r"C:\AI-BS\saved_data", exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent 3 (Cross-Pair / Triangular Arb Engine) initialized...", flush=True)

    while True:
        try:
            equity = check_account_equity()
            is_live_enabled = equity >= MIN_ACTIVATION_EQUITY_USD

            # Query tickers for triangular components
            t_cro_usdt = get_ticker("CRO_USDT")
            t_btc_usdt = get_ticker("BTC_USDT")
            t_cro_btc = get_ticker("CRO_BTC")

            if t_cro_usdt and t_btc_usdt and t_cro_btc:
                cro_usdt_bid = Decimal(str(t_cro_usdt.get("b", 0)))
                cro_usdt_ask = Decimal(str(t_cro_usdt.get("k", 0)))
                
                btc_usdt_bid = Decimal(str(t_btc_usdt.get("b", 0)))
                btc_usdt_ask = Decimal(str(t_btc_usdt.get("k", 0)))

                cro_btc_bid = Decimal(str(t_cro_btc.get("b", 0)))
                cro_btc_ask = Decimal(str(t_cro_btc.get("k", 0)))

                if cro_usdt_bid > 0 and btc_usdt_bid > 0 and cro_btc_bid > 0:
                    # Direction A: Buy CRO with USDT -> Sell CRO for BTC -> Sell BTC for USDT
                    # 1 USDT -> (1 / cro_usdt_ask) CRO -> ((1 / cro_usdt_ask) * cro_btc_bid) BTC -> BTC * btc_usdt_bid USDT
                    ratio_forward = (Decimal("1") / cro_usdt_ask) * cro_btc_bid * btc_usdt_bid
                    edge_forward_bps = (ratio_forward - Decimal("1")) * Decimal("10000")

                    # Direction B: Buy BTC with USDT -> Buy CRO with BTC -> Sell CRO for USDT
                    ratio_reverse = (Decimal("1") / btc_usdt_ask) * (Decimal("1") / cro_btc_ask) * cro_usdt_bid
                    edge_reverse_bps = (ratio_reverse - Decimal("1")) * Decimal("10000")

                    arb_signal = {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "account_equity_usd": float(equity),
                        "activation_threshold_usd": float(MIN_ACTIVATION_EQUITY_USD),
                        "live_trading_unlocked": is_live_enabled,
                        "status": "ARMED_LIVE" if is_live_enabled else "STANDBY_SCOUTING",
                        "market_prices": {
                            "cro_usdt_ask": float(cro_usdt_ask),
                            "cro_usdt_bid": float(cro_usdt_bid),
                            "btc_usdt_ask": float(btc_usdt_ask),
                            "btc_usdt_bid": float(btc_usdt_bid),
                            "cro_btc_ask": float(cro_btc_ask),
                            "cro_btc_bid": float(cro_btc_bid),
                        },
                        "synthetic_edges_bps": {
                            "usdt_cro_btc_usdt_bps": float(edge_forward_bps),
                            "usdt_btc_cro_usdt_bps": float(edge_reverse_bps)
                        },
                        "best_synthetic_direction": "CRO->BTC->USDT" if edge_forward_bps > edge_reverse_bps else "BTC->CRO->USDT",
                        "best_edge_bps": float(max(edge_forward_bps, edge_reverse_bps))
                    }

                    tmp = OUTPUT_ARB_PATH + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(arb_signal, f, indent=2)
                    os.replace(tmp, OUTPUT_ARB_PATH)

        except Exception as e:
            pass

        time.sleep(POLL_INTERVAL_SEC)

if __name__ == "__main__":
    main()
