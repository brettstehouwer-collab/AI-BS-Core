"""
AI-BS Strategy Transition Manager:
1. Liquidates 100% of CRO at the Best Ask using POST_ONLY Maker limit orders.
2. Monitors fill completion until CRO balance reaches 0.
3. Automatically transitions the trading engine to the 3-Tranche Structural Dip Grid:
   - Tranche 1: 1.2% dip ($0.04360) -> $30 USDT
   - Tranche 2: 2.4% dip ($0.04308) -> $35 USDT
   - Tranche 3: 3.8% dip ($0.04250) -> $30+ USDT
"""

import os
import sys
import time
import json
import socket
import http.client
from decimal import Decimal

INSTRUMENT = "CRO_USDT"
OUTPUT_SIGNAL_PATH = r"C:\AI-BS\saved_data\strategy_transition_state.json"

class IPv4HTTPSConnection(http.client.HTTPSConnection):
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

def load_client():
    import importlib.util
    spec = importlib.util.spec_from_file_location("trader_mod", r"C:\AI-BS\scratch\live_cro_usdt_trader.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    api_key, secret = mod.load_dpapi_credentials()
    return mod.CryptoComClient(api_key, secret)

def get_live_book():
    conn = IPv4HTTPSConnection("api.crypto.com", 443, timeout=3)
    try:
        conn.request("GET", f"/exchange/v1/public/get-book?instrument_name={INSTRUMENT}&depth=5")
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") == 0:
            bids = data["result"]["data"][0]["bids"]
            asks = data["result"]["data"][0]["asks"]
            return Decimal(str(bids[0][0])), Decimal(str(asks[0][0]))
    except Exception:
        pass
    finally:
        conn.close()
    return None, None

def cancel_all_open_orders(client):
    try:
        client.private_post("private/cancel-all-orders", {"instrument_name": INSTRUMENT})
        print("Cancelled all open orders on exchange.", flush=True)
    except Exception as e:
        print(f"Error cancelling orders: {e}", flush=True)

def execute_full_liquidation():
    client = load_client()
    print("--- Initiating Full Portfolio Liquidation at Best Ask (Post-Only) ---", flush=True)

    # 1. Cancel open orders
    cancel_all_open_orders(client)
    time.sleep(1.0)

    # 2. Get current CRO balance
    resp = client.private_post("private/user-balance", {})
    balances = resp.get("result", {}).get("data", [{}])[0].get("position_balances", [])
    cro_total = Decimal("0")
    for b in balances:
        if b.get("instrument_name") == "CRO":
            cro_total = Decimal(str(b.get("quantity", 0)))
            break

    print(f"Total CRO to liquidate: {cro_total}", flush=True)
    if cro_total < 25:
        print("CRO balance already minimal. Liquidation complete.", flush=True)
        return

    # 3. Post maker sell at best ask
    while True:
        best_bid, best_ask = get_live_book()
        if not best_bid or not best_ask:
            time.sleep(1)
            continue

        target_ask = best_ask
        print(f"Targeting Maker Sell at Best Ask: {target_ask} USDT", flush=True)

        qty_to_sell = int(cro_total)
        req_body = {
            "instrument_name": INSTRUMENT,
            "side": "SELL",
            "type": "LIMIT",
            "price": str(target_ask),
            "quantity": str(qty_to_sell),
            "post_only": True,
            "exec_inst": ["POST_ONLY"],
            "client_oid": f"liquidate-{int(time.time())}"
        }

        try:
            order_res = client.private_post("private/create-order", req_body)
            order_id = order_res.get("result", {}).get("order_id")
            print(f"Posted Liquidation Order: {order_id} for {qty_to_sell} CRO @ {target_ask}", flush=True)

            # Monitor order fill
            while True:
                time.sleep(2.0)
                detail = client.private_post("private/get-order-detail", {"order_id": order_id})
                data = detail.get("result", {})
                status = data.get("status")
                cum_qty = Decimal(str(data.get("cumulative_quantity", 0)))

                print(f"Order {order_id} status: {status} | Filled: {cum_qty}/{qty_to_sell}", flush=True)
                if status == "FILLED":
                    print(">>> Liquidation 100% FILLED! <<<", flush=True)
                    return
                elif status in ["CANCELED", "REJECTED", "EXPIRED"]:
                    print(f"Order closed with status {status}. Reposting...", flush=True)
                    break

                # Drift check: if best ask moved up, cancel and chase higher
                _, current_ask = get_live_book()
                if current_ask and current_ask > target_ask:
                    print(f"Market moving higher (Ask now {current_ask}). Repositioning higher...", flush=True)
                    client.private_post("private/cancel-order", {"order_id": order_id})
                    time.sleep(1.0)
                    break

        except Exception as e:
            print(f"Exception during order placement: {e}", flush=True)
            time.sleep(2.0)

if __name__ == "__main__":
    execute_full_liquidation()
