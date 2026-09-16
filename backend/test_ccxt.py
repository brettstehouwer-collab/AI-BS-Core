import asyncio
import os
import sys
import ccxt.pro as ccxtpro
from dotenv import load_dotenv

sys.path.append("C:/AI-BS/backend")
from crypto_trader_bot import decrypt_vault_key

async def run_auth_test():
    load_dotenv("C:/AI-BS/backend/.env", override=True)
    
    keys = {}
    with open("C:/AI-BS/backend/.env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                keys[k] = decrypt_vault_key(v.strip('"'))
                
    api_key = keys.get("CRYPTO_COM_API_KEY")
    secret = keys.get("CRYPTO_COM_SECRET_KEY")
    
    print(f"API Key starting chars: {api_key[:5]}")
    
    exchange = ccxtpro.cryptocom({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
    })
    
    try:
        print("[+] Fetching balance to verify auth...")
        balance = await exchange.fetch_balance()
        usd = balance.get('USD', {}).get('free', 0.0)
        print(f"[SUCCESS] Auth valid. USD Balance: {usd}")
    except Exception as e:
        print(f"[ERROR] Auth failed: {e}")
    finally:
        await exchange.close()

asyncio.run(run_auth_test())
