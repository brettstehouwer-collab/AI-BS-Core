import asyncio
import httpx
import sys

async def main():
    print("Testing Hybrid Engine Stream with gauntlet intent...")
    payload = {
        "prompt": "run gauntlet Should I use SQLite memory-mapped IO instead of Redis for my single-node agentic edge server?",
        "history": []
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", "http://localhost:8000/api/v1/hybrid-chat/stream", json=payload) as response:
            async for chunk in response.aiter_text():
                sys.stdout.write(chunk)
                sys.stdout.flush()

asyncio.run(main())
