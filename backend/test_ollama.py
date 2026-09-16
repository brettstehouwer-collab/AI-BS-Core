"""Test Ollama backend API."""

import asyncio

import httpx


async def test():
    """Run test."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("http://127.0.0.1:11434/api/chat", json={
            "model": "stehouwer_llm",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False
        })
        print("Status code:", r.status_code)
        print("Response:", r.text)

asyncio.run(test())
