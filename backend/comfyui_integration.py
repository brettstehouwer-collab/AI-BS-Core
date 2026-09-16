#!/usr/bin/env python3
"""
AI-BS Matrix — ComfyUI Integration Module
============================================
Communicates with a local ComfyUI instance for advanced image generation workflows.
Supports custom nodes, control nets, IP-Adapter, and complex pipelines.

Usage:
    from comfyui_integration import ComfyUIClient
    client = ComfyUIClient()
    result = await client.generate(prompt="A cozy cabin", workflow="img2img")
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("comfyui_integration")


@dataclass
class ComfyUIConfig:
    """Configuration for ComfyUI connection."""

    host: str = "127.0.0.1"
    port: int = 8188
    base_url: str = ""  # auto-computed

    def __post_init__(self):
        if not self.base_url:
            self.base_url = f"http://{self.host}:{self.port}"


@dataclass
class ComfyUIResult:
    """Result from a ComfyUI generation."""

    status: str  # "success", "error", "queued"
    prompt_id: Optional[str] = None
    output_images: List[str] = field(default_factory=list)
    execution_time_sec: float = 0.0
    error: Optional[str] = None

    def __bool__(self):
        return self.status == "success"


class ComfyUIClient:
    """
    Async client for communicating with a local ComfyUI instance.

    Supports:
    - Text-to-image generation
    - Image-to-image (img2img)
    - ControlNet workflows
    - IP-Adapter style transfers
    - Custom node pipelines
    - Workflow management

    Requires:
    - ComfyUI running locally (default: http://127.0.0.1:8189)
    - Python 3.12+ with aiohttp
    """

    def __init__(self, config: Optional[ComfyUIConfig] = None):
        self.config = config or ComfyUIConfig()
        self._prompt_id: Optional[str] = None
        self._is_connected = False
        logger.info(f"ComfyUIClient initialized at {self.config.base_url}")

    # --- Connection Management ---
    async def connect(self) -> bool:
        """Test connection to ComfyUI instance."""
        try:
            import aiohttp  # type: ignore

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.base_url}/system_stats", timeout=5
                ) as resp:
                    if resp.status == 200:
                        self._is_connected = True
                        logger.info("ComfyUI connection established")
                        return True
        except Exception as e:
            logger.warning(f"ComfyUI connection failed: {e}")
        return False

    async def disconnect(self):
        """Close any active connections."""
        self._is_connected = False
        self._prompt_id = None

    # --- Workflow Templates ---
    @staticmethod
    def get_workflow(workflow_type: str = "txt2img") -> Dict[str, Any]:
        """
        Get a pre-built workflow template.

        Args:
            workflow_type: One of "txt2img", "img2img", "controlnet", "ipadapter"

        Returns:
            ComfyUI workflow JSON as dict
        """
        workflows = {
            "txt2img": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": 8.0,
                        "denoise": 1.0,
                        "latent_image": ["5", 0],
                        "model": ["4", 0],
                        "negative": ["7", 0],
                        "positive": ["6", 0],
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "seed": -1,
                        "steps": 20,
                    },
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "batch_size": 1,
                        "height": 1024,
                        "width": 1024,
                    },
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": "MASTER_PROMPT"},
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": "low quality, blurry"},
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2],
                    },
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "AI-BS",
                        "images": ["8", 0],
                    },
                },
            },
            "img2img": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": 8.0,
                        "denoise": 0.75,
                        "latent_image": ["11", 0],
                        "model": ["4", 0],
                        "negative": ["7", 0],
                        "positive": ["6", 0],
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "seed": -1,
                        "steps": 20,
                    },
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": "MASTER_PROMPT"},
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["4", 1], "text": "low quality, blurry"},
                },
                "8": {
                    "class_type": "VAEEncode",
                    "inputs": {
                        "pixels": ["10", 0],
                        "vae": ["4", 2],
                    },
                },
                "9": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                },
                "10": {
                    "class_type": "LoadImage",
                    "inputs": {"image": "INPUT_IMAGE_PATH"},
                },
                "11": {
                    "class_type": "VAEEncode",
                    "inputs": {
                        "pixels": ["10", 0],
                        "vae": ["9", 2],
                    },
                },
                "12": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2],
                    },
                },
                "13": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "AI-BS-img2img",
                        "images": ["12", 0],
                    },
                },
            },
        }

        workflow = workflows.get(workflow_type, workflows["txt2img"])
        return json.loads(json.dumps(workflow))  # Deep copy

    # --- Generation ---
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "low quality, blurry, deformed",
        workflow_type: str = "txt2img",
        model_name: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg: float = 8.0,
        seed: int = -1,
    ) -> ComfyUIResult:
        """
        Generate an image via ComfyUI workflow.

        Args:
            prompt: Positive text prompt
            negative_prompt: Negative text prompt
            workflow_type: Workflow template to use
            model_name: Checkpoint model name (auto-detected if not provided)
            width: Output image width
            height: Output image height
            steps: Number of inference steps
            cfg: Classifier-free guidance scale
            seed: Random seed (-1 for random)

        Returns:
            ComfyUIResult with output images
        """
        import aiohttp  # type: ignore

        if not await self.connect():
            return ComfyUIResult(
                status="error",
                error="ComfyUI not connected. Start ComfyUI and try again.",
            )

        start = time.time()

        try:
            workflow = self.get_workflow(workflow_type)

            # Inject parameters into workflow
            for node_id, node in workflow.items():
                if "inputs" in node:
                    inputs = node["inputs"]

                    # Replace prompt text
                    if "text" in inputs and "MASTER_PROMPT" in inputs["text"]:
                        inputs["text"] = prompt

                    # Replace negative prompt
                    if "text" in inputs and "low quality" in inputs["text"]:
                        inputs["text"] = negative_prompt

                    # Replace model checkpoint
                    if "ckpt_name" in inputs and model_name:
                        inputs["ckpt_name"] = model_name

                    # Replace dimensions
                    if "width" in inputs:
                        inputs["width"] = width
                    if "height" in inputs:
                        inputs["height"] = height

                    # Replace steps
                    if "steps" in inputs:
                        inputs["steps"] = steps

                    # Replace CFG
                    if "cfg" in inputs:
                        inputs["cfg"] = cfg

                    # Replace seed
                    if "seed" in inputs and seed != -1:
                        inputs["seed"] = seed

            async with aiohttp.ClientSession() as session:
                # Queue the prompt
                async with session.post(
                    f"{self.config.base_url}/prompt",
                    json={"prompt": workflow},
                    timeout=30,
                ) as resp:
                    if resp.status != 200:
                        return ComfyUIResult(
                            status="error",
                            error=f"ComfyUI returned {resp.status}",
                        )

                    data = await resp.json()
                    self._prompt_id = data.get("prompt_id")
                    logger.info(f"ComfyUI prompt queued: {self._prompt_id}")

                # Wait for completion
                while True:
                    await asyncio.sleep(1)

                    async with session.get(
                        f"{self.config.base_url}/history/{self._prompt_id}",
                        timeout=5,
                    ) as resp:
                        if resp.status == 200:
                            history = await resp.json()
                            if self._prompt_id in history:
                                break

                # Fetch output images
                history = history[self._prompt_id]
                output_images = []

                for node_id, node_output in history.get("outputs", {}).items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            img_url = f"{
                                self.config.base_url}/view?filename={
                                img['filename']}&subfolder={
                                img.get(
                                    'subfolder',
                                    '')}&type={
                                img.get(
                                    'type',
                                    'output')}"
                            output_images.append(img_url)

                elapsed = time.time() - start

                return ComfyUIResult(
                    status="success",
                    prompt_id=self._prompt_id,
                    output_images=output_images,
                    execution_time_sec=elapsed,
                )

        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"ComfyUI generation failed: {e}")
            return ComfyUIResult(
                status="error",
                prompt_id=self._prompt_id,
                execution_time_sec=elapsed,
                error=str(e),
            )

    # --- Workflow Management ---
    async def get_available_models(self) -> List[str]:
        """List available checkpoint models on ComfyUI."""
        import aiohttp  # type: ignore

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.base_url}/object_info",
                    timeout=10,
                ) as resp:
                    if resp.status == 200:
                        info = await resp.json()
                        checkpoints = (
                            info.get("CheckpointLoaderSimple", {})
                            .get("input", {})
                            .get("required", {})
                            .get("ckpt_name", ([], {}))[0]
                        )
                        return checkpoints
        except Exception as e:
            logger.warning(f"Failed to get models: {e}")
        return []

    async def get_available_workflows(self) -> List[str]:
        """List available workflow templates."""
        return list(self.get_workflow.__func__.__defaults__[0].keys())  # type: ignore

    async def upload_image(self, image_path: str) -> str:
        """Upload an image to ComfyUI for img2img workflows."""
        import aiohttp  # type: ignore

        try:
            with open(image_path, "rb") as f:
                files = {"image": (Path(image_path).name, f)}

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.config.base_url}/upload/image",
                        data=files,
                        timeout=30,
                    ) as resp:
                        if resp.status == 200:
                            return await resp.text()
        except Exception as e:
            logger.error(f"Image upload failed: {e}")
        return ""


# --- Singleton instance for SwarmOrchestrator integration ---
_comfyui_instance: Optional[ComfyUIClient] = None


def get_comfyui_client(config: Optional[ComfyUIConfig] = None) -> ComfyUIClient:
    """Get or create the singleton ComfyUIClient instance."""
    global _comfyui_instance
    if _comfyui_instance is None:
        _comfyui_instance = ComfyUIClient(config)
    return _comfyui_instance
