import asyncio
import os
import sys
import ccxt.pro as ccxtpro
from dotenv import load_dotenv

sys.path.append(r"C:\AI-BS\backend")
from crypto_trader_bot import decrypt_vault_key

async def check_exchange_status():
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
    
    try:
        print("=== ACCOUNT BALANCES ===")
        balance = await exchange.fetch_balance()
        non_zero = {k: v for k, v in balance.get('total', {}).items() if v and v > 0}
        print("Non-zero balances:", non_zero)
        
        print("\n=== RECENT MY TRADES (CRO/USD) ===")
        try:
            trades = await exchange.fetch_my_trades(symbol="CRO/USD", limit=10)
            if trades:
                for t in trades:
                    print(f"Trade: {t.get('datetime')} | Side: {t.get('side')} | Price: {t.get('price')} | Amount: {t.get('amount')} | Cost: {t.get('cost')}")
            else:
                print("No recent trades returned for CRO/USD.")
        except Exception as e:
            print(f"fetch_my_trades(CRO/USD) note: {e}")
            
        print("\n=== RECENT MY TRADES (CRO/USDT) ===")
        try:
            trades = await exchange.fetch_my_trades(symbol="CRO/USDT", limit=10)
            if trades:
                for t in trades:
                    print(f"Trade: {t.get('datetime')} | Side: {t.get('side')} | Price: {t.get('price')} | Amount: {t.get('amount')} | Cost: {t.get('cost')}")
            else:
                print("No recent trades returned for CRO/USDT.")
        except Exception as e:
            print(f"fetch_my_trades(CRO/USDT) note: {e}")

        print("\n=== RECENT CLOSED ORDERS ===")
        try:
            orders = await exchange.fetch_closed_orders(symbol="CRO/USD", limit=5)
            if orders:
                for o in orders:
                    print(f"Order: {o.get('datetime')} | Status: {o.get('status')} | Side: {o.get('side')} | Price: {o.get('price')} | Amount: {o.get('amount')}")
            else:
                print("No closed orders found for CRO/USD.")
        except Exception as e:
            print(f"fetch_closed_orders note: {e}")
            
        print("\n=== OPEN ORDERS ===")
        try:
            open_orders = await exchange.fetch_open_orders()
            print("Open orders:", open_orders)
        except Exception as e:
            print(f"fetch_open_orders note: {e}")

    except Exception as e:
        print("Error checking exchange:", e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_exchange_status())
