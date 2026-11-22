import ccxt
from pathlib import Path

ENV_FILE = Path('.env')
keys = {}
if ENV_FILE.exists():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                keys[k] = v

try:
    exchange = ccxt.cryptocom({
        'apiKey': keys.get('CRYPTO_COM_API_KEY', ''),
        'secret': keys.get('CRYPTO_COM_SECRET_KEY', ''),
    })
    balance = exchange.fetch_balance()
    non_zero = {k: v for k, v in balance.get('total', {}).items() if v > 0}
    print(f'Balances: {non_zero}')
except Exception as e:
    print(f'Error: {e}')
