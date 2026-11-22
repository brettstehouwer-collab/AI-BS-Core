import json
import os
import psutil

state_path = r"C:\AI-BS\saved_data\structural_dip_state.json"
watchdog_path = r"C:\AI-BS\saved_data\agent4_watchdog_status.json"

print("--- CRYPTO ACCOUNT LIVE STATUS ---")
if os.path.exists(state_path):
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Status: {data.get('status')}")
    print(f"Instrument: {data.get('instrument')}")
    print(f"Last Tick UTC: {data.get('last_tick_utc')}")
    pv = data.get("portfolio_valuation", {})
    print(f"Total Account Value: ${pv.get('total_account_value_usd')} USD")
    print(f"CRO Units: {pv.get('cro_units_total')} (Valuation: ${pv.get('cro_valuation_usd')} USD)")
    print(f"Mid Price: ${pv.get('current_mid_price')}")
    print(f"USDT Cash: ${pv.get('usdt_cash_total')}")
    print(f"Cumulative Realized PnL: +${data.get('total_realized_pnl_usdt')} USDT")
    print(f"Profit Reserve: ${data.get('profit_reserve_usdt')} USDT")
    print("\n--- ACTIVE SELL ORDERS ON BOOK ---")
    for o in data.get("active_orders", []):
        print(f"  {o.get('side')} {o.get('quantity')} CRO @ ${o.get('price')} (ID: {o.get('order_id')})")
    print("\n--- OPEN LOTS ---")
    for lot in data.get("open_lots", []):
        print(f"  Tranche {lot.get('tranche_idx')}: {lot.get('qty_cro')} CRO, Entry: ${lot.get('entry_price')}, Target: +{float(lot.get('target_profit_pct', 0))*100:.1f}%")

if os.path.exists(watchdog_path):
    with open(watchdog_path, "r", encoding="utf-8") as f:
        wdata = json.load(f)
    print("\n--- AGENT 4 WATCHDOG ---")
    print(f"Watchdog Status: {wdata.get('watchdog_status')} | Health: {wdata.get('watchdog_health')}")
    cb = wdata.get("circuit_breaker_status", {})
    print(f"Circuit Breaker Tripped: {cb.get('kill_switch_tripped')}")
    print(f"Drawdown: ${cb.get('equity_drawdown_usdt'):.4f} USDT (Cutoff: ${cb.get('max_allowable_drawdown_usdt')})")
    print(f"Agent 1 Online: {wdata.get('agent1_execution_engine_online')}")
