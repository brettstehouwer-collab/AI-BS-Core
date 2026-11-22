import asyncio
import os
import sys
import json
import time
from pathlib import Path
import ccxt.pro as ccxtpro
from dotenv import load_dotenv

sys.path.append(r"C:\AI-BS\backend")
from crypto_trader_bot import decrypt_vault_key
from core.cro_quantitative_ledger import log_trade_entry

LEDGER_FILE = Path(r"C:\AI-BS\backend\crypto_ledger.json")

def load_ledger():
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            return json.load(f)
    return {
        "positions": {},
        "twap_orders": [],
        "reference_prices": {},
        "total_profit_usd": 0.0,
        "last_action": "initialized",
        "strategy_layer": "Market Making",
    }

def save_ledger(ledger):
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

async def execute_buy():
    load_dotenv(r"C:\AI-BS\backend\.env", override=True)
    keys = {}
    with open(r"C:\AI-BS\backend\.env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                keys[k] = decrypt_vault_key(v.strip('"'))
                
    api_key = keys.get("CRYPTO_COM_API_KEY")
    secret = keys.get("CRYPTO_COM_SECRET_KEY")
    
    exchange = ccxtpro.cryptocom({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
    })
    
    symbol = "CRO/USD"
    trade_usd = 1.00
    
    try:
        print("[1] Loading markets...")
        await exchange.load_markets()
        
        print(f"[2] Fetching ticker for {symbol}...")
        ticker = await exchange.fetch_ticker(symbol)
        ask = ticker.get('ask') or ticker.get('last')
        print(f"Current Ask Price: {ask}")
        
        if not ask or ask <= 0:
            print("[ERROR] Invalid ask price")
            return
            
        # Minimum whole CRO amount to cover >= $1.00 USD
        raw_amt = trade_usd / ask
        buy_amt = float(exchange.amount_to_precision(symbol, raw_amt))
        if buy_amt * ask < 1.00:
            buy_amt = float(exchange.amount_to_precision(symbol, buy_amt + 1.0))
            
        est_cost = buy_amt * ask
        print(f"[3] Target Order: Buy {buy_amt} {symbol} at ~${ask:.5f} (Est Cost: ${est_cost:.2f} USD)")
        
        # Check USD balance
        balance = await exchange.fetch_balance()
        usd_free = float(balance.get('USD', {}).get('free', 0.0))
        print(f"Available USD Balance: ${usd_free:.2f}")
        
        if usd_free < est_cost:
            print(f"[ERROR] Insufficient USD balance (${usd_free:.2f} < ${est_cost:.2f})")
            return
            
        print("[4] Submitting Market Buy order to Crypto.com...")
        order = await exchange.create_market_buy_order(symbol, buy_amt)
        print("[SUCCESS] Order response:", json.dumps(order, indent=2, default=str))
        
        fill_price = order.get('price') or ask
        filled_amt = order.get('filled') or buy_amt
        actual_cost = order.get('cost') or (fill_price * filled_amt)
        
        # [5] Update Ledger
        ledger = load_ledger()
        pos = ledger["positions"].get(symbol, {"amount": 0.0, "avg_buy_price": 0.0, "long_term_vault": 4.4579})
        existing_amt = pos.get("amount", 0.0)
        existing_price = pos.get("avg_buy_price", 0.0)
        existing_vault = pos.get("long_term_vault", 4.4579)
        
        new_amt = existing_amt + filled_amt
        total_cost = (existing_price * existing_amt) + (fill_price * filled_amt)
        new_avg_price = total_cost / new_amt if new_amt > 0 else fill_price
        
        ledger["positions"][symbol] = {
            "amount": new_amt,
            "avg_buy_price": new_avg_price,
            "long_term_vault": existing_vault
        }
        ledger["reference_prices"][symbol] = fill_price
        ledger["last_action"] = f"INITIAL_SCALP_ENTRY {symbol}: {filled_amt} CRO @ ${fill_price:.5f} (${actual_cost:.2f})"
        ledger["strategy_layer"] = "Dual Scalp & Long-Term Accumulator (CRO 50c Focus)"
        save_ledger(ledger)
        print(f"[6] Ledger updated: {ledger['positions'][symbol]}")
        
        # [7] Log into Quantitative Ledger DB
        log_trade_entry(
            trade_type="BUY",
            price=fill_price,
            amount=filled_amt,
            symbol=symbol,
            strategy_trigger="USER_INITIATED_SCALP_ENTRY",
            notes=f"Initial $1.00 scalp entry after +6% breakout. Target TP: +2.0% (~${fill_price * 1.02:.5f})"
        )
        print("[7] Trade entry recorded in cro_quantitative_ledger.db")

    except Exception as e:
        print(f"[ERROR] Trade execution failed: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(execute_buy())
