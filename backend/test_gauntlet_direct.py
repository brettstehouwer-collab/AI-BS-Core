import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

from aibs_reasoning_engine import AIBSSelfProblemSolver

async def main():
    q = "Do you always run the 12 stages when I ask any question?"
    print(f"Testing Swarm Gauntlet with Query: {q}\n")
    res = await AIBSSelfProblemSolver.solve_and_refine(q)
    print("=== FINAL SOVEREIGN SYNTHESIS ===")
    print(res.get("final_solution"))

asyncio.run(main())
