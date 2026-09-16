import asyncio
from bullshit_orchestrator import SwarmOrchestrator
import logging

logging.basicConfig(level=logging.INFO)


async def test_react_loop():
    orchestrator = SwarmOrchestrator()
    task = (
        "I need to see what is blocking port 11435. Please investigate the workspace."
    )
    print("================== Auto-Builder ReAct Loop Test ==================")
    print(f"User Task: {task}")

    final_response = await orchestrator.prompt_auto_builder(task)

    print("==================================================================")
    print("FINAL LLM OUTPUT:")
    print(final_response)


if __name__ == "__main__":
    asyncio.run(test_react_loop())
