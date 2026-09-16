import json
import logging
import os
import subprocess
import time
from typing import Dict, Any

from commercial_gateway.gpu_network_router import (
    JOB_QUEUE,
    load_real_compute_ledger,
    save_real_compute_ledger,
)

logger = logging.getLogger("ComputeOrchestratorAgent")
logger.setLevel(logging.INFO)

SCHEDULE_CONFIG_FILE = r"C:\AI-BS\backend\compute_schedule_config.json"


class ComputeOrchestratorAgent:
    """
    Agent responsible for monitoring the Renter API Queue and dynamically overriding
    the Clore.ai schedule to execute high-paying direct client workloads inside WSL2.
    """

    def __init__(self):
        logger.info("ComputeOrchestratorAgent initialized.")

    async def process_task(self, task_description: str) -> Dict[str, Any]:
        """Entry point for the swarm to hand off processing to this agent."""
        logger.info("Checking Compute Job Queue for high-paying direct jobs...")

        # Look for the highest paying job in the queue
        if not JOB_QUEUE:
            return {
                "status": "no_jobs",
                "message": "Queue is empty. Clore.ai yield continues.",
            }

        best_job = max(JOB_QUEUE, key=lambda j: j.get("max_budget_usd", 0.0))

        if best_job.get("max_budget_usd", 0.0) < 1.00:
            return {
                "status": "low_yield",
                "message": "No jobs meet the yield threshold. Keeping Clore.ai active.",
            }

        # Secure the job
        logger.info(
            f"Secured high-yield direct job {best_job['job_id']} for ${best_job['max_budget_usd']:.2f}"
        )
        JOB_QUEUE.remove(best_job)

        # 1. Override Schedule
        self._set_swarm_override(True)
        logger.info("Override set. Waiting for Monetization Daemon to yield the GPU...")
        time.sleep(12)  # Give monetization daemon 10s loop time to kill clore

        # 2. Execute Workload in WSL2 Docker
        result = self._execute_wsl2_docker_job(best_job)

        # 3. Restore Schedule
        self._set_swarm_override(False)

        # 4. Credit Earnings
        self._credit_earnings(best_job["max_budget_usd"])

        return {
            "status": "success",
            "job_id": best_job["job_id"],
            "result": result,
            "earned_usd": best_job["max_budget_usd"],
        }

    def _set_swarm_override(self, active: bool):
        try:
            if not os.path.exists(SCHEDULE_CONFIG_FILE):
                return
            with open(SCHEDULE_CONFIG_FILE, "r") as f:
                config = json.load(f)

            if active:
                # Save previous mode to restore later
                config["previous_mode"] = config.get("current_mode", "auto_schedule")
                config["current_mode"] = "swarm_override"
            else:
                config["current_mode"] = config.get("previous_mode", "auto_schedule")

            with open(SCHEDULE_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to set swarm override: {e}")

    def _execute_wsl2_docker_job(self, job: Dict[str, Any]) -> str:
        """Runs arbitrary client code inside a locked down Docker container in WSL2."""
        logger.info(f"Executing job {job['job_id']} in secure WSL2 container.")

        # Best way to make money: Enable users to save model weights/LoRAs
        # We mount a unique host directory so the client can export their training results.
        output_dir_win = rf"C:\AI-BS\backend\client_outputs\{job['job_id']}"
        output_dir_wsl = f"/mnt/c/AI-BS/backend/client_outputs/{job['job_id']}"
        os.makedirs(output_dir_win, exist_ok=True)

        code_payload = job.get(
            "prompt_or_code", "print('Hello from AI-BS Secure Docker Enclave')"
        )

        # Safest route: Aggressive container lockdown
        cmd = [
            "wsl",
            "-d",
            "Ubuntu",
            "-u",
            "root",
            "docker",
            "run",
            "--rm",
            "--gpus",
            "all",
            "--memory",
            "16g",
            "--cpus",
            "8.0",
            "--pids-limit",
            "100",  # Prevent fork bombs
            "--cap-drop",
            "ALL",  # Safest route: drop all linux capabilities
            "--security-opt",
            "no-new-privileges:true",
            "--network",
            "none",  # No internet access inside container
            "-v",
            f"{output_dir_wsl}:/workspace/output",  # Premium feature for higher yield
            "-w",
            "/workspace",
            "pytorch/pytorch:latest",
            "python",
            "-c",
            code_payload,
        ]

        try:
            logger.info("Spinning up ultra-secure WSL2 Docker perimeter...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            # Check if they exported any weights
            files_exported = os.listdir(output_dir_win)
            export_msg = f"\n[Premium Egress]: 0 files exported."
            if files_exported:
                export_msg = f"\n[Premium Egress]: {len(files_exported)} files successfully exported to /client_outputs/{job['job_id']}. Ready for client download."

            if result.returncode == 0:
                logger.info(f"Container execution successful: {result.stdout.strip()}")
                return result.stdout.strip() + export_msg
            else:
                logger.warning(f"Container execution failed: {result.stderr.strip()}")
                return f"Error: {result.stderr.strip()}" + export_msg
        except subprocess.TimeoutExpired:
            return "Error: Job timed out. (Max compute duration reached)"
        except Exception as e:
            logger.error(f"WSL2 Docker error: {e}")
            return f"Error: {e}"

    def _credit_earnings(self, amount: float):
        try:
            ledger = load_real_compute_ledger()
            ledger["total_earned_usd"] = round(ledger["total_earned_usd"] + amount, 2)
            ledger["pending_usd"] = round(ledger["pending_usd"] + amount, 2)
            save_real_compute_ledger(ledger)
            logger.info(f"Credited ${amount:.2f} to AI-BS Master Ledger.")
        except Exception as e:
            logger.error(f"Error crediting earnings: {e}")


def get_compute_orchestrator_agent():
    return ComputeOrchestratorAgent()
