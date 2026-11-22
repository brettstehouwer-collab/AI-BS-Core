"""Legacy liquidation utility: disabled pending reconciled execution."""
raise RuntimeError("Liquidation disabled: reconciliation and shared risk controls required")

import ccxt
import time
from pathlib import Path

ENV_FILE = Path('.env')
keys = {}
if ENV_FILE.exists():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                keys[k] = v.strip('"')

try:
    exchange_pub = ccxt.cryptocom()
    diff = exchange_pub.fetch_ticker('BTC/USDT')['timestamp'] - int(time.time() * 1000)
    
    exchange = ccxt.cryptocom({
        'apiKey': keys.get('CRYPTO_COM_API_KEY', ''),
        'secret': keys.get('CRYPTO_COM_SECRET_KEY', ''),
        'enableRateLimit': True,
    })
    exchange.nonce = lambda: int(time.time() * 1000) + diff
    
    # Load markets
    exchange.load_markets()
    markets = exchange.markets.keys()
    
    balance = exchange.fetch_balance()
    totals = balance.get('total', {})
    
    sold_to_usd = 0
    failed_dust = []

    print("--- INITIATING LIQUIDATION TO USD ---")
    
    for coin, amount in totals.items():
        if coin in ['USD'] or amount <= 0:
            continue
            
        # Try to find a USD pair
        symbol_usd = f"{coin}/USD"
        symbol_usdt = f"{coin}/USDT"
        
        target_symbol = None
        if symbol_usd in markets:
            target_symbol = symbol_usd
        elif symbol_usdt in markets:
            target_symbol = symbol_usdt
            
        if not target_symbol:
            print(f"Skipping {coin}: No USD or USDT market found.")
            continue
            
        try:
            # Format amount according to exchange precision limits
            amount_str = exchange.amount_to_precision(target_symbol, amount)
            amount_float = float(amount_str)
            
            if amount_float > 0:
                print(f"Attempting to sell {amount_float} {coin} on {target_symbol}...")
                order = exchange.create_market_sell_order(target_symbol, amount_float)
                print(f"? Successfully sold {coin}!")
                sold_to_usd += 1
            else:
                failed_dust.append(coin)
        except ccxt.InvalidOrder as e:
            # Usually implies order is too small (dust)
            print(f"? Failed to sell {coin} (likely dust): {e}")
            failed_dust.append(coin)
        except Exception as e:
            print(f"? Failed to sell {coin}: {e}")
            failed_dust.append(coin)
            
    # If we accumulated USDT, sell it to USD
    time.sleep(2) # Wait for orders to settle
    final_balance = exchange.fetch_balance()
    usdt_amount = final_balance.get('total', {}).get('USDT', 0)
    if usdt_amount > 0 and 'USDT/USD' in markets:
        try:
            usdt_str = exchange.amount_to_precision('USDT/USD', usdt_amount)
            if float(usdt_str) > 0:
                print(f"Converting {usdt_str} USDT to USD...")
                exchange.create_market_sell_order('USDT/USD', float(usdt_str))
                print(f"? Converted USDT to USD!")
        except Exception as e:
            print(f"? Failed to convert USDT: {e}")

    print("\n--- LIQUIDATION COMPLETE ---")
    usd_balance = exchange.fetch_balance().get('total', {}).get('USD', 0)
    print(f"New USD Balance: ")
    if failed_dust:
        print(f"The following coins could not be sold via API (Dust balances): {', '.join(failed_dust)}")
        
except Exception as e:
    print('Critical Error:', e)
