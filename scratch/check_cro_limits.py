import asyncio
import ccxt.pro as ccxtpro
import json

async def main():
    e = ccxtpro.cryptocom()
    await e.load_markets()
    m = e.markets.get("CRO/USD", {})
    print("Limits:", json.dumps(m.get("limits"), indent=2))
    print("Precision:", json.dumps(m.get("precision"), indent=2))
    await e.close()

if __name__ == "__main__":
    asyncio.run(main())
