import asyncio
from stage_engine import run_orchestration


async def test_swarm():
    payload = [
        {
            "id": "agent_1",
            "description": "Parallel task 1",
            "language": "python",
            "command": "import time; print('Agent 1 starting...'); time.sleep(2); print('Agent 1 finished.')",
            "depends_on": [],
        },
        {
            "id": "agent_2",
            "description": "Parallel task 2",
            "language": "python",
            "command": "import time; print('Agent 2 starting...'); time.sleep(2); print('Agent 2 finished.')",
            "depends_on": [],
        },
        {
            "id": "agent_3",
            "description": "Dependent task 3",
            "language": "python",
            "command": "print('Agent 3 executing because 1 and 2 are done.')",
            "depends_on": ["agent_1", "agent_2"],
        },
    ]
    res = await run_orchestration("Test Swarm Parallel Execution", payload)
    import json

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    asyncio.run(test_swarm())
