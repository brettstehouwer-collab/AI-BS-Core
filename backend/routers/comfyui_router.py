import json
import os
import uuid
import asyncio
import math
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from comfyui_client import inject_prompt_into_workflow, queue_prompt, get_history, upload_image_to_comfyui
from video_batcher_utils import extract_last_frame, stitch_videos_ffmpeg

router = APIRouter(prefix="/api/comfyui", tags=["comfyui"])
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "..", "comfyui_workflows")

chained_jobs = {}

class GenerateRequest(BaseModel):
    workflow_filename: str
    prompt_text: str
    base_image: str | None = None

class GenerateChainedRequest(BaseModel):
    workflow_filename: str
    prompt_text: str
    target_duration_sec: int
    chunk_duration_sec: int
    base_image: str | None = None

class Scene(BaseModel):
    prompt_text: str
    target_duration_sec: int

class GenerateScriptRequest(BaseModel):
    workflow_filename: str
    scenes: list[Scene]
    chunk_duration_sec: int
    base_image: str | None = None

@router.get("/workflows")
async def list_workflows():
    """Lists all available JSON workflows in the backend folder."""
    if not os.path.exists(WORKFLOWS_DIR):
        return {"workflows": []}
    files = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith(".json")]
    return {"workflows": files}

@router.post("/upload")
async def upload_base_image(image: UploadFile = File(...)):
    """Uploads a reference image to ComfyUI."""
    file_bytes = await image.read()
    response = upload_image_to_comfyui(file_bytes, image.filename)
    if not response or "name" not in response:
        raise HTTPException(status_code=500, detail="Failed to upload image to ComfyUI")
    return response

@router.post("/generate")
async def generate_media(request: GenerateRequest):
    """Injects the prompt into the requested workflow and queues it in ComfyUI."""
    file_path = os.path.join(WORKFLOWS_DIR, request.workflow_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Workflow file not found")
        
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            workflow_json = json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in workflow file")
            
    # Inject prompt intelligently
    modified_workflow = inject_prompt_into_workflow(workflow_json, request.prompt_text, request.base_image)
    
    # Generate unique client ID for this session
    client_id = str(uuid.uuid4())
    
    # Queue it
    response = queue_prompt(modified_workflow, client_id)
    if not response or "prompt_id" not in response:
        raise HTTPException(status_code=500, detail="Failed to queue prompt to ComfyUI")
        
    return {"status": "queued", "prompt_id": response["prompt_id"], "client_id": client_id}

@router.get("/status/{prompt_id}")
async def check_status(prompt_id: str):
    """Checks ComfyUI history to see if the prompt finished and returns output paths."""
    if prompt_id.startswith("chained-"):
        return chained_jobs.get(prompt_id, {"status": "pending"})
        
    history = get_history(prompt_id)
    if not history:
        return {"status": "pending"}
        
    if prompt_id in history:
        # Prompt finished! Extract outputs
        outputs = []
        prompt_data = history[prompt_id]
        if "outputs" in prompt_data:
            for node_id, node_output in prompt_data["outputs"].items():
                if "images" in node_output:
                    for img in node_output["images"]:
                        outputs.append(img)
                if "gifs" in node_output:
                    for gif in node_output["gifs"]:
                        outputs.append(gif)
                if "videos" in node_output:
                    for vid in node_output["videos"]:
                        outputs.append(vid)
        return {"status": "completed", "outputs": outputs}
    
    return {"status": "pending"}

@router.get('/view')
async def view_media(filename: str, subfolder: str = '', folder_type: str = 'output'):
    from fastapi.responses import Response
    from comfyui_client import get_image
    img_data = get_image(filename, subfolder, folder_type)
    if img_data:
        media_type = 'video/mp4' if filename.endswith(('.mp4', '.webm')) else 'image/png'
        if filename.endswith('.gif'): media_type = 'image/gif'
        return Response(content=img_data, media_type=media_type)
    raise HTTPException(status_code=404, detail='Media not found')

async def run_chained_generation(job_id: str, request: GenerateChainedRequest):
    try:
        total_chunks = math.ceil(request.target_duration_sec / request.chunk_duration_sec)
        file_path = os.path.join(WORKFLOWS_DIR, request.workflow_filename)
        with open(file_path, "r", encoding="utf-8") as f:
            workflow_json = json.load(f)
            
        chunk_files = []
        input_dir = r"C:\AI-BS\ComfyUI\input"
        chain_img_name = f"chain_input_{int(time.time())}.png"
        chain_img_path = os.path.join(input_dir, chain_img_name)
        
        # Chunk 1
        wf_chunk1 = inject_prompt_into_workflow(workflow_json, request.prompt_text, request.base_image)
        res = queue_prompt(wf_chunk1, str(uuid.uuid4()))
        prompt_id = res["prompt_id"]
        
        media_filename = None
        while True:
            history = get_history(prompt_id)
            if history and prompt_id in history:
                prompt_data = history[prompt_id]
                if "outputs" in prompt_data:
                    for node_id, node_output in prompt_data["outputs"].items():
                        if "images" in node_output:
                            media_filename = node_output["images"][0]["filename"]
                        if "gifs" in node_output:
                            media_filename = node_output["gifs"][0]["filename"]
                        if "videos" in node_output:
                            media_filename = node_output["videos"][0]["filename"]
                break
            await asyncio.sleep(2)
            
        if not media_filename:
            chained_jobs[job_id] = {"status": "error", "error": "Chunk 1 failed"}
            return
            
        first_video_path = os.path.join(r"C:\AI-BS\ComfyUI\output", media_filename)
        chunk_files.append(first_video_path)
        
        # Chunks 2..N
        for i in range(1, total_chunks):
            success = extract_last_frame(chunk_files[-1], chain_img_path)
            if not success:
                chained_jobs[job_id] = {"status": "error", "error": f"Failed extracting frame for chunk {i+1}"}
                return
                
            wf_chunk = inject_prompt_into_workflow(workflow_json, request.prompt_text, chain_img_name)
            res = queue_prompt(wf_chunk, str(uuid.uuid4()))
            prompt_id = res["prompt_id"]
            
            media_filename = None
            while True:
                history = get_history(prompt_id)
                if history and prompt_id in history:
                    prompt_data = history[prompt_id]
                    if "outputs" in prompt_data:
                        for node_id, node_output in prompt_data["outputs"].items():
                            if "images" in node_output:
                                media_filename = node_output["images"][0]["filename"]
                            if "gifs" in node_output:
                                media_filename = node_output["gifs"][0]["filename"]
                            if "videos" in node_output:
                                media_filename = node_output["videos"][0]["filename"]
                    break
                await asyncio.sleep(2)
                
            if not media_filename:
                chained_jobs[job_id] = {"status": "error", "error": f"Chunk {i+1} failed"}
                return
                
            chunk_video_path = os.path.join(r"C:\AI-BS\ComfyUI\output", media_filename)
            chunk_files.append(chunk_video_path)
            
        if total_chunks > 1:
            final_video_name = f"stitched_{int(time.time())}.mp4"
            final_video_path = os.path.join(r"C:\AI-BS\ComfyUI\output", final_video_name)
            
            stitch_success = stitch_videos_ffmpeg(chunk_files, final_video_path)
            if not stitch_success:
                 chained_jobs[job_id] = {"status": "error", "error": "Stitching failed"}
                 return
        else:
            final_video_name = media_filename
            
        chained_jobs[job_id] = {
            "status": "completed", 
            "outputs": [{"filename": final_video_name, "type": "video"}]
        }
    except Exception as e:
        chained_jobs[job_id] = {"status": "error", "error": str(e)}

@router.post("/generate_chained")
async def generate_media_chained(request: GenerateChainedRequest, background_tasks: BackgroundTasks):
    job_id = f"chained-{uuid.uuid4()}"
    chained_jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(run_chained_generation, job_id, request)
    return {"status": "queued", "prompt_id": job_id, "client_id": "chained_batcher"}

async def run_script_generation(job_id: str, request: GenerateScriptRequest):
    try:
        file_path = os.path.join(WORKFLOWS_DIR, request.workflow_filename)
        with open(file_path, "r", encoding="utf-8") as f:
            workflow_json = json.load(f)
            
        chunk_files = []
        input_dir = r"C:\AI-BS\ComfyUI\input"
        chain_img_name = f"chain_input_{int(time.time())}.png"
        chain_img_path = os.path.join(input_dir, chain_img_name)
        
        current_base_image = request.base_image
        
        for scene_idx, scene in enumerate(request.scenes):
            total_chunks = math.ceil(scene.target_duration_sec / request.chunk_duration_sec)
            if total_chunks <= 0:
                continue
                
            for i in range(total_chunks):
                if scene_idx > 0 or i > 0:
                    # We need to extract the last frame of the previous chunk
                    success = extract_last_frame(chunk_files[-1], chain_img_path)
                    if not success:
                        chained_jobs[job_id] = {"status": "error", "error": f"Failed extracting frame for scene {scene_idx+1} chunk {i+1}"}
                        return
                    current_base_image = chain_img_name
                    
                wf_chunk = inject_prompt_into_workflow(workflow_json, scene.prompt_text, current_base_image)
                res = queue_prompt(wf_chunk, str(uuid.uuid4()))
                prompt_id = res["prompt_id"]
                
                media_filename = None
                while True:
                    history = get_history(prompt_id)
                    if history and prompt_id in history:
                        prompt_data = history[prompt_id]
                        if "outputs" in prompt_data:
                            for node_id, node_output in prompt_data["outputs"].items():
                                if "images" in node_output:
                                    media_filename = node_output["images"][0]["filename"]
                                if "gifs" in node_output:
                                    media_filename = node_output["gifs"][0]["filename"]
                                if "videos" in node_output:
                                    media_filename = node_output["videos"][0]["filename"]
                        break
                    await asyncio.sleep(2)
                    
                if not media_filename:
                    chained_jobs[job_id] = {"status": "error", "error": f"Scene {scene_idx+1} chunk {i+1} failed"}
                    return
                    
                chunk_video_path = os.path.join(r"C:\AI-BS\ComfyUI\output", media_filename)
                chunk_files.append(chunk_video_path)
                
        if len(chunk_files) > 1:
            final_video_name = f"script_{int(time.time())}.mp4"
            final_video_path = os.path.join(r"C:\AI-BS\ComfyUI\output", final_video_name)
            
            stitch_success = stitch_videos_ffmpeg(chunk_files, final_video_path)
            if not stitch_success:
                 chained_jobs[job_id] = {"status": "error", "error": "Stitching script failed"}
                 return
        elif len(chunk_files) == 1:
            final_video_name = os.path.basename(chunk_files[0])
        else:
            chained_jobs[job_id] = {"status": "error", "error": "No chunks generated"}
            return
            
        chained_jobs[job_id] = {
            "status": "completed", 
            "outputs": [{"filename": final_video_name, "type": "video"}]
        }
    except Exception as e:
        chained_jobs[job_id] = {"status": "error", "error": str(e)}

@router.post("/generate_script")
async def generate_media_script(request: GenerateScriptRequest, background_tasks: BackgroundTasks):
    job_id = f"chained-{uuid.uuid4()}"
    chained_jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(run_script_generation, job_id, request)
    return {"status": "queued", "prompt_id": job_id, "client_id": "script_batcher"}
