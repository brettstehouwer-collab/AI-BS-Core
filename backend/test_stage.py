import asyncio
from stage_engine import run_orchestration


async def test():
    await run_orchestration(
        "Test",
        [{"description": "test error", "language": "python", "command": "print(1/0)"}],
    )


asyncio.run(test())
