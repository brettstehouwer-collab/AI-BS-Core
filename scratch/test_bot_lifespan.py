import asyncio
import sys
sys.path.append(r"C:\AI-BS\backend")
from crypto_trader_bot import app, lifespan

async def test():
    try:
        async with lifespan(app):
            import crypto_trader_bot
            print("Exchange instance:", crypto_trader_bot.exchange_instance)
            if crypto_trader_bot.exchange_instance:
                bal = await crypto_trader_bot.exchange_instance.fetch_balance()
                print("Balance fetched:", bal.get("USD"))
    except Exception as e:
        print("Lifespan error:", e)

if __name__ == "__main__":
    asyncio.run(test())
