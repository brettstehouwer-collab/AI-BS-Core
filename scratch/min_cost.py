import ccxt

exchange = ccxt.cryptocom()
exchange.load_markets()

pairs = ['XLM/USD', 'ADA/USD', 'PYTH/USD', 'AAVE/USD', 'ARB/USD', 'AVAX/USD', 'DOT/USD', 'NEAR/USD', 'CRO/USD', 'HBAR/USD']

print('\n--- Minimum Order Costs ---')
for pair in pairs:
    if pair in exchange.markets:
        min_cost = exchange.markets[pair]['limits']['cost']['min']
        print(f"{pair}: ${min_cost}")
    else:
        print(f"{pair}: Not Found")
