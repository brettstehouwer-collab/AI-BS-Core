import os
import time
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VAULT_DIR = os.path.join(BASE_DIR, "AI-BS_Knowledge_Vaults", "Agent_Thoughts")


def log_agent_thought(task_name: str, reasoning: str, tools_used: list):
    """
    Saves the agent's internal reasoning and logic directly to the Knowledge Vault
    so that it can be indexed by ChromaDB and learned by the local LLM.
    """
    os.makedirs(VAULT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_task_name = task_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"ThoughtLog_{timestamp}_{safe_task_name}.md"
    filepath = os.path.join(VAULT_DIR, filename)

    content = f"# Agent Thought Log: {task_name}\n"
    content += f"**Timestamp:** {datetime.now().isoformat()}\n\n"
    content += f"## Tool Selection & Logic\n"
    content += f"**Tools Used:** {', '.join(tools_used)}\n\n"
    content += f"## Reasoning & Internal State\n"
    content += f"{reasoning}\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[Thought Logger] Internal logic saved to Vault: {filepath}")
    return filepath


if __name__ == "__main__":
    # Simple test
    log_agent_thought(
        "Test_Initialization",
        "Testing the logging module to ensure vault writing works.",
        ["write_to_file", "run_command"],
    )
