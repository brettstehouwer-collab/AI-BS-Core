"""Contain the retired unverified shared compute queue, including direct helpers.

No job payload is consumed, executed, logged or treated as earned money.
"""
from typing import Any, Dict

NETWORK_COMPUTE_HOLD = "Compute dispatch is held pending verified owner, paid budget and approved isolation."


def require_verified_compute_dispatch():
    raise RuntimeError(NETWORK_COMPUTE_HOLD)


class ComputeOrchestratorAgent:
    """Compatibility surface for the swarm; all unverified execution stays held."""

    async def process_task(self, task_description: str) -> Dict[str, Any]:
        return {"status": "held", "execution_enabled": False,
                "message": NETWORK_COMPUTE_HOLD, "earned_usd": None}

    def _set_swarm_override(self, active: bool):
        require_verified_compute_dispatch()

    def _execute_wsl2_docker_job(self, job: Dict[str, Any]) -> str:
        require_verified_compute_dispatch()

    def _credit_earnings(self, amount):
        require_verified_compute_dispatch()


def get_compute_orchestrator_agent():
    return ComputeOrchestratorAgent()
