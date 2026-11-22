import ccxt
import time
from pathlib import Path

ENV_FILE = Path('C:/Users/footb/AI-BS_Matrix/.env')
keys = {}
if ENV_FILE.exists():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                keys[k] = v

try:
    # 1. Fetch server time using public API
    exchange_pub = ccxt.cryptocom()
    ticker = exchange_pub.fetch_ticker('BTC/USDT')
    server_time = ticker['timestamp']
    local_time = int(time.time() * 1000)
    diff = server_time - local_time
    print(f'Server Time: {server_time}')
    print(f'Local Time : {local_time}')
    print(f'Difference : {diff} ms')

    # 2. Authenticated call
    exchange = ccxt.cryptocom({
        'apiKey': keys.get('CRYPTO_COM_API_KEY', ''),
        'secret': keys.get('CRYPTO_COM_SECRET_KEY', ''),
        'enableRateLimit': True,
    })
    # Sync nonce to server time
    exchange.nonce = lambda: int(time.time() * 1000) + diff
    print('Testing Synced Nonce:', exchange.nonce())
    
    balance = exchange.fetch_balance()
    non_zero = {k: v for k, v in balance.get('total', {}).items() if v > 0}
    print(f'Success with Synced Nonce: {non_zero}')
except Exception as e:
    print(f'Error: {e}')
