import asyncio
import ccxt.pro as ccxtpro

async def test_keys(api, sec):
    print(f"Testing API: {api[:5]}...")
    exchange = ccxtpro.cryptocom({
        'apiKey': api,
        'secret': sec,
        'enableRateLimit': True,
    })
    try:
        balance = await exchange.fetch_balance()
        usd = balance.get('USD', {}).get('free', 0.0)
        print(f"[SUCCESS] Auth valid. USD Balance: {usd}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False
    finally:
        await exchange.close()

async def main():
    sec = "cxakp_wPcK8F7VHcpqkbCSHyWV8u"
    
    print("--- Test 1 ---")
    res1 = await test_keys("ykuA6Ed1Qdi898mtXv3GRD", sec)
    
    print("\n--- Test 2 ---")
    res2 = await test_keys("iqWyB7nMkLmE4vuaA58V2Y", sec)
    
    if res1 or res2:
        print("\n[+] At least one keypair worked!")
    else:
        print("\n[-] Neither worked.")

asyncio.run(main())
