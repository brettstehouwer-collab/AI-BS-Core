import asyncio
from stage_engine import run_orchestration


async def run_test():
    massive_plan = [
        {
            "id": "agent_1_header",
            "depends_on": [],
            "language": "html",
            "description": "Create a glassmorphism dark-mode header component.",
            "command": "<html><body><header style='background:rgba(0,0,0,0.5); padding:20px; color:white;'><h1>Dashboard</h1></header></body></html>",
        },
        {
            "id": "agent_2_sidebar",
            "depends_on": [],
            "language": "html",
            "description": "Create a sleek dark-mode sidebar.",
            "command": "<html><body><nav style='width:200px; height:100vh; background:#222; color:white;'><ul><li>Home</li></ul></nav></body></html>",
        },
        {
            "id": "agent_3_chart",
            "depends_on": [],
            "language": "html",
            "description": "Create an aesthetically pleasing HTML/CSS chart placeholder with OVERLAPPING text to trigger visual failure.",
            "command": "<html><body><div style='position:absolute; top:0; left:0; font-size:100px; color:red; z-index:999;'>I AM OVERLAPPING THE CHART</div><div style='background:blue; width:300px; height:300px;'>Chart Data</div></body></html>",
        },
        {
            "id": "agent_4_assembly",
            "depends_on": ["agent_1_header", "agent_2_sidebar", "agent_3_chart"],
            "language": "python",
            "description": "Assemble the final components (Won't execute if agent 3 fails).",
            "command": "print('Assembly complete.')",
        },
    ]

    print("Starting Massive Swarm Test...")
    result = await run_orchestration(
        "Generate a beautiful dark-mode React dashboard", massive_plan
    )
    print("Swarm Result:")
    import json

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(run_test())
