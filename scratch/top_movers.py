import ccxt

exchange = ccxt.cryptocom()
tickers = exchange.fetch_tickers()

movers = []
for symbol, data in tickers.items():
    if not symbol.endswith('/USD') and not symbol.endswith('/USDT'):
        continue
    pct_change = data.get('percentage')
    vol = data.get('quoteVolume')
    if pct_change is not None and vol is not None and vol > 100000:
        movers.append({'symbol': symbol, 'change': pct_change, 'vol': vol})

# Sort by absolute percentage change (fastest moving up or down)
movers.sort(key=lambda x: abs(x['change']), reverse=True)

print('\nTop 10 Fastest Moving Markets (>$100k Vol):')
for i, m in enumerate(movers[:10]):
    direction = '+' if m['change'] > 0 else ''
    print(f"{i+1}. {m['symbol']}: {direction}{m['change']:.2f}% (Vol: ${m['vol']:,.0f})")
