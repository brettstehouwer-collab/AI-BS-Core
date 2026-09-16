import asyncio
import httpx
import json

BROKER_URL = "http://127.0.0.1:8085/publish"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"

async def ingest_finance():
    print("[Finance Ingestor] Starting live data feed...")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                res = await client.get(COINGECKO_URL, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    
                    # Push to message broker
                    payload = {
                        "topic": "finance_ticker",
                        "payload": data
                    }
                    
                    # We can use fire-and-forget or await it
                    broker_res = await client.post(BROKER_URL, json=payload, timeout=5.0)
                    if broker_res.status_code == 200:
                        print(f"[Finance Ingestor] Successfully pushed ticker data.")
                    else:
                        print(f"[Finance Ingestor] Broker error: {broker_res.text}")
                else:
                    print(f"[Finance Ingestor] CoinGecko API Error: {res.status_code}")
                    
            except Exception as e:
                print(f"[Finance Ingestor] Exception: {e}")
                
            await asyncio.sleep(60) # Poll every 60 seconds to respect free tier rate limits

if __name__ == "__main__":
    try:
        asyncio.run(ingest_finance())
    except KeyboardInterrupt:
        print("[Finance Ingestor] Shutting down.")
