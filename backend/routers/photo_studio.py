"""
AI-BS Photo Studio & Vision Processing Router
---------------------------------------------
Exposes hybrid dual-path processing:
1. Fast Direct Path (ONNX Runtime GPU / BiRefNet): Sub-second alpha matting running in-process
   via persistent FastAPI lifespan singleton (`app.state.matting_engine`).
2. Generative Depth Path (ComfyUI via Local Loopback): High-end diffusion, inpainting,
   and super-resolution dispatched with concrete node graph schema to 127.0.0.1:8188 / 8189.
"""

import os
import sys
import time
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Request

from modules.vision_matting import get_matting_engine, LocalMattingEngine

logger = logging.getLogger("PhotoStudioRouter")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/photo-studio", tags=["Photo Studio"])


def get_tenant(request: Request) -> str:
    return request.headers.get("X-Client-ID", "stehouwer_publishing")


class MattingRequest(BaseModel):
    input_path: str = Field(..., description="Path to source image file on local disk")
    output_path: Optional[str] = Field(None, description="Optional path to save output image. Auto-generated if omitted.")
    mode: str = Field("direct_gpu", description="Execution mode: 'direct_gpu' or 'comfyui_diffusion'")
    alpha_matting: bool = Field(True, description="Enable soft sub-pixel alpha boundary matting")
    model_name: str = Field("birefnet-general", description="Matting model: 'birefnet-general', 'u2net', or 'isnet-general-use'")
    only_mask: bool = Field(False, description="Whether to output single-channel alpha mask instead of composite")
    upscale_factor: Optional[float] = Field(2.0, description="Upscale multiplier for ComfyUI workflow")


class ComfyWorkflowTemplate:
    """
    Constructs concrete, valid ComfyUI API graph schemas for background removal and upscaling.
    Avoids empty prompt payload rejections (HTTP 400).
    """
    @staticmethod
    def build_birefnet_upscale_graph(
        image_path: str,
        upscale_factor: float = 2.0,
        output_prefix: str = "aibs_matte"
    ) -> Dict[str, Any]:
        """
        Concrete ComfyUI node graph in API format.
        """
        prompt = {
            "1": {
                "inputs": {
                    "image": os.path.basename(image_path),
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {
                    "image": ["1", 0],
                    "model_name": "birefnet-general",
                    "alpha_matting": True
                },
                "class_type": "BiRefNet"
            },
            "3": {
                "inputs": {
                    "model_name": "4x-UltraSharp.pth"
                },
                "class_type": "UpscaleModelLoader"
            },
            "4": {
                "inputs": {
                    "upscale_model": ["3", 0],
                    "image": ["2", 0]
                },
                "class_type": "ImageUpscaleWithModel"
            },
            "5": {
                "inputs": {
                    "filename_prefix": output_prefix,
                    "images": ["4", 0]
                },
                "class_type": "SaveImage"
            }
        }
        return prompt


@router.get("/health")
async def get_health(request: Request, client_id: str = Depends(get_tenant)):
    """
    Returns health, active ONNX execution provider (CUDA vs CPU), and ComfyUI loopback connectivity.
    """
    # Check lifespan singleton or lazy module singleton
    engine: LocalMattingEngine = getattr(request.app.state, "matting_engine", None)
    if not engine:
        engine = get_matting_engine()

    telemetry = engine.get_runtime_telemetry()

    # Check ComfyUI reachability
    comfy_online = False
    for port in [8188, 8189]:
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    comfy_online = True
                    break
        except Exception:
            pass

    return {
        "status": "HEALTHY",
        "client_id": client_id,
        "engine": "LocalMattingEngine",
        "active_provider": telemetry.get("active_provider"),
        "cuda_accelerated": "CUDA" in str(telemetry.get("active_provider")),
        "model_name": telemetry.get("model_name"),
        "telemetry": telemetry,
        "comfyui_loopback_online": comfy_online
    }


@router.post("/process-matte")
async def process_matte(req: MattingRequest, request: Request, client_id: str = Depends(get_tenant)):
    """
    Routes matting job dynamically between in-process Direct-CUDA execution and ComfyUI loopback diffusion.
    """
    if not os.path.exists(req.input_path):
        raise HTTPException(status_code=400, detail=f"Input image not found on disk: {req.input_path}")

    # Resolve output path
    if not req.output_path:
        stem = Path(req.input_path).stem
        out_dir = Path(req.input_path).parent
        tag = "mask" if req.only_mask else "matte"
        req.output_path = str(out_dir / f"{stem}_{tag}_{int(time.time())}.png")

    if req.mode == "direct_gpu":
        try:
            # 1. Retrieve persistent lifespan singleton if available
            engine: LocalMattingEngine = getattr(request.app.state, "matting_engine", None)
            if not engine or engine.model_name != req.model_name:
                engine = get_matting_engine(req.model_name)

            t0 = time.time()
            if req.only_mask:
                out_file = engine.generate_mask_only(req.input_path, req.output_path)
            else:
                out_file = engine.extract_foreground(req.input_path, req.output_path, alpha_matting=req.alpha_matting)

            elapsed_ms = (time.time() - t0) * 1000.0

            return {
                "status": "SUCCESS",
                "client_id": client_id,
                "engine": "Direct-CUDA",
                "active_provider": engine.active_provider,
                "latency_ms": round(elapsed_ms, 2),
                "output_path": out_file,
                "relative_url": f"/api/media/file/images/{os.path.basename(out_file)}"
            }
        except Exception as e:
            logger.error(f"Direct GPU matting failure: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Direct GPU matting error: {str(e)}")

    elif req.mode == "comfyui_diffusion":
        # 2. Dispatch via concrete ComfyUI node graph schema
        try:
            from comfy_bridge import queue_comfyui_workflow, COMFYUI_HOST
            
            # Select target host port (prefer 8188 or 8189)
            target_host = "http://127.0.0.1:8188"
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", 8188)) != 0:
                    target_host = "http://127.0.0.1:8189"

            graph_payload = ComfyWorkflowTemplate.build_birefnet_upscale_graph(
                image_path=req.input_path,
                upscale_factor=req.upscale_factor or 2.0
            )

            prompt_id = await queue_comfyui_workflow(graph_payload, host=target_host)
            return {
                "status": "QUEUED_COMFYUI",
                "client_id": client_id,
                "engine": "ComfyUI-Loopback",
                "host": target_host,
                "prompt_id": prompt_id,
                "message": "Workflow dispatched to ComfyUI loopback queue."
            }
        except Exception as e:
            logger.error(f"ComfyUI dispatch failure: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"ComfyUI dispatch failed on loopback: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported mode: {req.mode}. Use 'direct_gpu' or 'comfyui_diffusion'.")


@router.post("/mask")
async def generate_mask(req: MattingRequest, request: Request, client_id: str = Depends(get_tenant)):
    """Convenience endpoint dedicated to alpha mask generation."""
    req.only_mask = True
    return await process_matte(req, request, client_id)


@router.get("/models")
async def list_available_models():
    """Returns supported matting models and their optimal use cases."""
    return {
        "default": "birefnet-general",
        "models": [
            {
                "name": "birefnet-general",
                "description": "Bilateral Reference Network - SOTA sub-pixel definition for hair, fur, and intricate boundaries.",
                "vram_mb": 1200,
                "latency_range": "180ms - 400ms"
            },
            {
                "name": "u2net",
                "description": "Standard U^2-Net - Balanced multi-scale salient object extraction.",
                "vram_mb": 450,
                "latency_range": "120ms - 250ms"
            },
            {
                "name": "isnet-general-use",
                "description": "DIS/IS-Net - High-contrast boundary extraction with crisp edge isolation.",
                "vram_mb": 800,
                "latency_range": "150ms - 300ms"
            }
        ]
    }
