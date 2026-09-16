import os
import sys
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("ChatRouter")
router = APIRouter(prefix="/api/chat", tags=["Chat & Cognitive Intelligence"])

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    model: str = Field(default="stehouwer_llm", description="Target model name")
    messages: List[ChatMessage] = Field(default_factory=list, description="Conversation messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = Field(default=True)
    system_prompt: Optional[str] = None

def normalize_ollama_host(raw: Optional[str], default_port: int = 11434) -> str:
    if not raw:
        return f"http://127.0.0.1:{default_port}"
    s = raw.strip()
    if not s.startswith("http://") and not s.startswith("https://"):
        s = f"http://{s}"
    s = s.replace("0.0.0.0", "127.0.0.1")
    from urllib.parse import urlparse
    parsed = urlparse(s)
    if not parsed.port:
        s = f"{s.rstrip('/')}:{default_port}"
    return s.rstrip('/')

OLLAMA_HOST_PRIMARY = normalize_ollama_host(os.environ.get("OLLAMA_HOST"), 11434)
OLLAMA_HOST_SECONDARY = normalize_ollama_host(os.environ.get("OLLAMA_HOST_EDRIVE"), 11435)

async def resolve_model_host(model_name: str) -> str:
    """Dynamically resolves which Ollama instance hosts the requested model."""
    for host in [OLLAMA_HOST_PRIMARY, OLLAMA_HOST_SECONDARY]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        tag = m.get("name", "").split(":")[0]
                        if tag == model_name or m.get("name") == model_name:
                            return host
        except Exception:
            continue
    return OLLAMA_HOST_PRIMARY

@router.get("/models")
async def get_available_models():
    """Returns all available models discovered across local Ollama instances."""
    models_dict = {}
    for host in [OLLAMA_HOST_PRIMARY, OLLAMA_HOST_SECONDARY]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        name = m.get("name", "").split(":")[0]
                        if name and name not in models_dict:
                            models_dict[name] = {
                                "name": name,
                                "host": host,
                                "size_gb": round(m.get("size", 0) / (1024**3), 2),
                                "details": m.get("details", {})
                            }
        except Exception as e:
            logger.debug(f"Ollama tags lookup on {host}: {e}")
            
    if not models_dict:
        # Fallback default catalog
        for fallback in ["stehouwer_llm", "stehouwer_qwen", "stehouwer_dolphin", "stehouwer_hermes", "llama3.2"]:
            models_dict[fallback] = {"name": fallback, "host": OLLAMA_HOST_PRIMARY, "size_gb": 4.5, "details": {}}
            
    return {"status": "success", "models": list(models_dict.values())}

try:
    from scripts.dynamic_vram_layer_arbiter import arbitrate_workload
except ImportError:
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        from scripts.dynamic_vram_layer_arbiter import arbitrate_workload
    except Exception:
        arbitrate_workload = None

class EmbedRequest(BaseModel):
    model: str = Field(default="nomic-embed-text")
    input: Any = Field(...)

@router.post("/embed")
@router.post("/embeddings")
async def generate_embedding(request: EmbedRequest):
    """Routes vector embeddings to Pure-CPU Port 11435 on Ryzen 9 9950X with 0 VRAM usage."""
    payload = {"model": request.model, "input": request.input}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
            resp = await client.post(f"{OLLAMA_HOST_SECONDARY}/api/embed", json=payload)
            if resp.status_code == 200:
                return resp.json()
            # Fallback to primary if secondary offline
            resp_fb = await client.post(f"{OLLAMA_HOST_PRIMARY}/api/embed", json=payload)
            if resp_fb.status_code == 200:
                return resp_fb.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
@router.post("/completions")
async def generate_chat_completion(request: ChatRequest):
    """Executes a chat completion with dynamic CPU/GPU layer offloading and zero-latency token streaming."""
    target_host = await resolve_model_host(request.model)
    num_gpu = 99
    if arbitrate_workload:
        try:
            plan = arbitrate_workload(request.model, task_type="chat")
            target_host = plan.get("host", target_host)
            num_gpu = plan.get("num_gpu", 99)
        except Exception as e:
            logger.debug(f"Arbiter fallback: {e}")
    
    ollama_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    if request.system_prompt:
        ollama_messages.insert(0, {"role": "system", "content": request.system_prompt})

    options = {"temperature": request.temperature}
    if num_gpu < 99 or "stehouwer" in request.model or "qwen" in request.model:
        options["num_gpu"] = num_gpu

    payload = {
        "model": request.model,
        "messages": ollama_messages,
        "stream": request.stream,
        "options": options
    }

    if request.stream:
        async def stream_generator():
            try:
                client = httpx.AsyncClient(timeout=httpx.Timeout(5400.0, connect=15.0, read=5400.0, write=30.0))
                async with client.stream("POST", f"{target_host}/api/chat", json=payload) as resp:
                    if resp.status_code != 200:
                        err_text = await resp.aread()
                        yield f"data: {json.dumps({'error': err_text.decode('utf-8', errors='replace')})}\n\n"
                        await client.aclose()
                        return
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                done = chunk.get("done", False)
                                yield f"data: {json.dumps({'content': content, 'done': done})}\n\n"
                                if done:
                                    break
                            except Exception:
                                continue
                await client.aclose()
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            stream_generator(), 
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )
    else:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5400.0, connect=15.0, read=5400.0, write=30.0)) as client:
                resp = await client.post(f"{target_host}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"status": "success", "response": data.get("message", {}).get("content", "")}
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))