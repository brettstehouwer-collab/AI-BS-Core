import os
import sys
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StrictStr
from core.local_ollama_http import local_ollama_client
from gpu.compute_scheduler import GPUAdmissionError
from gpu.model_residency import adaptive_embedding_batches, build_embedding_batches
from orchestrator.gpu_task_dispatcher import admitted_options, get_dispatcher, local_ollama_host

logger = logging.getLogger("ChatRouter")
router = APIRouter(prefix="/api/chat", tags=["Chat & Cognitive Intelligence"])

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    user_prompt: Optional[StrictStr] = Field(default=None, min_length=1, max_length=128000)
    source_references: Optional[list] = Field(default=None, max_length=4)
    prompt: Optional[str] = None
    mode: Optional[str] = None
    plan_only: bool = False
    execution_backend: Optional[str] = None
    provider: Optional[StrictStr] = None
    model: str = Field(default="stehouwer_llm", description="Target model name")
    messages: List[ChatMessage] = Field(default_factory=list, description="Conversation messages")
    temperature: float = Field(default=0.7, strict=True, ge=0.0, le=2.0)
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

def local_ollama_hosts():
    """Validate both configured transports before metadata or input can be sent."""
    try:
        return tuple(local_ollama_host(host) for host in (OLLAMA_HOST_PRIMARY, OLLAMA_HOST_SECONDARY))
    except GPUAdmissionError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.reason}) from exc

async def resolve_model_host(model_name: str) -> str:
    """Dynamically resolves which Ollama instance hosts the requested model."""
    hosts = local_ollama_hosts()
    for host in hosts:
        try:
            async with local_ollama_client(host, timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        tag = m.get("name", "").split(":")[0]
                        if tag == model_name or m.get("name") == model_name:
                            return host
        except Exception:
            continue
    return hosts[0]

@router.get("/models")
async def get_available_models():
    """Returns all available models discovered across local Ollama instances."""
    hosts = local_ollama_hosts()
    models_dict = {}
    for host in hosts:
        try:
            async with local_ollama_client(host, timeout=httpx.Timeout(2.0, connect=1.0)) as client:
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
            models_dict[fallback] = {"name": fallback, "host": hosts[0], "size_gb": 4.5, "details": {}}
            
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
    """Batch embeddings in input order; explicitly request CPU on the secondary."""
    inputs = [request.input] if isinstance(request.input, str) else request.input
    if not isinstance(inputs, list) or not inputs or not all(isinstance(x, str) for x in inputs):
        raise HTTPException(status_code=422, detail="input must be a string or nonempty string list")
    try:
        primary_host, secondary_host = local_ollama_hosts()
        dispatcher = get_dispatcher()
        if dispatcher.enabled:
            status = await dispatcher.controller.snapshot()
            batches = adaptive_embedding_batches(inputs, available_mib=status['available_budget_mib'])
        else:
            batches = build_embedding_batches(inputs)
        result = {"model": request.model, "embeddings": [], "total_duration": 0,
                  "load_duration": 0, "prompt_eval_count": 0}
        async with local_ollama_client(primary_host, secondary_host, timeout=httpx.Timeout(60.0, connect=5.0)) as client:
            for batch in batches:
                payload = {"model": request.model, "input": batch}
                try:
                    resp = await client.post(f"{secondary_host}/api/embed",
                                             json={**payload, "options": {"num_gpu": 0}})
                    resp.raise_for_status()
                except httpx.HTTPError:
                    async with get_dispatcher().lease(request.model, primary_host,
                                                       workload="embeddings", priority=20) as admission:
                        resp = await client.post(f"{primary_host}/api/embed",
                                                 json={**payload, 'keep_alive': admission['keep_alive_s'],
                                                       'options': admitted_options({}, admission)})
                        resp.raise_for_status()
                data = resp.json()
                if len(data.get("embeddings", [])) != len(batch):
                    raise HTTPException(status_code=502, detail="embedding response count mismatch")
                result["embeddings"].extend(data["embeddings"])
                for key in ("total_duration", "load_duration", "prompt_eval_count"):
                    result[key] += data.get(key, 0)
        return result
    except GPUAdmissionError as e:
        raise HTTPException(status_code=503, detail={"code": e.reason}) from e
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail="embedding backend unavailable") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
@router.post("/completions")
async def generate_chat_completion(request: ChatRequest):
    """Chat completion with bounded local GPU admission and token streaming."""
    body = request.model_dump() if hasattr(request, 'model_dump') else request.dict()
    from core.attached_source_context import validate_request_sources, request_source_bundle
    source_references = validate_request_sources(body)
    from core.media_intent_policy import resolve_media_status
    service_reply = await resolve_media_status(body)
    if service_reply is not None:
        if request.stream:
            async def service_status_events():
                yield f"data: {json.dumps({'content': service_reply, 'done': True})}\n\n"
            return StreamingResponse(service_status_events(), media_type="text/event-stream")
        return {"status": "success", "response": service_reply, "model": "local-service-status"}
    from core.coding_chat import coding_request
    from core.historical_reference_context import historical_reference_context, request_reference_query
    reply = await asyncio.to_thread(coding_request, body)
    if reply is not None:
        return reply
    from core.bs_chat_provider import bs_chat_reply, chat_reply_response
    provider_reply = await bs_chat_reply(body)
    if provider_reply is not None:
        return chat_reply_response(provider_reply, stream=request.stream)
    target_host = await resolve_model_host(request.model)
    num_gpu = 99
    if arbitrate_workload:
        try:
            plan = await asyncio.to_thread(arbitrate_workload, request.model, task_type="chat")
            target_host = plan.get("host", target_host)
            num_gpu = plan.get("num_gpu", 99)
        except Exception as e:
            logger.debug(f"Arbiter fallback: {e}")
    
    ollama_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    if request.system_prompt:
        ollama_messages.insert(0, {"role": "system", "content": request.system_prompt})
    from core.pipeline_context_injector import inject_aibs_pipeline_context
    ollama_messages = inject_aibs_pipeline_context(ollama_messages)
    source_receipt = None
    if source_references:
        bundle = await request_source_bundle(request.user_prompt or request_reference_query(body), source_references)
        references, source_receipt = bundle['context'], bundle['receipt']
        from core.attached_source_context import source_unavailable_reply
        unavailable = source_unavailable_reply(bundle)
        if unavailable is not None:
            return chat_reply_response(unavailable, stream=request.stream)
    else:
        references = await asyncio.to_thread(historical_reference_context, request_reference_query(body))
    if references:
        ollama_messages.insert(0, {"role": "system", "content": references})

    options = {"temperature": request.temperature}
    if num_gpu < 99 or "stehouwer" in request.model or "qwen" in request.model:
        options["num_gpu"] = num_gpu

    payload = {
        "model": request.model,
        "messages": ollama_messages,
        "stream": request.stream,
        "options": options,
        "keep_alive": "5m"
    }

    if request.stream:
        async def stream_generator():
            try:
                async with get_dispatcher().lease(request.model, target_host, options=options) as admission:
                    payload['keep_alive'] = admission['keep_alive_s']
                    payload['options'] = admitted_options(options, admission)
                    async with local_ollama_client(target_host, timeout=httpx.Timeout(5400.0, connect=15.0, read=5400.0, write=30.0)) as client:
                        async with client.stream("POST", f"{target_host}/api/chat", json=payload) as resp:
                            if resp.status_code != 200:
                                err_text = await resp.aread()
                                yield f"data: {json.dumps({'error': err_text.decode('utf-8', errors='replace')})}\n\n"
                                return
                            async for line in resp.aiter_lines():
                                if line:
                                    try:
                                        chunk = json.loads(line)
                                    except json.JSONDecodeError:
                                        continue
                                    if chunk.get("error"):
                                        yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                                        return
                                    content = chunk.get("message", {}).get("content", "")
                                    done = chunk.get("done", False)
                                    yield f"data: {json.dumps({'content': content, 'done': done, **({'source_retrieval':source_receipt} if source_receipt is not None else {})})}\n\n"
                                    if done:
                                        break
            except GPUAdmissionError as e:
                yield f"data: {json.dumps({'error': e.reason, 'code': 'GPU_ADMISSION_DENIED'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            stream_generator(), 
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )
    else:
        try:
            async with get_dispatcher().lease(request.model, target_host, options=options) as admission:
                payload['keep_alive'] = admission['keep_alive_s']
                payload['options'] = admitted_options(options, admission)
                async with local_ollama_client(target_host, timeout=httpx.Timeout(5400.0, connect=15.0, read=5400.0, write=30.0)) as client:
                    resp = await client.post(f"{target_host}/api/chat", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return {"status": "success", "response": data.get("message", {}).get("content", ""),
                                **({'source_retrieval':source_receipt} if source_receipt is not None else {})}
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except GPUAdmissionError as e:
            raise HTTPException(status_code=503, detail={"code": e.reason}) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
