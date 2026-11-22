import asyncio
import ccxt.pro as ccxtpro
from pathlib import Path

keys = {}
with open("C:/AI-BS/backend/.env", "r") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys[k] = v.strip('"').strip("'")

async def test():
    api_key = keys.get("CRYPTO_COM_API_KEY", "")
    secret = keys.get("CRYPTO_COM_SECRET_KEY", "")
    print(f"API Key prefix: {api_key[:8]}..., len={len(api_key)}")
    print(f"Secret prefix: {secret[:8]}..., len={len(secret)}")

    ex = ccxtpro.cryptocom({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
    })
    try:
        bal = await ex.fetch_balance()
        print("Fetch balance success:", bal)
    except Exception as e:
        print("Fetch balance failed:", type(e), e)
    finally:
        await ex.close()

if __name__ == "__main__":
    asyncio.run(test())
