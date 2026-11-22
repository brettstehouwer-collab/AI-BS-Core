import ccxt

exchange = ccxt.cryptocom()
exchange.load_markets()

pairs = ['XLM/USD', 'ADA/USD', 'PYTH/USD', 'AAVE/USD', 'ARB/USD', 'AVAX/USD', 'DOT/USD', 'NEAR/USD', 'CRO/USD', 'HBAR/USD']

print('\n--- Minimum Order Amounts ---')
for pair in pairs:
    if pair in exchange.markets:
        min_amt = exchange.markets[pair]['limits']['amount']['min']
        last_price = exchange.fetch_ticker(pair)['last']
        print(f"{pair}: {min_amt} coins (approx ${min_amt * last_price if min_amt and last_price else 'Unknown'})")
    else:
        print(f"{pair}: Not Found")
