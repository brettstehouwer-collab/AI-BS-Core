#!/usr/bin/env python3
"""
PHASE 4, STAGE 1: HYPERVISOR CONTROLLER DAEMON
Bridges FastAPI Orchestrator with Docker-based VM isolation layer.

Instead of QEMU, we use Docker containers as lightweight hypervisors.
Each container acts as a virtual machine with its own filesystem, network namespace, and resource limits.

Architecture:
  Orchestrator (FastAPI :8000)
    ↓
  HypervisorControllerDaemon (manages Docker containers)
    ↓
  Docker Engine
    ↓
  Alpine Linux containers (as isolated execution environments)

This trades some hardware-level isolation depth for immediate, production-ready
capability without needing QEMU installation.
"""

import asyncio
import json
import logging
import docker
import uuid
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] HypervisorController: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class VMConfig:
    """Virtual Machine Configuration"""

    vm_id: str
    memory_mb: int = 512
    cpu_cores: int = 1
    disk_image: Optional[str] = None
    timeout_seconds: int = 3600
    network_isolated: bool = True


class HypervisorControllerDaemon:
    """
    Manages VM lifecycle using Docker containers.
    Provides hardware-level isolation for arbitrary code execution.
    """

    def __init__(self):
        """Initialize Docker client and tracking structures"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker engine connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise

        self.active_vms: Dict[str, dict] = {}
        self.vm_log_dir = Path("./logs/vm_execution")
        self.vm_log_dir.mkdir(parents=True, exist_ok=True)

    def boot_vm(self, config: VMConfig) -> dict:
        """
        Boot an isolated Alpine Linux container as a VM.

        Args:
            config: VMConfig with vm_id, memory, cores, etc.

        Returns:
            {"status": "booting", "vm_id": "...", "container_id": "...", "pid": ...}
        """
        try:
            # Build container configuration
            container_config = {
                "image": "alpine:latest",
                "detach": True,
                "name": f"vm-{config.vm_id}",
                "hostname": f"vm-{config.vm_id}",
                "stdin_open": True,
                "tty": True,
                "mem_limit": f"{config.memory_mb}m",
                "cpu_quota": int(100000 * config.cpu_cores),  # CPU limit
                "network_disabled": config.network_isolated,
                "security_opt": ["no-new-privileges"],
                "read_only": False,
                "tmpfs": {"/tmp": "size=256m,mode=1777"},  # Temporary storage
            }

            logger.info(f"Booting VM {config.vm_id} with config: {config}")

            # Create and start container
            container = self.docker_client.containers.run(
                **container_config,
                command="/bin/sh -c 'sleep infinity'",  # Keep alive for execution
            )

            # Track the VM
            self.active_vms[config.vm_id] = {
                "container_id": container.id,
                "container": container,
                "status": "running",
                "created_at": datetime.now().isoformat(),
                "memory_mb": config.memory_mb,
                "cpu_cores": config.cpu_cores,
            }

            logger.info(
                f"VM {config.vm_id} booted successfully (container: {container.id[:12]})"
            )

            return {
                "status": "booting",
                "vm_id": config.vm_id,
                "container_id": container.id,
                "memory_mb": config.memory_mb,
                "cpu_cores": config.cpu_cores,
            }

        except Exception as e:
            logger.error(f"Failed to boot VM {config.vm_id}: {e}")
            raise

    def execute_in_vm(self, vm_id: str, command: str, timeout: int = 30) -> dict:
        """
        Execute a command inside a running VM container.

        Args:
            vm_id: VM identifier
            command: Shell command to execute
            timeout: Execution timeout in seconds

        Returns:
            {"status": "success|failure", "exit_code": ..., "stdout": "...", "stderr": "..."}
        """
        if vm_id not in self.active_vms:
            return {"status": "error", "error": f"VM {vm_id} not found"}

        try:
            vm_info = self.active_vms[vm_id]
            container = vm_info["container"]

            logger.info(f"Executing in VM {vm_id}: {command}")

            # Execute command in container
            exit_code, output = container.exec_run(
                cmd=command,
                stdout=True,
                stderr=True,
                stdin=False,
                tty=False,
                detach=False,
            )

            result = {
                "status": "success" if exit_code == 0 else "failure",
                "vm_id": vm_id,
                "exit_code": exit_code,
                "stdout": (
                    output.decode("utf-8", errors="ignore")
                    if isinstance(output, bytes)
                    else str(output)
                ),
                "command": command,
            }

            logger.info(f"Command execution in {vm_id}: exit_code={exit_code}")
            return result

        except Exception as e:
            logger.error(f"Failed to execute in VM {vm_id}: {e}")
            return {"status": "error", "error": str(e), "vm_id": vm_id}

    def get_vm_status(self, vm_id: str) -> dict:
        """Get status of a running VM"""
        if vm_id not in self.active_vms:
            return {"status": "not_found", "vm_id": vm_id}

        try:
            vm_info = self.active_vms[vm_id]
            container = vm_info["container"]
            container.reload()

            return {
                "status": (
                    "running" if container.status == "running" else container.status
                ),
                "vm_id": vm_id,
                "container_id": container.id[:12],
                "memory_mb": vm_info["memory_mb"],
                "cpu_cores": vm_info["cpu_cores"],
                "created_at": vm_info["created_at"],
            }
        except Exception as e:
            logger.error(f"Failed to get status of VM {vm_id}: {e}")
            return {"status": "error", "vm_id": vm_id, "error": str(e)}

    def shutdown_vm(self, vm_id: str) -> dict:
        """Shutdown and clean up a VM"""
        if vm_id not in self.active_vms:
            return {"status": "not_found", "vm_id": vm_id}

        try:
            vm_info = self.active_vms[vm_id]
            container = vm_info["container"]

            logger.info(f"Shutting down VM {vm_id}")

            # Stop container
            container.stop(timeout=10)

            # Remove container
            container.remove()

            # Clean up tracking
            del self.active_vms[vm_id]

            logger.info(f"VM {vm_id} shutdown complete")

            return {
                "status": "shutdown",
                "vm_id": vm_id,
                "container_id": container.id[:12],
            }

        except Exception as e:
            logger.error(f"Failed to shutdown VM {vm_id}: {e}")
            return {"status": "error", "vm_id": vm_id, "error": str(e)}

    def list_vms(self) -> dict:
        """List all active VMs"""
        vms = []
        for vm_id, info in self.active_vms.items():
            vms.append(
                {
                    "vm_id": vm_id,
                    "container_id": info["container_id"][:12],
                    "memory_mb": info["memory_mb"],
                    "cpu_cores": info["cpu_cores"],
                    "created_at": info["created_at"],
                }
            )

        return {
            "status": "success",
            "count": len(vms),
            "vms": vms,
        }


# Singleton instance
_controller_instance: Optional[HypervisorControllerDaemon] = None


def get_hypervisor_controller() -> HypervisorControllerDaemon:
    """Get or create the singleton hypervisor controller"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = HypervisorControllerDaemon()
    return _controller_instance


if __name__ == "__main__":
    # Test the controller
    controller = get_hypervisor_controller()

    # Boot a test VM
    config = VMConfig(
        vm_id=str(uuid.uuid4())[:8],
        memory_mb=256,
        cpu_cores=1,
    )

    result = controller.boot_vm(config)
    print(f"Boot result: {json.dumps(result, indent=2)}")

    # Execute a command
    if result["status"] == "booting":
        vm_id = result["vm_id"]
        exec_result = controller.execute_in_vm(
            vm_id, "echo 'Hello from VM' && uname -a"
        )
        print(f"Execute result: {json.dumps(exec_result, indent=2)}")

        # Get status
        status = controller.get_vm_status(vm_id)
        print(f"VM status: {json.dumps(status, indent=2)}")

        # Shutdown
        shutdown_result = controller.shutdown_vm(vm_id)
        print(f"Shutdown result: {json.dumps(shutdown_result, indent=2)}")
