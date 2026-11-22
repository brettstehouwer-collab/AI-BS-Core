import requests
import json

def analyze_crypto_com():
    url = "https://api.crypto.com/v2/public/get-ticker"
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to fetch data")
        return
        
    data = response.json()
    if 'result' not in data or 'data' not in data['result']:
        print("Invalid response")
        return
        
    tickers = data['result']['data']
    
    usd_pairs = []
    usdt_pairs = []
    btc_pairs = []
    
    for t in tickers:
        inst = t.get('i', '')
        # t['c'] is 24h price change, t['v'] is volume, t['h'] high, t['l'] low
        # Volatility could be measured by (High - Low) / Low
        high = float(t.get('h', 0))
        low = float(t.get('l', 0))
        if low <= 0 or high <= 0:
            continue
            
        volatility = (high - low) / low
        volume = float(t.get('v', 0)) * float(t.get('a', 0)) # approx quote volume
        
        item = {
            'instrument': inst,
            'volatility': volatility * 100,
            'volume': volume
        }
        
        if inst.endswith('_USD'):
            usd_pairs.append(item)
        elif inst.endswith('_USDT'):
            usdt_pairs.append(item)
        elif inst.endswith('_BTC'):
            btc_pairs.append(item)
            
    # Sort by volatility
    usd_pairs = sorted(usd_pairs, key=lambda x: x['volatility'], reverse=True)
    usdt_pairs = sorted(usdt_pairs, key=lambda x: x['volatility'], reverse=True)
    
    print("--- TOP 10 VOLATILE USD PAIRS (Good for your bot) ---")
    for p in usd_pairs[:10]:
        print(f"{p['instrument']}: Volatility {p['volatility']:.2f}% | Vol: ${p['volume']:,.0f}")
        
    print("\n--- TOP 10 VOLATILE USDT PAIRS ---")
    for p in usdt_pairs[:10]:
        print(f"{p['instrument']}: Volatility {p['volatility']:.2f}% | Vol: ${p['volume']:,.0f}")
        
    print(f"\nTotal USD pairs: {len(usd_pairs)}")
    print(f"Total USDT pairs: {len(usdt_pairs)}")

if __name__ == '__main__':
    analyze_crypto_com()
