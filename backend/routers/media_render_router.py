"""
Autonomous Media Studio REST API Router for AI-BS (FastAPI)
Prefixes: /api/v1/render and /api/v1/media
"""

import os
import json
from fastapi import APIRouter, HTTPException, Query, Path, UploadFile, File, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from core.media_render_engine import MediaRenderEngine
from core.vram_resource_arbiter import vram_arbiter
from security.host_control_access import AdminHostControlRoute
from security.contained_file_access import write_bounded_upload, validate_upload_filename, resolve_media_path, open_verified_media, stream_media_response

MEDIA_UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "saved_data", "media_uploads"))
MEDIA_ROOTS = [MEDIA_UPLOAD_DIR, os.path.abspath(os.path.join(MEDIA_UPLOAD_DIR, "..", "media_renders"))]
router = APIRouter(prefix="/api/v1/media", tags=["Autonomous Media Studio"], route_class=AdminHostControlRoute)


# =========================================================================
# FILE UPLOAD ENDPOINT
# =========================================================================
@router.post("/upload")
async def upload_media_file(file: UploadFile = File(...)):
    """Store a bounded, new upload after router administrator admission."""
    safe_name = validate_upload_filename(file.filename)
    out_path, size = await write_bounded_upload(file, MEDIA_UPLOAD_DIR, safe_name)
    suffix = out_path.suffix.lower()
    media_type = "video" if suffix in {".mp4", ".mov", ".webm", ".mkv", ".avi"} else (
        "image" if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".tif", ".tiff", ".svg"} else "audio")
    return {"status": "success", "filename": safe_name, "filepath": str(out_path),
            "size_bytes": size, "media_type": media_type, "message": "Media upload saved."}


@router.get("/stream")
async def stream_media_file(request: Request, path: str = Query(..., description="Managed application media path")):
    return stream_media_response(path, MEDIA_ROOTS, request)


@router.get("/inspect")
async def inspect_media_file(path: str = Query(..., description="Managed application media path")):
    import math
    import subprocess
    from urllib.parse import quote
    with open_verified_media(path, MEDIA_ROOTS) as (clean_path, source):
        is_video = clean_path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv", ".avi"}
        is_image = clean_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
        duration = width = height = None
        probe_status = "unavailable"
        if is_video:
            try:
                proc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,duration", "-show_entries", "format=duration",
                    "-of", "json", "pipe:0"], stdin=source, shell=False, capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    streams = data.get("streams", [])
                    if streams:
                        stream = streams[0]
                        width = int(stream.get("width", 0)) or None
                        height = int(stream.get("height", 0)) or None
                        value = float(stream.get("duration") or data.get("format", {}).get("duration", 0))
                        duration = value if math.isfinite(value) and value > 0 else None
                        probe_status = "available" if width and height and duration is not None else "unavailable"
            except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, AttributeError):
                duration = width = height = None
        return {"status": "success", "filename": clean_path.name, "filepath": str(clean_path),
                "size_bytes": os.fstat(source.fileno()).st_size, "media_type": "video" if is_video else ("image" if is_image else "audio"),
                "width": width, "height": height, "duration": duration, "probe_status": probe_status,
                "stream_url": "/api/v1/media/stream?path=" + quote(str(clean_path), safe="")}


# =========================================================================
# SCHEMAS
# =========================================================================
class PipelineExecuteRequest(BaseModel):
    recipe: Dict[str, Any] = Field(..., description="Multi-stage production recipe with domain steps")
    job_id: Optional[str] = Field(default=None, description="Optional custom job identifier")

class SceneDetectRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    threshold: float = Field(default=27.0, description="Cut detection sensitivity")

class SmartReframeRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    target_aspect: str = Field(default="9:16", description="Target aspect ratio ('9:16', '1:1', '4:5')")
    smoothing_window: int = Field(default=15, description="Gaze smoothing filter window")

class PsdComposeRequest(BaseModel):
    psd_path: str = Field(..., description="Path to master PSD/PSB file")
    layer_overrides: Dict[str, Any] = Field(default_factory=dict, description="Layer updates/replacements")
    output_path: Optional[str] = None

class RasterTransformRequest(BaseModel):
    image_path: str = Field(..., description="Path to source image")
    operations: List[Dict[str, Any]] = Field(default_factory=list, description="List of resize, crop, cmyk operations")
    output_format: str = Field(default="png", description="Target file format")

class VseTimelineRequest(BaseModel):
    timeline_tracks: List[Dict[str, Any]] = Field(default_factory=list, description="Tracks and clips configuration")
    output_filename: Optional[str] = None
    resolution: str = Field(default="1920x1080", description="Canvas resolution")

class StripSilenceRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    db_threshold: float = Field(default=-32.0, description="Silence threshold in dB")
    min_silence_sec: float = Field(default=0.4, description="Minimum silence duration")

class ApplyLutRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    lut_path: str = Field(..., description="Path to .cube 3D LUT")
    intensity: float = Field(default=1.0, description="Grading intensity (0.0 to 1.0)")

class VoiceCloneRequest(BaseModel):
    text: str = Field(..., description="Text script to synthesize")
    ref_audio_path: str = Field(..., description="Path to reference speaker audio sample")
    output_filename: Optional[str] = None

class AudioCleanRequest(BaseModel):
    audio_path: str = Field(..., description="Path to noisy/reverberant audio")
    output_filename: Optional[str] = None

class DuckMusicRequest(BaseModel):
    speech_path: str = Field(..., description="Path to primary vocal/speech audio")
    music_path: str = Field(..., description="Path to background music track")
    duck_db: float = Field(default=-12.0, description="Attenuation dB during speech")

class VmafVerifyRequest(BaseModel):
    ref_video: str = Field(..., description="Path to reference raw plate")
    encoded_video: str = Field(..., description="Path to encoded video")
    min_vmaf: float = Field(default=93.0, description="Minimum allowable VMAF score")

class ThumbnailRankRequest(BaseModel):
    video_path: str = Field(..., description="Path to exported video")
    top_k: int = Field(default=3, description="Number of candidate thumbnails to return")

class ManimRenderRequest(BaseModel):
    scene_code: str = Field(..., description="Manim Python scene class code")
    scene_name: str = Field(default="AibsScene", description="Target Scene class name")
    quality: str = Field(default="medium_quality", description="'low_quality' or 'medium_quality'")
    output_filename: Optional[str] = None

class BlenderHeadlessRequest(BaseModel):
    python_script: str = Field(..., description="Python script to execute in headless Blender")
    output_format: str = Field(default="gltf", description="'gltf', 'glb', 'fbx', or 'obj'")
    asset_name: str = Field(default="ProceduralAsset", description="Name of 3D asset")
    output_filename: Optional[str] = None

class CanvasOverlayRequest(BaseModel):
    title: str = Field(default="AI-BS Telemetry HUD", description="Overlay title")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Key-value metrics to render")
    theme: str = Field(default="cyberpunk_dark", description="Visual theme")
    output_filename: Optional[str] = None


# =========================================================================
# ENDPOINTS
# =========================================================================
@router.post("/pipeline/execute")
async def execute_media_pipeline(req: PipelineExecuteRequest):
    raise HTTPException(status_code=503, detail="Media pipeline dispatch is held pending verified domain execution and durable completion receipts.")

@router.post("/pipeline/resume/{job_id}")
async def resume_media_pipeline(job_id: str = Path(..., description="Job identifier to resume")):
    raise HTTPException(status_code=503, detail="Pipeline resumption is held pending verified checkpoint provenance and durable dispatch recovery.")

@router.get("/vram/telemetry")
async def get_vram_telemetry_endpoint():
    return vram_arbiter.get_vram_telemetry()

@router.post("/vram/flush")
async def flush_vram_endpoint():
    return vram_arbiter.flush_vram_cache()

@router.get("/checkpoints/{job_id}")
async def get_job_checkpoint(job_id: str):
    raise HTTPException(status_code=503, detail="Legacy pipeline checkpoints require reconciliation before they can establish execution progress.")

@router.post("/vision/scene-detect")
async def detect_scenes_endpoint(req: SceneDetectRequest):
    return MediaRenderEngine.detect_shot_boundaries(req.video_path, req.threshold)

@router.post("/vision/smart-reframe")
async def smart_reframe_endpoint(req: SmartReframeRequest):
    return MediaRenderEngine.smart_reframe_vertical(req.video_path, req.target_aspect, req.smoothing_window)

@router.post("/image/compose-psd")
async def compose_psd_endpoint(req: PsdComposeRequest):
    return MediaRenderEngine.compose_psd_layers(req.psd_path, req.layer_overrides, req.output_path)

@router.post("/image/raster-transform")
async def raster_transform_endpoint(req: RasterTransformRequest):
    return MediaRenderEngine.pyvips_raster_transform(req.image_path, req.operations, req.output_format)

@router.post("/video/assemble-timeline")
async def assemble_timeline_endpoint(req: VseTimelineRequest):
    return MediaRenderEngine.assemble_vse_timeline(req.timeline_tracks, req.output_filename, req.resolution)

@router.post("/video/strip-silence")
async def strip_silence_endpoint(req: StripSilenceRequest):
    return MediaRenderEngine.strip_audio_silences(req.video_path, req.db_threshold, req.min_silence_sec)

@router.post("/video/apply-lut")
async def apply_lut_endpoint(req: ApplyLutRequest):
    return MediaRenderEngine.apply_3d_lut_grade(req.video_path, req.lut_path, req.intensity)

@router.post("/audio/voice-clone")
async def voice_clone_endpoint(req: VoiceCloneRequest):
    return MediaRenderEngine.clone_neural_voice_tts(req.text, req.ref_audio_path, req.output_filename)

@router.post("/audio/deepfilter-clean")
async def deepfilter_clean_endpoint(req: AudioCleanRequest):
    return MediaRenderEngine.deepfilter_audio_clean(req.audio_path, req.output_filename)

@router.post("/audio/duck-music")
async def duck_music_endpoint(req: DuckMusicRequest):
    return MediaRenderEngine.duck_background_music(req.speech_path, req.music_path, req.duck_db)

@router.post("/qc/vmaf")
async def verify_vmaf_endpoint(req: VmafVerifyRequest):
    return MediaRenderEngine.verify_vmaf_quality(req.ref_video, req.encoded_video, req.min_vmaf)

@router.post("/qc/aesthetic-thumbnails")
async def score_thumbnails_endpoint(req: ThumbnailRankRequest):
    return MediaRenderEngine.score_aesthetic_thumbnails(req.video_path, req.top_k)

@router.post("/vault/query")
async def query_vault_endpoint(query: str = Query(..., description="Semantic query for recipes"), top_k: int = Query(default=3)):
    return MediaRenderEngine.query_media_workflow_vault(query, top_k)

# =========================================================================
# WRITING STUDIO INTEGRATION ENDPOINTS
# =========================================================================
class ScriptToRecipeRequest(BaseModel):
    script_text: str = Field(..., description="Screenplay scene or full script Fountain text")
    scene_heading: Optional[str] = Field(default=None, description="INT./EXT. scene heading")
    target_pipeline: str = Field(default="auto_short", description="Pipeline target: 'auto_short', 'cinematic_trailer', 'audio_drama'")
    characters: Optional[List[str]] = Field(default_factory=list, description="Characters participating in scene")
    dialogue: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Structured character dialogue")
    action_lines: Optional[List[str]] = Field(default_factory=list, description="Scene visual action lines")
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio ('9:16', '16:9')")

class ScriptStoryboardRequest(BaseModel):
    script_text: str = Field(..., description="Screenplay scene text")
    scene_heading: Optional[str] = Field(default=None, description="INT./EXT. scene heading")
    action_lines: Optional[List[str]] = Field(default_factory=list, description="Scene action lines")
    num_panels: int = Field(default=4, description="Number of storyboard panels to generate")

@router.post("/script/to-recipe")
async def script_to_recipe_endpoint(req: ScriptToRecipeRequest):
    return MediaRenderEngine.convert_script_to_production_recipe(
        script_text=req.script_text,
        scene_heading=req.scene_heading,
        target_pipeline=req.target_pipeline,
        characters=req.characters,
        dialogue=req.dialogue,
        action_lines=req.action_lines,
        aspect_ratio=req.aspect_ratio
    )

@router.post("/script/storyboard")
async def script_storyboard_endpoint(req: ScriptStoryboardRequest):
    return MediaRenderEngine.generate_script_storyboard_prompts(
        script_text=req.script_text,
        scene_heading=req.scene_heading,
        action_lines=req.action_lines,
        num_panels=req.num_panels
    )


# Legacy /render aliases for backwards compatibility
@router.post("/render/manim/scene")
async def render_manim_endpoint(req: ManimRenderRequest):
    return MediaRenderEngine.render_manim_animation(req.scene_code, req.scene_name, req.quality, req.output_filename)

@router.post("/render/blender/headless")
async def render_blender_endpoint(req: BlenderHeadlessRequest):
    return MediaRenderEngine.execute_headless_blender(req.python_script, req.output_format, req.asset_name, req.output_filename)

@router.post("/render/canvas/overlay")
async def render_canvas_endpoint(req: CanvasOverlayRequest):
    return MediaRenderEngine.render_canvas_overlay(req.title, req.metrics, req.theme, req.output_filename)


# =========================================================================
# BSMEDIA-CHAT, DEDICATED CHROMADB & VLM ENDPOINTS (v5.297.0)
# =========================================================================
class MediaChatRequest(BaseModel):
    prompt: str = Field(..., description="Creator prompt or directive")
    media_context: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None

class MediaIndexRequest(BaseModel):
    media_id: Optional[str] = None
    media_type: str = Field(..., description="video, image, audio, or recipe")
    title: str
    description: str
    file_path: str
    metadata: Optional[Dict[str, Any]] = None

class MediaSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    media_type: Optional[str] = None

class VLMAnalyzeRequest(BaseModel):
    media_path: str
    instruction: Optional[str] = "Analyze this media frame and provide specific directorial edit instructions."

@router.post("/chat/stream")
async def stream_media_chat(req: MediaChatRequest):
    """Streams conversational guidance from BsMedia-Chat powered by VLM & stehouwer_media_memory."""
    from fastapi.responses import StreamingResponse
    from core.sovereign_reasoning.vlm_guidance_engine import vlm_guidance_engine

    async def event_generator():
        async for chunk in vlm_guidance_engine.stream_media_chat_guidance(
            prompt=req.prompt,
            media_context=req.media_context,
            messages=req.messages
        ):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/vault/index")
async def index_media_asset_endpoint(req: MediaIndexRequest):
    """Indexes a media asset into the dedicated stehouwer_media_memory ChromaDB collection."""
    from core.media_chromadb_vault import media_chroma_vault
    import uuid
    m_id = req.media_id or f"media_{uuid.uuid4().hex[:8]}"
    return media_chroma_vault.add_media_asset(
        media_id=m_id,
        media_type=req.media_type,
        title=req.title,
        description=req.description,
        file_path=req.file_path,
        metadata=req.metadata
    )

@router.post("/vault/search")
async def search_media_vault_endpoint(req: MediaSearchRequest):
    """Searches the dedicated stehouwer_media_memory ChromaDB collection."""
    from core.media_chromadb_vault import media_chroma_vault
    return media_chroma_vault.search_media_memory(
        query=req.query,
        top_k=req.top_k,
        media_type=req.media_type
    )

@router.get("/vault/stats")
async def get_media_vault_stats():
    """Returns statistics on the dedicated media ChromaDB collection."""
    from core.media_chromadb_vault import media_chroma_vault
    return media_chroma_vault.get_stats()

@router.post("/vlm/analyze")
async def analyze_visual_endpoint(req: VLMAnalyzeRequest):
    """Analyzes a visual asset using the local VLM engine."""
    from core.sovereign_reasoning.vlm_guidance_engine import vlm_guidance_engine
    return await vlm_guidance_engine.analyze_visual_asset(
        image_or_frame_path=req.media_path,
        instruction=req.instruction
    )

