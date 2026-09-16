import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.comfy_image_processor import ComfyImageProcessor, MEDIA_OUTPUT_DIR

router = APIRouter(prefix="/api/v1/comfy/process", tags=["ComfyUI Image Processing & Matting"])


class MattingRequest(BaseModel):
    image_path: str = Field(..., description="Absolute path or relative path to target image")
    output_filename: Optional[str] = Field(None, description="Optional output filename")
    model_name: Optional[str] = Field("RMBG-1.4", description="Matting model: 'RMBG-1.4', 'BiRefNet', 'LayerStyle'")


class UpscaleRequest(BaseModel):
    image_path: str = Field(..., description="Absolute path or relative path to target image")
    scale_factor: Optional[int] = Field(4, description="Upscale multiplier (e.g. 2, 4)")
    output_filename: Optional[str] = Field(None, description="Optional output filename")
    model_name: Optional[str] = Field("4x-UltraSharp.pth", description="Upscaler model")


@router.post("/matting")
async def matting_endpoint(req: MattingRequest):
    """
    Executes background removal / alpha matting with ComfyUI or sovereign high-precision engine.
    """
    try:
        res = await ComfyImageProcessor.process_matting(
            image_path=req.image_path,
            output_filename=req.output_filename,
            model_name=req.model_name or "RMBG-1.4"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upscale")
async def upscale_endpoint(req: UpscaleRequest):
    """
    Executes 4x super-resolution upscaling with ComfyUI or sovereign high-fidelity engine.
    """
    try:
        res = await ComfyImageProcessor.process_upscale(
            image_path=req.image_path,
            scale_factor=req.scale_factor or 4,
            output_filename=req.output_filename,
            model_name=req.model_name or "4x-UltraSharp.pth"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/download/{filename}")
async def download_processed_media(filename: str):
    """
    Serves matted or upscaled output image assets directly.
    """
    safe_name = os.path.basename(filename)
    path = os.path.join(MEDIA_OUTPUT_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Processed media not found.")
    return FileResponse(path, media_type="image/png", filename=safe_name)
