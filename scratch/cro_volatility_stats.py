import asyncio
import ccxt.pro as ccxtpro
import pandas as pd
import numpy as np
import json
import urllib.request

def get_crypto_com_ticker():
    url = "https://api.crypto.com/v2/public/get-ticker?instrument_name=CRO_USD"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode())
    return data['result']['data'][0]

async def calculate_cro_volatility():
    # Use kraken or binance or cryptocom for daily candles
    exchange = ccxtpro.cryptocom()
    ticker = get_crypto_com_ticker()
    
    current_price = float(ticker['a'])
    high_24h = float(ticker['h'])
    low_24h = float(ticker['l'])
    change_24h_pct = float(ticker['c']) * 100
    spread_24h_pct = ((high_24h - low_24h) / low_24h) * 100
    
    print("=== LIVE CRO TICKER (Crypto.com) ===")
    print(f"Current Price: ${current_price:.5f}")
    print(f"24h High: ${high_24h:.5f}")
    print(f"24h Low: ${low_24h:.5f}")
    print(f"24h Price Change: {change_24h_pct:+.2f}%")
    print(f"24h High-to-Low Volatility Spread: {spread_24h_pct:.2f}%")
    
    # Fetch historical daily candles (past 60-90 days)
    try:
        await exchange.load_markets()
        ohlcv = await exchange.fetch_ohlcv("CRO/USD", "1d", limit=90)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
        df['daily_range_pct'] = ((df['high'] - df['low']) / df['low']) * 100
        
        green_days = df[df['change_pct'] > 0]
        red_days = df[df['change_pct'] < 0]
        
        avg_daily_range = df['daily_range_pct'].mean()
        avg_green_day = green_days['change_pct'].mean()
        avg_red_day = red_days['change_pct'].mean()
        median_daily_range = df['daily_range_pct'].median()
        
        # 14-day ATR %
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean().iloc[-1]
        atr_pct = (atr_14 / current_price) * 100
        
        print("\n=== HISTORICAL VOLATILITY (Past 90 Days) ===")
        print(f"Average Daily Intraday Range (High vs Low): {avg_daily_range:.2f}% (Median: {median_daily_range:.2f}%)")
        print(f"Average Rise on Positive Days: +{avg_green_day:.2f}%")
        print(f"Average Fall on Negative Days: {avg_red_day:.2f}%")
        print(f"14-Day Daily ATR (Average True Range): ${atr_14:.5f} ({atr_pct:.2f}% of price)")
        
    except Exception as e:
        print(f"OHLCV fetch note: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(calculate_cro_volatility())
