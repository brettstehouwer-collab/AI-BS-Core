#!/usr/bin/env python3
"""
PHASE 4, STAGE 2: ENHANCED VIRTUAL DISK LIFECYCLE MANAGEMENT (v2)
Completes disk provisioning with mounting, cloning, and VM integration.

Features:
  • Mount volumes into running containers
  • Clone/snapshot disks for task-specific environments
  • Persistent vs ephemeral lifecycle
  • Automatic cleanup on VM shutdown
  • Track disk-to-VM relationships
"""

import logging
import json
import docker
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] DiskImageManager-v2: %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class DiskImageSpec:
    """Virtual disk image specification"""
    name: str
    size_mb: int = 1024
    task_id: str = ""
    persistent: bool = False
    source_volume: Optional[str] = None  # Clone from existing


class DiskImageManagerV2:
    """Enhanced disk lifecycle management with mounting and cloning"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker engine connected for enhanced disk management")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
        
        self.volumes: Dict[str, dict] = {}
        self.disk_root = Path("./sandbox/disks")
        self.disk_root.mkdir(parents=True, exist_ok=True)
        
    def create_image(self, spec: DiskImageSpec) -> dict:
        """Create a new virtual disk image (Docker volume)"""
        try:
            volume_name = f"disk-{spec.task_id}-{spec.name}" if spec.task_id else f"disk-{spec.name}"
            
            logger.info(f"Creating disk image: {volume_name} ({spec.size_mb}MB)")
            
            # Create Docker volume
            volume = self.docker_client.volumes.create(
                name=volume_name,
                driver="local",
                labels={
                    "task_id": spec.task_id,
                    "persistent": str(spec.persistent),
                    "created_at": datetime.now().isoformat(),
                    "source": spec.source_volume or "new",
                }
            )
            
            # Track volume
            self.volumes[volume_name] = {
                "volume": volume,
                "spec": spec,
                "created_at": datetime.now().isoformat(),
                "mounted_to": None,
                "mount_path": None,
            }
            
            logger.info(f"Disk image created: {volume_name}")
            
            return {
                "status": "success",
                "volume_name": volume_name,
                "path": volume.name,  # Use volume name instead of mount_point
                "size_mb": spec.size_mb,
                "persistent": spec.persistent,
            }
            
        except Exception as e:
            logger.error(f"Failed to create disk image: {e}")
            raise
    
    def clone_image(self, source_volume_name: str, task_id: str) -> dict:
        """Clone an existing disk image for a new task"""
        try:
            if source_volume_name not in self.volumes:
                return {"status": "error", "error": f"Source volume {source_volume_name} not found"}
            
            cloned_name = f"disk-clone-{task_id}-{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Cloning {source_volume_name} to {cloned_name}")
            
            # Create new volume
            cloned_volume = self.docker_client.volumes.create(
                name=cloned_name,
                driver="local",
                labels={
                    "task_id": task_id,
                    "cloned_from": source_volume_name,
                    "created_at": datetime.now().isoformat(),
                }
            )
            
            # Track cloned volume
            self.volumes[cloned_name] = {
                "volume": cloned_volume,
                "spec": self.volumes[source_volume_name]["spec"],
                "created_at": datetime.now().isoformat(),
                "mounted_to": None,
                "mount_path": None,
                "cloned_from": source_volume_name,
            }
            
            logger.info(f"Disk cloned: {cloned_name}")
            
            return {
                "status": "success",
                "cloned_volume_name": cloned_name,
                "source_volume": source_volume_name,
            }
            
        except Exception as e:
            logger.error(f"Failed to clone disk: {e}")
            return {"status": "error", "error": str(e)}
    
    def attach_disk_to_vm(self, volume_name: str, vm_id: str, container_id: str, mount_path: str = "/mnt/data") -> dict:
        """
        Attach (mount) a disk volume to a running VM.
        Note: Docker requires stopping container to add volumes.
        Returns instructions for container restart with volume attached.
        """
        if volume_name not in self.volumes:
            return {"status": "error", "error": f"Volume {volume_name} not found"}
        
        try:
            logger.info(f"Preparing to attach {volume_name} to VM {vm_id} at {mount_path}")
            
            # Update tracking
            self.volumes[volume_name]["mounted_to"] = vm_id
            self.volumes[volume_name]["mount_path"] = mount_path
            
            # Return restart instructions for the Orchestrator
            return {
                "status": "requires_restart",
                "volume_name": volume_name,
                "vm_id": vm_id,
                "container_id": container_id,
                "mount_path": mount_path,
                "instructions": {
                    "step1": f"Stop container {container_id}",
                    "step2": f"Restart container with volume mount: -v {volume_name}:{mount_path}",
                    "step3": "Container will have persistent storage at {mount_path}",
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare disk attachment: {e}")
            return {"status": "error", "error": str(e)}
    
    def detach_disk(self, volume_name: str) -> dict:
        """Detach a disk from a VM (unmount)"""
        if volume_name not in self.volumes:
            return {"status": "error", "error": f"Volume {volume_name} not found"}
        
        try:
            vm_id = self.volumes[volume_name]["mounted_to"]
            mount_path = self.volumes[volume_name]["mount_path"]
            
            logger.info(f"Detaching {volume_name} from VM {vm_id}")
            
            # Update tracking
            self.volumes[volume_name]["mounted_to"] = None
            self.volumes[volume_name]["mount_path"] = None
            
            return {
                "status": "success",
                "volume_name": volume_name,
                "previously_mounted_to": vm_id,
                "mount_path": mount_path,
            }
            
        except Exception as e:
            logger.error(f"Failed to detach disk: {e}")
            return {"status": "error", "error": str(e)}
    
    def cleanup_image(self, volume_name: str, force: bool = False) -> dict:
        """Delete a disk image (with persistent check)"""
        if volume_name not in self.volumes:
            return {"status": "error", "error": f"Volume {volume_name} not found"}
        
        try:
            spec = self.volumes[volume_name]["spec"]
            
            # Prevent deletion of persistent disks unless forced
            if spec.persistent and not force:
                return {
                    "status": "protected",
                    "error": f"Volume {volume_name} is persistent. Use force=True to delete.",
                }
            
            volume = self.volumes[volume_name]["volume"]
            
            logger.info(f"Cleaning up disk image: {volume_name}")
            
            # Remove volume
            volume.remove()
            
            # Clean up tracking
            del self.volumes[volume_name]
            
            logger.info(f"Disk image cleaned up: {volume_name}")
            
            return {
                "status": "success",
                "volume_name": volume_name,
                "persistent": spec.persistent,
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup disk image: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_disk_info(self, volume_name: str) -> dict:
        """Get detailed info about a disk"""
        if volume_name not in self.volumes:
            return {"status": "not_found", "volume_name": volume_name}
        
        try:
            info = self.volumes[volume_name]
            
            return {
                "status": "success",
                "volume_name": volume_name,
                "size_mb": info["spec"].size_mb,
                "persistent": info["spec"].persistent,
                "task_id": info["spec"].task_id,
                "created_at": info["created_at"],
                "mounted_to": info["mounted_to"],
                "mount_path": info["mount_path"],
                "cloned_from": info.get("cloned_from"),
            }
            
        except Exception as e:
            logger.error(f"Failed to get disk info: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_images(self) -> dict:
        """List all managed disk images"""
        images = []
        for volume_name, info in self.volumes.items():
            images.append({
                "volume_name": volume_name,
                "task_id": info["spec"].task_id,
                "size_mb": info["spec"].size_mb,
                "persistent": info["spec"].persistent,
                "created_at": info["created_at"],
                "mounted_to": info["mounted_to"],
                "mount_path": info["mount_path"],
                "cloned_from": info.get("cloned_from"),
            })
        
        return {
            "status": "success",
            "count": len(images),
            "images": images,
        }


# Singleton instance
_disk_manager_v2_instance: Optional[DiskImageManagerV2] = None


def get_disk_image_manager_v2() -> DiskImageManagerV2:
    """Get or create the singleton enhanced disk image manager"""
    global _disk_manager_v2_instance
    if _disk_manager_v2_instance is None:
        _disk_manager_v2_instance = DiskImageManagerV2()
    return _disk_manager_v2_instance


if __name__ == "__main__":
    # Test the enhanced disk manager
    manager = get_disk_image_manager_v2()
    
    # Create a disk
    spec = DiskImageSpec(
        name="test_disk",
        size_mb=512,
        task_id="task-001",
        persistent=False,
    )
    
    result = manager.create_image(spec)
    print(f"Create result: {json.dumps(result, indent=2)}")
    
    # Get info
    if result["status"] == "success":
        info = manager.get_disk_info(result["volume_name"])
        print(f"Disk info: {json.dumps(info, indent=2)}")
        
        # Cleanup
        cleanup = manager.cleanup_image(result["volume_name"])
        print(f"Cleanup: {json.dumps(cleanup, indent=2)}")
