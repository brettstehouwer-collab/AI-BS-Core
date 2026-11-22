import asyncio
import os
import sys
import json
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
    return {}

def save_ledger(ledger):
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

async def set_initial_dip_buy():
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
    # Dip target: 4.2% below entry of 0.06063
    dip_price = 0.05808
    dip_amount = 18.0  # 18 * 0.05808 = $1.045 USD (above $1.00 min)
    
    try:
        await exchange.load_markets()
        print(f"Placing Limit Buy Order: {dip_amount} {symbol} @ ${dip_price:.5f} (Cost: ${dip_amount * dip_price:.2f})")
        
        order = await exchange.create_limit_buy_order(symbol, dip_amount, dip_price)
        order_id = order.get('id')
        print(f"[SUCCESS] Limit order placed on Crypto.com! Order ID: {order_id}")
        
        ledger = load_ledger()
        if "pending_dip_buys" not in ledger:
            ledger["pending_dip_buys"] = {}
            
        ledger["pending_dip_buys"][symbol] = {
            "dip_target_price": dip_price,
            "allocated_usd": round(dip_amount * dip_price, 2),
            "buy_amount": dip_amount,
            "limit_order_id": order_id,
            "status": "resting_limit",
            "notes": "Pre-set 4.2% dip buy for active scalp position"
        }
        ledger["last_action"] = f"LIMIT_DIP_BUY_SET {symbol}: {dip_amount} CRO @ ${dip_price:.5f}"
        save_ledger(ledger)
        print("Ledger updated with pending dip buy.")
        
        log_trade_entry(
            trade_type="LIMIT_ORDER",
            price=dip_price,
            amount=dip_amount,
            symbol=symbol,
            strategy_trigger="INITIAL_DIP_ORDER_PLACED",
            notes=f"Resting 4.2% dip buy limit order on Crypto.com (Order ID: {order_id})"
        )
        print("Recorded in cro_quantitative_ledger.db.")
        
    except Exception as e:
        print(f"[ERROR] Failed to place limit order: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(set_initial_dip_buy())
