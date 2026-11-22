import asyncio, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.get('https://discord.com') as r:
            print(r.status)
asyncio.run(main())
