import asyncio
from hunter_gatherer import hunt_for_knowledge


async def main():
    await hunt_for_knowledge()


asyncio.run(main())
