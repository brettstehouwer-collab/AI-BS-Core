import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

exchange = ccxt.cryptocom({
    'apiKey': os.getenv('CRYPTO_COM_API_KEY'),
    'secret': os.getenv('CRYPTO_COM_SECRET_KEY'),
    'enableRateLimit': True
})

try:
    balance = exchange.fetch_balance()
    print('\n--- Current Balances ---')
    for currency, amount in balance['total'].items():
        if amount > 0:
            print(f"{currency}: {amount}")
except Exception as e:
    print(f"Error: {e}")
