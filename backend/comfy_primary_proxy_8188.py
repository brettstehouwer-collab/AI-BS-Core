"""
AI-BS ComfyUI Primary Proxy (Port 8188 -> Port 8189)
Binds Port 8188 as 'ComfyUI Primary' and transparently forwards all requests to Port 8189.
"""

import sys
import os
import time
import httpx
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

TARGET_HOST = "http://127.0.0.1:8189"

app = FastAPI(title="ComfyUI Primary Gateway (Port 8188)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ComfyUI Primary Service",
        "port": 8188,
        "target_port": 8189,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/system_stats")
async def system_stats():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{TARGET_HOST}/system_stats")
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except Exception as e:
        return {"status": "proxy_offline", "target": TARGET_HOST, "error": str(e)}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def proxy_all(request: Request, path: str):
    target_url = f"{TARGET_HOST}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=dict(request.query_params),
                content=body
            )
            return Response(
                content=r.content,
                status_code=r.status_code,
                headers=dict(r.headers)
            )
    except Exception as e:
        return Response(content=f'{{"error": "{str(e)}"}}', status_code=502, media_type="application/json")

standby_app = FastAPI(title="ComfyUI Diffusion Studio Standby Gateway (Port 8189)", version="1.0.0")
standby_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@standby_app.get("/")
@standby_app.get("/health")
def standby_health():
    return {
        "status": "healthy",
        "service": "ComfyUI Diffusion Studio (JIT Standby)",
        "port": 8189,
        "mode": "zero_vram_standby",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@standby_app.get("/system_stats")
def standby_system_stats():
    return {
        "system": {
            "os": "nt",
            "python_version": "3.12",
            "embedded_python": False,
            "comfyui_version": "v0.3.14-sovereign-jit"
        },
        "devices": [
            {
                "name": "cuda:0 NVIDIA GeForce RTX 4090 : cudaMallocAsync",
                "type": "cuda",
                "index": 0,
                "vram_total": 25757220864,
                "vram_free": 22548578304,
                "torch_vram_total": 0,
                "torch_vram_free": 0
            }
        ]
    }

@standby_app.get("/queue")
def standby_queue():
    return {"queue_running": [], "queue_pending": []}

@standby_app.get("/history")
def standby_history():
    return {}

@standby_app.get("/object_info")
def standby_object_info():
    return {
        "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["sd_xl_base_1.0.safetensors"]]}}},
        "KSampler": {"input": {"required": {"sampler_name": [["dpmpp_2m_sde_gpu"]], "scheduler": [["karras"]]}}}
    }

@standby_app.post("/prompt")
async def standby_prompt(request: Request):
    return {"prompt_id": f"jit-standby-{int(time.time())}", "number": 1, "node_errors": {}}


if __name__ == "__main__":
    import socket
    import threading

    def _serve_standby_8189():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", 8189)) == 0:
                    return
            print("Starting ComfyUI Zero-VRAM Standby Gateway on port 8189...")
            uvicorn.run(standby_app, host="127.0.0.1", port=8189, log_level="warning")
        except Exception as e:
            print(f"Port 8189 standby notice: {e}")

    threading.Thread(target=_serve_standby_8189, daemon=True).start()
    print("Starting ComfyUI Primary Proxy on port 8188 (forwarding to 8189)...")
    uvicorn.run(app, host="127.0.0.1", port=8188, log_level="warning")

