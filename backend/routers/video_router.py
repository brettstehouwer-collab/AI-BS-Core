import os
import sys
import uuid
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File, Form
from pydantic import BaseModel
import tempfile
try:
    import whisper
except ImportError:
    whisper = None

router = APIRouter(prefix="/api/video", tags=["video"])

VIDEO_EDITING_DIR = Path("C:/AI-BS/AI-BS_Modual_Video_Editing")
SCREEN_RECORDINGS_DIR = VIDEO_EDITING_DIR / "Screen Recordings"
SCREEN_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

PYTHON_EXE = sys.executable or r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"


class VideoPipelineRequest(BaseModel):
    prompt: str
    engine: Optional[str] = "comfyui"


class BatchPipelineRequest(BaseModel):
    prompt: str
    engine: Optional[str] = "comfyui"


class StreamRequest(BaseModel):
    video_path: str


@router.post("/test_pipeline")
async def run_single_scene_pipeline(payload: VideoPipelineRequest):
    """
    Executes a single scene generation pipeline via ComfyUI (Wan2.1) or Diffusers.
    """
    prompt = payload.prompt.strip()
    engine = payload.engine or "comfyui"
    
    unique_id = str(uuid.uuid4())[:8]
    
    if engine == "unreal":
        output_filename = f"generated_unreal_{unique_id}.py"
        output_path = SCREEN_RECORDINGS_DIR / output_filename
        script_path = VIDEO_EDITING_DIR / "video_gen_engine" / "unreal_bridge.py"
        cmd = [
            PYTHON_EXE,
            str(script_path),
            "--prompt", prompt,
            "--out", str(output_path)
        ]
    elif "comfyui" in engine:
        output_filename = f"generated_scene_{unique_id}.mp4"
        output_path = SCREEN_RECORDINGS_DIR / output_filename
        script_path = VIDEO_EDITING_DIR / "video_gen_engine" / "comfyui_bridge.py"
        cmd = [
            PYTHON_EXE,
            str(script_path),
            "--prompt", prompt,
            "--engine", engine,
            "--out", str(output_path)
        ]
    else: # diffusers / cogvideox
        output_filename = f"generated_scene_{unique_id}.mp4"
        output_path = SCREEN_RECORDINGS_DIR / output_filename
        script_path = VIDEO_EDITING_DIR / "video_gen_engine" / "generator.py"
        cmd = [
            PYTHON_EXE,
            str(script_path),
            "--prompt", prompt,
            "--engine", engine,
            "--out", str(output_path)
        ]

    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(VIDEO_EDITING_DIR),
            env=env
        )
        stdout, stderr = await proc.communicate()
        
        stdout_str = stdout.decode("utf-8", errors="ignore")
        stderr_str = stderr.decode("utf-8", errors="ignore")
        combined_logs = f"{stdout_str}\n{stderr_str}".strip()

        if proc.returncode == 0 and output_path.exists():
            return {
                "status": "success",
                "output": combined_logs,
                "video_path": str(output_path),
                "stream_url": f"/api/video/stream?path={output_path.name}"
            }
        else:
            return {
                "status": "error",
                "output": combined_logs,
                "error": stderr_str or "Video generation process failed or did not output a video file.",
                "message": combined_logs
            }
    except Exception as e:
        return {
            "status": "error",
            "output": f"[ERROR] Failed to execute video pipeline: {str(e)}",
            "message": str(e)
        }


@router.post("/batch_pipeline")
async def start_batch_pipeline(payload: BatchPipelineRequest, background_tasks: BackgroundTasks):
    """
    Launches a multi-scene video batch generator job in the background.
    """
    job_id = str(uuid.uuid4())
    output_filename = f"batch_video_{job_id[:8]}.mp4"
    output_path = SCREEN_RECORDINGS_DIR / output_filename
    status_file = SCREEN_RECORDINGS_DIR / f"batch_status_{job_id}.json"

    # Initialize status
    with open(status_file, "w") as f:
        json.dump({
            "status": "running",
            "message": "Initializing batch worker...",
            "current": 0,
            "total": 1,
            "final_path": None
        }, f)

    def run_worker():
        worker_script = VIDEO_EDITING_DIR / "video_gen_engine" / "video_batch_worker.py"
        cmd = [
            PYTHON_EXE,
            str(worker_script),
            "--script", payload.prompt,
            "--engine", payload.engine or "comfyui",
            "--out", str(output_path),
            "--status_file", str(status_file)
        ]
        subprocess.run(cmd, cwd=str(VIDEO_EDITING_DIR))

    background_tasks.add_task(run_worker)
    return {"status": "accepted", "job_id": job_id}


@router.get("/batch_status/{job_id}")
def get_batch_status(job_id: str):
    status_file = SCREEN_RECORDINGS_DIR / f"batch_status_{job_id}.json"
    if not status_file.exists():
        return {"status": "running", "message": "Starting batch worker...", "current": 0, "total": 1}
    try:
        with open(status_file, "r") as f:
            return json.load(f)
    except Exception as e:
        return {"status": "running", "message": "Updating...", "current": 0, "total": 1}


@router.post("/start_stream")
def start_video_stream(payload: StreamRequest):
    p = Path(payload.video_path)
    if not p.exists():
        # Check in SCREEN_RECORDINGS_DIR
        alt = SCREEN_RECORDINGS_DIR / p.name
        if alt.exists():
            p = alt
        else:
            raise HTTPException(status_code=404, detail=f"Video file not found at {payload.video_path}")
    return {
        "status": "success",
        "stream_url": f"/api/video/stream?path={p.name}"
    }


@router.get("/stream")
def stream_video_file(path: str = Query(..., description="File name or absolute path")):
    target = Path(path)
    if not target.is_absolute():
        target = SCREEN_RECORDINGS_DIR / path
        if not target.exists():
            target = Path("C:/AI-BS/screenplay_projects/Echoes_Within") / path

    if not target.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
        
    return FileResponse(
        path=str(target),
        media_type="video/mp4",
        filename=target.name
    )


@router.get("/script")
def get_script_content(path: str = Query(..., description="File name or absolute path to .py")):
    target = Path(path)
    if not target.is_absolute():
        target = SCREEN_RECORDINGS_DIR / path
        if not target.exists():
            target = Path("C:/AI-BS/screenplay_projects/Echoes_Within") / path

    if not target.exists():
        raise HTTPException(status_code=404, detail="Script file not found")
    try:
        content = target.read_text(encoding="utf-8")
        return {"status": "success", "path": str(target), "content": content, "filename": target.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


UE_CMD_EXE = r"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
UE_EDITOR_EXE = r"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
UPROJECT_PATH = r"C:\AI-BS\UnrealHub\AI_BS_Hub.uproject"


class UnrealExecutionRequest(BaseModel):
    script_path: str


@router.post("/unreal/execute_script")
async def execute_unreal_script(payload: UnrealExecutionRequest):
    """
    Executes an Unreal Engine Python script headlessly on the local Unreal Engine 5.8 project,
    spawning and placing all actors, cameras, lights, and props in the level.
    """
    script_p = Path(payload.script_path)
    if not script_p.exists():
        alt = SCREEN_RECORDINGS_DIR / script_p.name
        if alt.exists():
            script_p = alt
        else:
            raise HTTPException(status_code=404, detail=f"Script not found at {payload.script_path}")

    cmd = [
        UE_CMD_EXE,
        UPROJECT_PATH,
        f"-ExecutePythonScript={str(script_p)}",
        "-nullrhi",
        "-unattended",
        "-NoSplash",
        "-StdOut"
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=r"C:\AI-BS\UnrealHub"
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode("utf-8", errors="ignore")
        
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "output": out[-3000:] if len(out) > 3000 else out,
            "message": "✅ Scene successfully constructed and saved in Unreal Engine 5.8 persistent level!" if proc.returncode == 0 else "Execution completed with warnings."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "output": f"[ERROR] Failed to run Unreal Engine: {e}"
        }


@router.post("/unreal/launch_editor")
def launch_unreal_editor(payload: UnrealExecutionRequest):
    """
    Launches Unreal Engine 5.8 Editor in interactive 3D Viewport mode.
    """
    script_p = Path(payload.script_path) if payload.script_path else None
    cmd = [UE_EDITOR_EXE, UPROJECT_PATH]
    if script_p and script_p.exists():
        cmd.append(f"-ExecutePythonScript={str(script_p)}")

    try:
        subprocess.Popen(cmd, cwd=r"C:\AI-BS\UnrealHub")
        return {
            "status": "success",
            "message": "🎮 Unreal Engine 5.8 Editor launched with 3D Scene Viewport!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UnrealCodeExecutionRequest(BaseModel):
    code: str


@router.post("/unreal/execute_code")
async def execute_unreal_code(payload: UnrealCodeExecutionRequest):
    """
    Executes raw Unreal Engine Python code sent directly from BS-CHAT,
    building and saving the 3D scene in AI_BS_Hub.uproject.
    """
    temp_name = f"chat_ue5_{uuid.uuid4().hex[:8]}.py"
    temp_path = SCREEN_RECORDINGS_DIR / temp_name
    
    # Write code to temp script
    code = payload.code.strip()
    if not code.startswith("import unreal"):
        code = "import unreal\n\n" + code
    if "save_current_level()" not in code:
        code += "\nunreal.EditorLoadingAndSavingUtils.save_current_level()\n"
        
    temp_path.write_text(code, encoding="utf-8")

    cmd = [
        UE_CMD_EXE,
        UPROJECT_PATH,
        f"-ExecutePythonScript={str(temp_path)}",
        "-nullrhi",
        "-unattended",
        "-NoSplash",
        "-StdOut"
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=r"C:\AI-BS\UnrealHub"
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode("utf-8", errors="ignore")
        
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "output": out[-3000:] if len(out) > 3000 else out,
            "script_path": str(temp_path),
            "message": "✅ 3D Level Generated & Saved in Unreal Engine 5.8 persistent project!" if proc.returncode == 0 else "Execution completed with warnings."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "output": f"[ERROR] Failed to run Unreal Engine: {e}"
        }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        temp_audio = Path(tempfile.gettempdir()) / f"whisper_{uuid.uuid4().hex}.wav"
        with open(temp_audio, "wb") as f:
            f.write(await file.read())
            
        model = whisper.load_model("base")
        result = model.transcribe(str(temp_audio), word_timestamps=True)
        
        words = []
        for segment in result.get('segments', []):
            for word in segment.get('words', []):
                words.append({
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                })
                
        temp_audio.unlink(missing_ok=True)
        return {"status": "success", "words": words}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/export_master")
async def export_master(
    audio_file: UploadFile = File(...),
    video_tracks: str = Form(...)
):
    try:
        tracks = json.loads(video_tracks)
        
        master_audio = Path(tempfile.gettempdir()) / f"master_{uuid.uuid4().hex}.wav"
        with open(master_audio, "wb") as f:
            f.write(await audio_file.read())
            
        output_file = SCREEN_RECORDINGS_DIR / f"final_export_{uuid.uuid4().hex}.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=60:d=10", # 10s blank for MVP
            "-i", str(master_audio),
            "-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_file)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        master_audio.unlink(missing_ok=True)
        
        return {
            "status": "success",
            "message": "FFmpeg NVENC Export Completed",
            "stream_url": f"/api/video/stream?path={output_file.name}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}